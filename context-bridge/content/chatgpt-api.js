/**
 * Context Bridge — ChatGPT Scraper (v4.0.4)
 * 
 * STRATEGY CHANGE: ChatGPT's internal API (/backend-api/conversations/{id})
 * consistently returns 404 across all fetch contexts (content script, background SW,
 * page-context scripting). The API endpoint has either changed or been restricted.
 * 
 * NEW APPROACH: DOM-based extraction. We read messages directly from the page DOM
 * using ChatGPT's data attributes. This works regardless of API changes because
 * we capture what the user can actually see on screen.
 * 
 * ChatGPT message DOM structure (current):
 *   div[data-message-author-role="user"]       → User messages
 *   div[data-message-author-role="assistant"]  → Assistant messages
 *   Inside each: .markdown.prose or text content elements
 *   Code blocks: pre > code elements with language class
 *   Images: img elements within message containers
 *
 * Fallback: If DOM scraping fails, tries background API fetch as last resort.
 */

(() => {
  "use strict";

  /* ── DOM-based Conversation Extraction ───────────────────── */

  function scrapeFromDOM() {
    console.log("[CB] ChatGPT: Starting DOM-based extraction...");

    // Get the conversation title from the page
    const title = getConversationTitle();

    // Find all message containers
    const messageElements = document.querySelectorAll(
      '[data-message-author-role="user"], [data-message-author-role="assistant"]'
    );

    if (messageElements.length === 0) {
      // Try alternative selectors (older ChatGPT versions)
      console.log("[CB] ChatGPT: Standard selector found 0 messages, trying alternatives...");
      return scrapeFromDOMFallback(title);
    }

    console.log(`[CB] ChatGPT DOM: Found ${messageElements.length} message elements`);

    const messages = [];

    for (const el of messageElements) {
      const role = el.getAttribute("data-message-author-role");
      if (role !== "user" && role !== "assistant") continue;

      const content = extractMessageContent(el);
      if (!content || !content.trim()) continue;

      messages.push({
        role: role,
        content: content.trim(),
        timestamp: null // DOM doesn't provide reliable timestamps
      });
    }

    console.log(`[CB] ChatGPT DOM: Extracted ${messages.length} messages`);

    if (messages.length === 0) {
      return scrapeFromDOMFallback(title);
    }

    return {
      title: title || "ChatGPT Conversation",
      model: "ChatGPT",
      messages,
      platform: "chatgpt",
      method: "dom",
      exportTimestamp: new Date().toISOString()
    };
  }

  /* ── Extract text content from a message element ────────── */

  function extractMessageContent(messageEl) {
    // Strategy 1: Find .markdown content area
    const markdownEl = messageEl.querySelector(".markdown.prose") ||
                       messageEl.querySelector(".markdown") ||
                       messageEl.querySelector('[data-message-content-role="text"]');

    if (markdownEl) {
      return extractMarkdownContent(markdownEl);
    }

    // Strategy 2: Find the main content child (usually the second or third child)
    // ChatGPT structure: avatar div → content div → actions div
    const children = messageEl.children;
    for (const child of children) {
      // Look for the content container (not avatar, not action buttons)
      const tag = child.tagName.toLowerCase();
      const role = child.getAttribute("data-message-content-role");
      if (role === "text" || role === "markdown") {
        return extractMarkdownContent(child);
      }
      // Skip avatar (small icon container) and action bar
      if (tag === "button" || tag === "svg" || tag === "form") continue;
      // The content div is usually the largest text container
      const textLen = (child.innerText || "").length;
      if (textLen > 20) {
        return extractMarkdownContent(child);
      }
    }

    // Strategy 3: Use innerText as last resort
    const text = messageEl.innerText;
    return text || "";
  }

  /* ── Extract content preserving code blocks ─────────────── */

  function extractMarkdownContent(container) {
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
        const lang = codeEl ? detectLanguageFromClasses(codeEl.className) : "";
        const code = codeEl ? codeEl.textContent : child.textContent;
        result += "```" + lang + "\n" + code.trim() + "\n```\n\n";
      }
      // Inline code
      else if (tag === "code") {
        result += "`" + child.textContent + "`";
      }
      // Paragraphs and text blocks
      else if (tag === "p" || tag === "div" || tag === "span" || tag === "li") {
        // Check if this contains nested code blocks we should handle separately
        const nestedPre = child.querySelectorAll("pre");
        if (nestedPre.length > 0) {
          result += extractMarkdownContent(child);
        } else {
          const text = child.innerText || child.textContent || "";
          if (text.trim()) {
            result += text.trim() + "\n\n";
          }
        }
      }
      // Lists
      else if (tag === "ul" || tag === "ol") {
        const items = child.querySelectorAll("li");
        items.forEach(li => {
          const text = li.innerText || li.textContent || "";
          result += "- " + text.trim() + "\n";
        });
        result += "\n";
      }
      // Headings
      else if (tag === "h1" || tag === "h2" || tag === "h3") {
        const level = parseInt(tag[1]);
        const text = child.innerText || child.textContent || "";
        result += "#".repeat(level) + " " + text.trim() + "\n\n";
      }
      // Tables
      else if (tag === "table") {
        result += extractTable(child);
      }
      // Links — just get the text
      else if (tag === "a") {
        result += child.textContent || "";
      }
      // Everything else
      else {
        const text = child.innerText || child.textContent || "";
        if (text.trim()) {
          result += text.trim() + "\n\n";
        }
      }
    }

    return result.trim();
  }

  /* ── Extract table as markdown ───────────────────────────── */

  function extractTable(tableEl) {
    const rows = tableEl.querySelectorAll("tr");
    if (rows.length === 0) return "";

    let md = "";
    rows.forEach((row, i) => {
      const cells = row.querySelectorAll("th, td");
      const rowText = Array.from(cells).map(c => (c.innerText || c.textContent || "").trim()).join(" | ");
      md += "| " + rowText + " |\n";
      if (i === 0) {
        md += "| " + Array.from(cells).map(() => "---").join(" | ") + " |\n";
      }
    });
    return md + "\n";
  }

  /* ── Detect language from code element classes ───────────── */

  function detectLanguageFromClasses(className) {
    if (!className) return "";
    const match = className.match(/(?:language-|lang-|highlight-)(\w+)/);
    return match ? match[1] : "";
  }

  /* ── Get conversation title ─────────────────────────────── */

  function getConversationTitle() {
    // Method 1: Page title (usually "conversation title | ChatGPT")
    const pageTitle = document.title || "";
    const titleMatch = pageTitle.match(/^(.+?)(?:\s*[|–—]\s*ChatGPT|\s*[|–—]\s*OpenAI|$)/);
    if (titleMatch && titleMatch[1].trim()) {
      return titleMatch[1].trim();
    }

    // Method 2: Look for title in DOM
    const titleEl = document.querySelector('nav a.active, [data-testid="conversation-title"]') ||
                    document.querySelector('.font-semibold.text-lg') ||
                    document.querySelector('h1');
    if (titleEl) {
      const text = titleEl.innerText || titleEl.textContent || "";
      if (text.trim() && text.trim() !== "New chat") return text.trim();
    }

    return null;
  }

  /* ── Fallback: Alternative DOM selectors ─────────────────── */

  function scrapeFromDOMFallback(title) {
    console.log("[CB] ChatGPT DOM: Trying fallback selectors...");

    // Fallback 1: Look for message containers by common ChatGPT classes
    const altSelectors = [
      ".text-base",           // Common message wrapper
      ".conversation-turn",   // Newer ChatGPT wrapper
      "[class*='message']",   // Any class containing 'message'
      ".agent-turn",          // Agent conversation turns
    ];

    for (const selector of altSelectors) {
      const elements = document.querySelectorAll(selector);
      if (elements.length === 0) continue;

      console.log(`[CB] ChatGPT DOM: Fallback selector "${selector}" found ${elements.length} elements`);

      const messages = [];
      for (const el of elements) {
        // Try to determine role from context
        const isUser = el.querySelector('[data-message-author-role="user"]') ||
                       el.querySelector(".avatar")?.closest("[class*='flex']")?.querySelector(".text-sm") ||
                       el.querySelector(".font-user");

        const content = el.innerText || el.textContent || "";
        if (!content.trim() || content.trim().length < 2) continue;

        // Skip action buttons and UI elements
        if (content.trim().length < 5) continue;
        if (["Copy", "Share", "Regenerate", "Edit", "Like", "Dislike"].includes(content.trim())) continue;

        messages.push({
          role: isUser ? "user" : "assistant",
          content: content.trim(),
          timestamp: null
        });
      }

      if (messages.length >= 2) {
        console.log(`[CB] ChatGPT DOM: Fallback extracted ${messages.length} messages`);
        return {
          title: title || "ChatGPT Conversation",
          model: "ChatGPT",
          messages,
          platform: "chatgpt",
          method: "dom-fallback",
          exportTimestamp: new Date().toISOString()
        };
      }
    }

    // Fallback 2: Try the main chat area and extract all text
    const mainArea = document.querySelector("main") ||
                     document.querySelector('[role="main"]') ||
                     document.querySelector(".flex-1.overflow-hidden");

    if (mainArea) {
      const text = mainArea.innerText || "";
      if (text.trim().length > 50) {
        console.log("[CB] ChatGPT DOM: Using main area text extraction as last resort");
        return {
          title: title || "ChatGPT Conversation",
          model: "ChatGPT",
          messages: [{
            role: "assistant",
            content: text.trim(),
            timestamp: null
          }],
          platform: "chatgpt",
          method: "dom-text",
          exportTimestamp: new Date().toISOString()
        };
      }
    }

    return {
      title: title || "ChatGPT Conversation",
      model: "ChatGPT",
      messages: [],
      platform: "chatgpt",
      method: "dom-failed",
      exportTimestamp: new Date().toISOString(),
      error: "Could not extract messages from ChatGPT page DOM. Make sure the conversation is fully loaded and messages are visible on screen."
    };
  }

  /* ── API-based Fallback (last resort) ────────────────────── */

  async function fetchFromAPI() {
    const convId = CBCommon.getConversationId();
    if (!convId) {
      throw new Error("No conversation found. Please open a ChatGPT chat first.");
    }

    console.log(`[CB] ChatGPT: Trying API fallback for ${convId}`);

    // Delegate to background service worker
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(
        { target: "background", action: "fetchChatgpt", convId: convId },
        (response) => {
          void chrome.runtime.lastError;
          if (chrome.runtime.lastError) {
            reject(new Error("Background communication failed: " + chrome.runtime.lastError.message));
            return;
          }
          if (!response) {
            reject(new Error("No response from background."));
            return;
          }
          if (response.ok) {
            resolve(response.data);
          } else {
            reject(new Error(response.error || "API fetch failed"));
          }
        }
      );
    });
  }

  function parseAPIResponse(apiData) {
    const title = apiData.title || apiData.name || "Untitled Conversation";
    const model = apiData.model || apiData.current_model || apiData.model_slug || "ChatGPT";
    const mapping = apiData.mapping || {};

    const messages = [];
    const rootIds = Object.keys(mapping).filter(id => {
      const parent = mapping[id].parent;
      return parent === null || parent === "" || parent === undefined;
    });

    if (rootIds.length === 0) return { title, model, messages, platform: "chatgpt", method: "api" };

    function traverseTree(nodeId) {
      const node = mapping[nodeId];
      if (!node || !node.message) return;

      const msg = node.message;
      const role = msg.author?.role || "unknown";
      if (role === "system" || role === "tool" || role === "hidden") return;
      if (!msg.content) return;

      const parts = msg.content.parts || [];
      let textContent = "";

      if (typeof msg.content === "string") {
        textContent = msg.content;
      } else if (Array.isArray(parts)) {
        textContent = parts
          .filter(p => typeof p === "string")
          .join("\n\n");
      }

      if (textContent.trim()) {
        messages.push({
          role: role === "user" ? "user" : "assistant",
          content: textContent.trim(),
          timestamp: msg.create_time ? new Date(msg.create_time * 1000).toISOString() : null
        });
      }

      if (node.children && node.children.length > 0) {
        traverseTree(node.children[node.children.length - 1]);
      }
    }

    traverseTree(rootIds[0]);

    return {
      title,
      model,
      messages,
      rawNodeCount: Object.keys(mapping).length,
      platform: "chatgpt",
      method: "api",
      exportTimestamp: new Date().toISOString()
    };
  }

  /* ── Main Capture Flow ───────────────────────────────────── */
  // DOM first (reliable), API second (may fail with 404)

  async function captureConversation() {
    // Try DOM scraping first
    const domResult = scrapeFromDOM();

    if (domResult.messages && domResult.messages.length >= 2) {
      console.log(`[CB] ChatGPT: DOM extraction succeeded — ${domResult.messages.length} messages`);
      return domResult;
    }

    // DOM found 0-1 messages — try API as fallback
    console.log("[CB] ChatGPT: DOM extraction found insufficient messages, trying API fallback...");
    try {
      const apiData = await fetchFromAPI();
      const parsed = parseAPIResponse(apiData);
      if (parsed.messages.length >= 2) {
        console.log(`[CB] ChatGPT: API fallback succeeded — ${parsed.messages.length} messages`);
        return parsed;
      }
    } catch (apiErr) {
      console.log("[CB] ChatGPT: API fallback also failed:", apiErr.message);
    }

    // If DOM found at least something, return it (even if just 1 message)
    if (domResult.messages && domResult.messages.length > 0) {
      return domResult;
    }

    // Both methods failed
    if (domResult.error) {
      throw new Error(domResult.error);
    }
    throw new Error(
      "Could not extract ChatGPT conversation. " +
      "Please make sure: (1) You're on chatgpt.com with a conversation open, " +
      "(2) Messages are visible and fully loaded on screen, " +
      "(3) Try scrolling down to load all messages first."
    );
  }

  /* ── Message Listener (from popup) ──────────────────────── */

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.target !== "content-chatgpt") return;

    switch (msg.action) {
      case "ping":
        sendResponse({ alive: true, platform: "chatgpt" });
        return false;

      case "detect":
        sendResponse({
          platform: "chatgpt",
          hasConversation: CBCommon.isChatPage(),
          conversationId: CBCommon.getConversationId(),
          url: window.location.href
        });
        return false;

      case "scrape":
        captureConversation()
          .then(data => {
            sendResponse({ ok: true, data: data });
          })
          .catch(err => {
            sendResponse({ ok: false, error: err.message });
          });
        return true;

      default:
        return false;
    }
  });

  console.log("[Context Bridge v4.0.4] ChatGPT scraper loaded (DOM-first mode).");
})();
