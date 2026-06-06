/**
 * Context Bridge — Z.ai Scraper (v4.1)
 * Fetches conversation data from Z.ai's internal REST API.
 * Falls back to DOM scraping when the API lazy-loads content (returns skeleton nodes only).
 *
 * Z.ai URL:  https://chat.z.ai/c/{convId}
 * Z.ai API:  GET /api/v1/chats/{id}
 * Auth:      Bearer token from cookie "token" (primary) or chrome.scripting MAIN world (fallback)
 *
 * API structure: apiData.chat.history.messages = OBJECT map keyed by UUID.
 * Each message: { id, parentId, childrenIds[], role, content, timestamp }
 *
 * IMPORTANT — Lazy-loading issue:
 *   Z.ai only populates `content` for the most recent message in the API response.
 *   All older messages are returned as skeleton nodes (id, parentId, role, timestamp) with
 *   no content field. This means API-only extraction yields 1 message out of 20+.
 *   SOLUTION: When <50% of API messages have content, fall back to DOM scraping.
 *
 * DOM structure (z.ai chat page):
 *   Parent wrapper: div.flex.flex-col.justify-between.px-5.mb-3... (rounded-lg group)
 *   User messages:   div.user-message
 *   Assistant msgs:  sibling divs without user-message class
 *   Input box:       div.messageInputContainer (excluded)
 *
 * NOTE: z.ai has strict CSP that blocks inline script injection.
 * Token extraction uses cookie (Method 1) or chrome.scripting (Method 2) ONLY.
 *
 * Tech stack: Svelte + Vite SPA, Open WebUI fork.
 */

