/**
 * Context Bridge — Z.ai API Scraper (v4.0.4)
 * Fetches complete conversation data from Z.ai's internal REST API.
 *
 * Z.ai URL:  https://chat.z.ai/c/{convId}
 * Z.ai API:  GET /api/v1/chats/{id}
 * Auth:      Bearer token from cookie "token" (primary) or chrome.scripting MAIN world (fallback)
 *
 * KEY: Messages are at apiData.chat.history.messages (an OBJECT map keyed by UUID).
 * Tree uses parentId/childrenIds. Each message: { id, parentId, childrenIds[], role, content, timestamp }
 *
 * NOTE: z.ai has strict CSP that blocks inline script injection.
 * Token extraction uses cookie (Method 1) or chrome.scripting (Method 2) ONLY.
 * No inline script injection — it always triggers CSP violations.
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
        fetchConversation()
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

  console.log("[Context Bridge v4.0.5] Z.ai API scraper loaded.");
})();