(() => {
  "use strict";

  /* ── Token Extraction ────────────────────────────────────── */
  // Content scripts run in an isolated world and CANNOT access page's localStorage.
  // Z.ai stores the JWT in BOTH a cookie named "token" AND localStorage.token.
  // Cookies ARE accessible from content scripts.
  //
  // IMPORTANT: z.ai has strict CSP that blocks ALL inline script injection.
  // We do NOT use document.createElement("script") — it triggers CSP violations.
  // Only cookie reading and chrome.scripting (MAIN world) are viable.

  let cachedToken = null;

  async function getToken() {
    if (cachedToken) return cachedToken;

    // Method 1: Read from cookie (works in content script isolated world)
    try {
      const cookies = document.cookie;
      const match = cookies.match(/(?:^|;\s*)token=([^;]+)/);
      if (match && match[1]) {
        const token = decodeURIComponent(match[1]).trim();
        if (token && token.length > 10) {
          cachedToken = token;
          console.log("[CB] Z.ai token found in cookie (" + token.length + " chars)");
          return cachedToken;
        }
      }
    } catch (e) {
      console.log("[CB] Cookie read failed:", e.message);
    }

    // Method 2: Use chrome.scripting to execute in MAIN world (MV3 approach)
    // This asks the background SW to run code in the page's MAIN world to read localStorage
    try {
      const token = await getTokenViaScripting();
      if (token && token.length > 10) {
        cachedToken = token;
        console.log("[CB] Z.ai token found via chrome.scripting (" + token.length + " chars)");
        return cachedToken;
      }
    } catch (e) {
      console.log("[CB] chrome.scripting failed:", e.message);
    }

    // Method 3: Try without explicit Bearer (cookies might be enough)
    console.log("[CB] No explicit token found, will try cookie-only auth");
    cachedToken = "";
    return cachedToken;
  }

  async function getTokenViaScripting() {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage(
        { target: "background", action: "getZaiToken" },
        (response) => {
          void chrome.runtime.lastError;
          resolve(response?.token || null);
        }
      );
    });
  }

  /* ── Fetch Conversation ─────────────────────────────────── */

  /* ── Scroll to top so z.ai renders all messages in DOM ── */
  // z.ai virtualises its message list — only visible messages exist in the DOM.
  // Before scraping we scroll the chat container to the very top and wait for
  // the DOM to stabilise so every message is rendered and scrapeable.

  async function scrollToTopAndWait() {
    // Find the scrollable chat container
    const container =
      document.querySelector("#chat-messages-container") ||
      document.querySelector("[id*='chat'][class*='overflow']") ||
      document.querySelector("main .overflow-y-auto") ||
      document.querySelector(".overflow-y-auto") ||
      document.querySelector("main");

    if (!container) {
      console.log("[CB] Z.ai: No scroll container found — skipping scroll");
      return;
    }

    const originalScrollTop = container.scrollTop;

    // If already at top, nothing to do
    if (originalScrollTop === 0) {
      console.log("[CB] Z.ai: Already at top");
      return;
    }

    console.log(`[CB] Z.ai: Scrolling to top (was at ${originalScrollTop}px)...`);

    return new Promise(resolve => {
      let lastNodeCount = document.querySelectorAll("div.user-message").length;
      let stableCount = 0;

      container.scrollTo({ top: 0, behavior: "smooth" });

      // Poll until the node count stabilises (no new messages loading)
      const poll = setInterval(() => {
        const count = document.querySelectorAll("div.user-message").length;
        if (count === lastNodeCount) {
          stableCount++;
          if (stableCount >= 4) { // stable for ~400ms
            clearInterval(poll);
            console.log(`[CB] Z.ai: DOM stable — ${count} user messages visible`);
            resolve();
          }
        } else {
          lastNodeCount = count;
          stableCount = 0;
          // Keep scrolling to top if we're not there yet
          if (container.scrollTop > 0) {
            container.scrollTo({ top: 0, behavior: "instant" });
          }
        }
      }, 100);

      // Hard timeout at 8 seconds — proceed regardless
      setTimeout(() => {
        clearInterval(poll);
        console.log("[CB] Z.ai: Scroll timeout — proceeding with whatever is rendered");
        resolve();
      }, 8000);
    });
  }

  async function fetchConversation() {
    const convId = CBCommon.getConversationId();
    if (!convId) {
      throw new Error("No conversation found. Please open a Z.ai chat first.");
    }

    console.log(`[CB] Fetching Z.ai conversation: ${convId.slice(0, 8)}...`);

    const token = await getToken();

    const headers = { "Accept": "application/json" };
    if (token && token.length > 0) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const url = `/api/v1/chats/${convId}`;

    const resp = await fetch(url, {
      credentials: "include",
      headers
    });

    if (!resp.ok) {
      const status = resp.status;
      let bodyText = "";
      try { bodyText = await resp.text(); } catch(e) {}

      if (status === 401) throw new Error("Authentication failed (401). Please log into chat.z.ai and refresh the page.");
      if (status === 403) throw new Error("Access denied (403) — this conversation may be private or deleted.");
      if (status === 404) throw new Error("Conversation not found (404). It may have been deleted or the URL is incorrect.");
      throw new Error(`Z.ai API returned ${status}${bodyText ? ': ' + bodyText.slice(0, 300) : ''}`);
    }

    const data = await resp.json();
    console.log(`[CB] Z.ai API response received — keys: ${Object.keys(data).join(", ")}`);

    return data;
  }

  /* ── Parse API Response ─────────────────────────────────── */
  // Messages are at apiData.chat.history.messages (an OBJECT/dict keyed by UUID)
  // This is the Open WebUI fork structure where chat.history contains the message tree.

  function parseConversation(apiData) {
    const result = parseConversationAPI(apiData);

    // z.ai lazy-loads content — the API skeleton is almost always incomplete.
    // Always attempt DOM scraping and use whichever source gives MORE messages.
    // DOM scraping captures the full visible conversation regardless of API gaps.
    console.log(
      `[CB] Z.ai: API gave ${result._withContent}/${result.rawNodeCount} messages with content — ` +
      `also trying DOM scraping to compare`
    );
    const domResult = scrapeFromDOM(apiData);

    if (domResult.messages.length > result.messages.length) {
      console.log(
        `[CB] Z.ai: DOM (${domResult.messages.length} msgs) > API (${result.messages.length} msgs) — using DOM`
      );
      return domResult;
    }

    console.log(
      `[CB] Z.ai: API (${result.messages.length} msgs) >= DOM (${domResult.messages.length} msgs) — using API`
    );
    return result;
  }

  /* ── DOM-based Fallback Extraction ──────────────────────── */
  // z.ai lazy-loads message content client-side. The API only returns content for
  // the most recent message; all older messages are skeleton nodes. This function
  // scrapes messages directly from the rendered DOM to capture all content.
  //
  // DOM structure:
  //   Parent: div.flex.flex-col.justify-between.px-5.mb-3.w-full.max-w-[1000px].mx-auto.rounded-lg.group
  //     ├── div.user-message          → User messages (contains user text)
  //     └── div (no user-message cls) → Assistant messages (contains Thought Process + response)
  //   Excluded: div.messageInputContainer (the chat input box)

  function scrapeFromDOM(apiData) {
    console.log("[CB] Z.ai: Starting DOM-based extraction...");

    // Get title from API data (more reliable than DOM) or page title
    const title = apiData.title || apiData.name || document.title.replace(/\s*[|–—]\s*Z\.?ai.*$/, "").trim() || "Z.ai Conversation";

    // Get model from API data
    const model =
      apiData.model ||
      (apiData.meta && Array.isArray(apiData.meta.models) && apiData.meta.models[0]) ||
      (apiData.chat && apiData.chat.models && Array.isArray(apiData.chat.models) && apiData.chat.models[0]) ||
      (apiData.chat && apiData.chat.model) ||
      "GLM";

    // The wrapper-parent approach is unreliable — z.ai's DOM is a flat sibling list,
    // not messages nested inside a parent wrapper. Go straight to the sibling walker.
    return scrapeFromDOMFallback(title, model, apiData);
  }

  /* ── Extract content from a z.ai DOM message element ──── */

  function extractZaiDOMContent(el, role) {
    // For assistant messages, skip the "Thought Process" collapsed section header
    // but keep the actual response content
    let result = "";

    // Walk through child elements to extract text content
    // Preserve code blocks and structure
    const blocks = el.querySelectorAll("pre > code");
    if (blocks.length > 0) {
      // Has code blocks — extract with syntax preservation
      return extractZaiMarkdownContent(el);
    }

    // Simple text extraction
    const text = el.innerText || el.textContent || "";
    return text.trim();
  }

  /* ── Extract z.ai DOM content preserving code blocks ──── */

  function extractZaiMarkdownContent(container) {
    let result = "";
    const children = container.children;

    if (children.length === 0) {
      return container.innerText || container.textContent || "";
    }

    for (const child of children) {
      const tag = child.tagName.toLowerCase();

      // Code blocks
      if (tag === "pre") {
        const codeEl = child.querySelector("code");
        const lang = codeEl ? detectZaiLanguage(codeEl.className) : "";
        const code = codeEl ? codeEl.textContent : child.textContent;
        result += "```" + lang + "\n" + code.trim() + "\n```\n\n";
      }
      // Inline code
      else if (tag === "code") {
        result += "`" + child.textContent + "`";
      }
      // Paragraphs, divs, spans
      else if (tag === "p" || tag === "div" || tag === "span" || tag === "li") {
        const nestedPre = child.querySelectorAll("pre");
        if (nestedPre.length > 0) {
          result += extractZaiMarkdownContent(child);
        } else {
          const text = child.innerText || child.textContent || "";
          if (text.trim()) result += text.trim() + "\n\n";
        }
      }
      // Lists
      else if (tag === "ul" || tag === "ol") {
        const items = child.querySelectorAll(":scope > li");
        items.forEach(li => {
          const text = li.innerText || li.textContent || "";
          result += "- " + text.trim() + "\n";
        });
        result += "\n";
      }
      // Headings
      else if (tag === "h1" || tag === "h2" || tag === "h3" || tag === "h4") {
        const level = parseInt(tag[1]);
        const text = child.innerText || child.textContent || "";
        result += "#".repeat(level) + " " + text.trim() + "\n\n";
      }
      // Tables
      else if (tag === "table") {
        result += extractZaiTable(child);
      }
      // Everything else
      else {
        const text = child.innerText || child.textContent || "";
        if (text.trim()) result += text.trim() + "\n\n";
      }
    }

    return result.trim();
  }

  /* ── Extract table as markdown ───────────────────────────── */

  function extractZaiTable(tableEl) {
    const rows = tableEl.querySelectorAll("tr");
    if (rows.length === 0) return "";
    let md = "";
    rows.forEach((row, i) => {
      const cells = row.querySelectorAll("th, td");
      const rowText = Array.from(cells).map(c => (c.innerText || c.textContent || "").trim()).join(" | ");
      md += "| " + rowText + " |\n";
      if (i === 0) md += "| " + Array.from(cells).map(() => "---").join(" | ") + " |\n";
    });
    return md + "\n";
  }

  /* ── Detect language from code element classes ─────────── */

  function detectZaiLanguage(className) {
    if (!className) return "";
    const match = className.match(/(?:language-|lang-|highlight-)(\w+)/);
    return match ? match[1] : "";
  }

  /* ── Broader DOM fallback for z.ai ─────────────────────── */

  function scrapeFromDOMFallback(title, model, apiData) {
    console.log("[CB] Z.ai DOM: Scraping from DOM...");

    // Confirmed z.ai DOM structure (from DevTools):
    //
    //   div.group.rounded-lg   ← wrapper (has ONE user-message inside)
    //     └── div.user-message ← user turn
    //   div.???                ← assistant turn (sibling of the WRAPPER, not of user-message)
    //   div.group.rounded-lg   ← next wrapper
    //     └── div.user-message ← next user turn
    //   ...
    //   div.messageInputContainer ← input box, stop here
    //
    // So: for each user-message, walk the WRAPPER's next siblings to find assistant content.

    const userMsgs = document.querySelectorAll("div.user-message");
    console.log(`[CB] Z.ai DOM: Found ${userMsgs.length} user-message divs`);

    if (userMsgs.length === 0) {
      console.log("[CB] Z.ai DOM: No user-message divs found — DOM scraping failed");
      return {
        title,
        model,
        messages: [],
        platform: "zai",
        exportTimestamp: new Date().toISOString(),
        messageSource: "DOM fallback (failed — no messages found)"
      };
    }

    const messages = [];
    const allUserMsgs = Array.from(userMsgs);

    for (let u = 0; u < allUserMsgs.length; u++) {
      const userEl = allUserMsgs[u];
      const nextUserEl = allUserMsgs[u + 1] || null;

      // Add the user message
      const userText = (userEl.innerText || userEl.textContent || "").trim();
      if (userText) {
        messages.push({ role: "user", content: userText, timestamp: null });
      }

      // The assistant response is a sibling of the WRAPPER (userEl.parentElement),
      // not a sibling of userEl itself. Walk from wrapper's next sibling forward
      // until we hit the next wrapper or the input box.
      const wrapper = userEl.parentElement;
      const nextWrapper = nextUserEl ? nextUserEl.parentElement : null;

      const assistantParts = [];
      let sibling = wrapper ? wrapper.nextElementSibling : null;

      while (sibling) {
        if (sibling === nextWrapper) break;
        if (sibling.classList.contains("messageInputContainer") ||
            sibling.querySelector(".messageInputContainer")) break;
        // If we hit another wrapper unexpectedly, stop
        if (sibling.querySelector("div.user-message")) break;

        const sibText = (sibling.innerText || sibling.textContent || "").trim();
        if (sibText.length > 5) {
          const isThoughtHeader = sibText === "Thought Process" && sibling.children.length <= 1;
          if (!isThoughtHeader) {
            assistantParts.push(extractZaiDOMContent(sibling, "assistant") || sibText);
          }
        }
        sibling = sibling.nextElementSibling;
      }

      if (assistantParts.length > 0) {
        messages.push({
          role: "assistant",
          content: assistantParts.filter(Boolean).join("\n\n").trim(),
          timestamp: null
        });
      }
    }

    console.log(`[CB] Z.ai DOM: Extracted ${messages.length} messages`);

    return {
      title,
      model,
      messages,
      platform: "zai",
      exportTimestamp: new Date().toISOString(),
      messageSource: "DOM scraping"
    };
  }

  /* ── Parse API Response ─────────────────────────────────── */
  // Messages are at apiData.chat.history.messages (an OBJECT/dict keyed by UUID)
  // This is the Open WebUI fork structure where chat.history contains the message tree.

  function parseConversationAPI(apiData) {
    const title = apiData.title || apiData.name || "Untitled Conversation";

    const model =
      apiData.model ||
      (apiData.meta && Array.isArray(apiData.meta.models) && apiData.meta.models[0]) ||
      (apiData.chat && apiData.chat.models && Array.isArray(apiData.chat.models) && apiData.chat.models[0]) ||
      (apiData.chat && apiData.chat.model) ||
      "GLM";

    // ── Find messages — try all known paths ──────────────────
    let messagesMap = null;
    let messageSource = "none";

    // Path 1 (CORRECT for Z.ai/Open WebUI): apiData.chat.history.messages
    if (apiData.chat && apiData.chat.history && apiData.chat.history.messages &&
        typeof apiData.chat.history.messages === "object" &&
        !Array.isArray(apiData.chat.history.messages) &&
        Object.keys(apiData.chat.history.messages).length > 0) {
      messagesMap = apiData.chat.history.messages;
      messageSource = "apiData.chat.history.messages (Open WebUI structure)";
    }
    // Path 2: Direct "messages" object (map)
    else if (apiData.messages && typeof apiData.messages === "object" && !Array.isArray(apiData.messages) && Object.keys(apiData.messages).length > 0) {
      messagesMap = apiData.messages;
      messageSource = "apiData.messages (object map)";
    }
    // Path 3: Direct "messages" array
    else if (Array.isArray(apiData.messages) && apiData.messages.length > 0) {
      messagesMap = {};
      for (const msg of apiData.messages) {
        if (msg && (msg.id || msg.content || msg.role)) {
          messagesMap[msg.id || ("arr_" + messagesMap.length)] = msg;
        }
      }
      messageSource = "apiData.messages (array → map)";
    }
    // Path 4: Nested in chat.messages (map)
    else if (apiData.chat && apiData.chat.messages && typeof apiData.chat.messages === "object" && !Array.isArray(apiData.chat.messages) && Object.keys(apiData.chat.messages).length > 0) {
      messagesMap = apiData.chat.messages;
      messageSource = "apiData.chat.messages (object map)";
    }
    // Path 5: Nested in chat.history.currentId (use currentId as leaf)
    else if (apiData.chat && apiData.chat.history && apiData.chat.history.currentId && apiData.chat.history.messages) {
      messagesMap = apiData.chat.history.messages;
      messageSource = "apiData.chat.history.messages (via currentId)";
    }
    // Path 6: Deep heuristic — scan nested objects for message-like shapes
    else {
      for (const key of Object.keys(apiData)) {
        const val = apiData[key];
        if (val && typeof val === "object" && !Array.isArray(val)) {
          for (const subKey of Object.keys(val)) {
            const subVal = val[subKey];
            if (subVal && typeof subVal === "object" && !Array.isArray(subVal)) {
              const subKeys = Object.keys(subVal);
              if (subKeys.length > 0) {
                const firstItem = subVal[subKeys[0]];
                if (firstItem && typeof firstItem === "object" && (firstItem.role !== undefined || firstItem.content !== undefined || firstItem.parentId !== undefined)) {
                  messagesMap = subVal;
                  messageSource = `apiData.${key}.${subKey} (deep heuristic)`;
                  break;
                }
              }
            }
          }
          if (messagesMap) break;
        }
      }
    }

    if (!messagesMap || Object.keys(messagesMap).length === 0) {
      console.warn("[CB] Z.ai: No messages found! Response keys:", Object.keys(apiData));
      return {
        title,
        model,
        messages: [],
        platform: "zai",
        exportTimestamp: new Date().toISOString(),
        debugInfo: "No messages found in any known path.",
        rawResponseKeys: Object.keys(apiData),
        responseSnippet: JSON.stringify(apiData).slice(0, 5000)
      };
    }

    const nodeCount = Object.keys(messagesMap).length;
    console.log(`[CB] Z.ai: Found messages via "${messageSource}" — ${nodeCount} nodes`);

    // ── Extract ALL messages sorted by timestamp ──────────────
    // Z.ai uses a tree structure, but for a single conversation we want ALL messages.
    // Tree traversal (following one branch) misses messages from other branches
    // (edits, regenerations, parallel threads). Sorting by timestamp captures everything.
    const messages = [];
    const allNodes = Object.values(messagesMap);

    // Filter to user/assistant only, sort chronologically
    const sorted = allNodes
      .filter(n => n.role === "user" || n.role === "assistant")
      .sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0));

    console.log(`[CB] Z.ai: ${sorted.length} user/assistant nodes (out of ${nodeCount} total)`);

    let withContent = 0;
    let withoutContent = 0;
    for (const node of sorted) {
      const hadContent = node.content;
      addMessage(messages, node);
      if (hadContent) withContent++;
      else withoutContent++;
    }

    console.log(`[CB] Z.ai: Extracted ${messages.length} messages (${withContent} with content, ${withoutContent} without)`);

    return {
      title,
      model,
      messages,
      rawNodeCount: nodeCount,
      _withContent: withContent,  // Internal — used by parseConversation to decide DOM fallback
      _withoutContent: withoutContent,
      platform: "zai",
      exportTimestamp: new Date().toISOString(),
      messageSource
    };
  }

  function addMessage(messages, node) {
    const role = node.role || "unknown";
    if (role === "system" || role === "tool" || role === "hidden") return;

    // Skip error messages (internal errors, not conversation content)
    if (node.error && !node.content) return;

    // Content can be string or array of content blocks
    let content = "";
    if (typeof node.content === "string") {
      content = node.content;
    } else if (Array.isArray(node.content)) {
      const textParts = [];
      for (const block of node.content) {
        if (typeof block === "string") {
          textParts.push(block);
        } else if (block && typeof block === "object") {
          if (block.type === "text" && block.text) textParts.push(block.text);
          else if (block.text) textParts.push(block.text);
          else if (block.content) textParts.push(typeof block.content === "string" ? block.content : JSON.stringify(block.content));
        }
      }
      content = textParts.join("\n\n");
    }

    if (node.contentType && node.contentType === "image") {
      content = content || "[Image attached]";
    }

    const timestamp = node.timestamp
      ? (typeof node.timestamp === "number"
        ? new Date(node.timestamp * 1000).toISOString()
        : new Date(node.timestamp).toISOString())
      : null;

    if (content && content.trim()) {
      const parsed = {
        role: role === "user" ? "user" : "assistant",
        content: content.trim(),
        timestamp
      };

      if (node.files && Array.isArray(node.files) && node.files.length > 0) {
        parsed.files = node.files;
      }

      messages.push(parsed);
    }
  }

  /* ── Message Listener (from popup) ──────────────────────── */

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.target !== "content-zai") return;

    switch (msg.action) {
      case "ping":
        sendResponse({ alive: true, platform: "zai" });
        return false;

      case "detect":
        sendResponse({
          platform: "zai",
          hasConversation: CBCommon.isChatPage(),
          conversationId: CBCommon.getConversationId(),
          url: window.location.href
        });
        return false;

      case "scrape":
        scrollToTopAndWait()
          .then(() => fetchConversation())
          .then(apiData => {
            const parsed = parseConversation(apiData);
            sendResponse({ ok: true, data: parsed });
          })
          .catch(err => {
            sendResponse({ ok: false, error: err.message });
          });
        return true;

      default:
        return false;
    }
  });

  console.log("[Context Bridge v4.1] Z.ai scraper loaded (API + DOM fallback).");
})();
