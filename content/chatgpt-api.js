/**
 * Context Bridge — ChatGPT Scraper (v5.0.1)
 * 
 * DOM-based extraction with three critical post-processing passes:
 *   1. Hidden element filtering — skip display:none, visibility:hidden, opacity:0
 *   2. Citation artifact removal — strip truncated source chips (text ending in …)
 *   3. Content deduplication — remove consecutive identical paragraphs
 *
 * Also handles non-<table> rendered tables (div-based grids).
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

  /* ═══════════════════════════════════════════════════════════════
     DOM HELPERS — Visibility, Citation Detection, Table Detection
     ═══════════════════════════════════════════════════════════════ */

  /**
   * Check if an element is visually hidden.
   * ChatGPT leaves streaming artifacts and superseded content in the DOM
   * with display:none or visibility:hidden. We must skip these.
   */
  function isHiddenElement(el) {
    try {
      const style = window.getComputedStyle(el);
      if (style.display === "none") return true;
      if (style.visibility === "hidden") return true;
      if (parseFloat(style.opacity) === 0) return true;
    } catch (e) {
      // getComputedStyle can throw on detached nodes — treat as hidden
      return true;
    }
    return false;
  }

  /**
   * Check if an element or its text is a ChatGPT citation/source artifact.
   * These appear as clickable chips with truncated filenames like:
   *   "claude-i-found-this-order-proce…"
   * They are NOT part of the assistant's actual response text.
   *
   * Detection heuristics:
   *   - Text ends with the Unicode ellipsis character … (U+2026)
   *   - Element is inside a citation/source annotation container
   *   - Element is a <sup> tag (ChatGPT wraps citations in superscript)
   */
  function isCitationElement(el) {
    const tag = el.tagName.toLowerCase();

    // ChatGPT wraps citation references in <sup> tags
    if (tag === "sup") return true;

    // Check for citation-specific class names or data attributes
    const cls = el.className || "";
    if (typeof cls === "string") {
      if (cls.includes("citation") || cls.includes("source-attribution")) return true;
      if (cls.includes("token") && cls.includes("citation")) return true;
    }

    // Check data attributes that ChatGPT uses for citations
    if (el.hasAttribute("data-citation") || el.hasAttribute("data-source")) return true;

    return false;
  }

  /**
   * Check if a text string looks like a citation artifact.
   * Citation chips typically show truncated filenames ending with …
   */
  function isCitationText(text) {
    const trimmed = text.trim();
    if (!trimmed) return false;

    // Text ending with Unicode ellipsis (U+2026) — almost always a citation chip
    if (trimmed.endsWith("\u2026")) return true;

    // Text ending with three dots that looks like a truncated filename
    if (trimmed.endsWith("...") && trimmed.length < 60) {
      // Check if it looks like a filename (contains dashes, dots, no spaces)
      if (!trimmed.includes(" ") && (trimmed.includes("-") || trimmed.includes("."))) {
        return true;
      }
    }

    return false;
  }

  /**
   * Remove citation artifacts from extracted text content.
   * Handles both the ellipsis-formatted chips and any residual
   * "claude-i-found-this…" fragments that slip through.
   */
  function removeCitationArtifacts(text) {
    // Remove lines that are just citation artifacts
    const lines = text.split("\n");
    const cleaned = lines.filter(line => {
      const trimmed = line.trim();
      // Skip empty lines
      if (!trimmed) return true;
      // Skip citation artifact lines
      if (isCitationText(trimmed)) return false;
      // Skip lines that are ONLY a citation fragment (no other content)
      if (/^\s*\S+\u2026\s*$/.test(trimmed)) return false;
      return true;
    });
    return cleaned.join("\n");
  }

  /**
   * Deduplicate consecutive identical paragraphs.
   * During streaming, ChatGPT's DOM may contain the same paragraph twice
   * (the "current" version and the "previous" version before the update).
   * After extraction, we detect and remove these duplicates.
   */
  function deduplicateContent(text) {
    // Split into paragraphs (by double newline or single newline)
    const paragraphs = text.split(/\n+/);
    const deduped = [];

    for (let i = 0; i < paragraphs.length; i++) {
      const current = paragraphs[i].trim();
      if (!current) {
        deduped.push("");
        continue;
      }

      // Check if this paragraph is identical to the previous non-empty one
      const prev = deduped.length > 0 ? deduped[deduped.length - 1].trim() : null;
      if (prev === current) {
        // Identical consecutive paragraph — skip it
        continue;
      }

      deduped.push(current);
    }

    // Rejoin with single newlines (preserve structure)
    return deduped.join("\n");
  }

  /**
   * Clean and post-process extracted content.
   * Pipeline: citation removal → deduplication → whitespace cleanup
   */
  function cleanExtractedContent(text) {
    let cleaned = removeCitationArtifacts(text);
    cleaned = deduplicateContent(cleaned);

    // Collapse 3+ consecutive newlines into 2 (paragraph break)
    cleaned = cleaned.replace(/\n{3,}/g, "\n\n");

    // Remove trailing whitespace from each line
    cleaned = cleaned.split("\n").map(line => line.trimEnd()).join("\n");

    return cleaned.trim();
  }

  /* ═══════════════════════════════════════════════════════════════
     DIV-BASED TABLE DETECTION
     ═══════════════════════════════════════════════════════════════ */

  /**
   * Check if a div element is actually a table rendered with divs.
   * ChatGPT sometimes renders tables using divs with specific patterns:
   *   - Grid/flex layout with consistent column structure
   *   - Role="table" or aria attributes
   *   - Multiple child divs that each contain the same number of text segments
   */
  function isDivTable(el) {
    const tag = el.tagName.toLowerCase();
    if (tag === "table") return true;

    // Check for explicit table role
    if (el.getAttribute("role") === "table" || el.getAttribute("role") === "grid") return true;
    if (el.hasAttribute("data-table") || el.hasAttribute("aria-rowcount")) return true;

    // Check class names that suggest table rendering
    const cls = el.className || "";
    if (typeof cls === "string" && (
      cls.includes("table") ||
      cls.includes("datagrid") ||
      cls.includes("spreadsheet")
    )) {
      return true;
    }

    // For div-based tables: check if direct children form a grid-like pattern
    // with consistent column count (at least 2 columns, at least 2 rows)
    if (tag === "div") {
      const children = Array.from(el.children);
      if (children.length < 2) return false;

      // Check if children have role="row" or if grandchildren have role="cell/columnheader"
      const hasRowRoles = children.some(c =>
        c.getAttribute("role") === "row" || c.getAttribute("role") === "rowgroup"
      );
      if (hasRowRoles) return true;

      // Check if this div contains a nested table
      if (el.querySelector("table")) return false; // real table inside, not a div table

      // Check for a pattern of consistent inner text segments across children
      // (heuristic: each child has similar number of text-bearing nodes)
      const childTextCounts = children.map(c => {
        // Count distinct text segments (separated by tags, not just whitespace)
        const walker = document.createTreeWalker(c, NodeFilter.SHOW_TEXT, {
          acceptNode: (node) => {
            if (node.textContent.trim()) return NodeFilter.FILTER_ACCEPT;
            return NodeFilter.FILTER_REJECT;
          }
        });
        let count = 0;
        while (walker.nextNode()) count++;
        return count;
      });

      // If at least 2 children have the same number of text segments (≥2), it might be a table
      const segmentCounts = childTextCounts.filter(c => c >= 2);
      if (segmentCounts.length >= 2) {
        // Check if the majority share the same count
        const counts = new Map();
        for (const c of segmentCounts) {
          counts.set(c, (counts.get(c) || 0) + 1);
        }
        for (const [count, freq] of counts) {
          if (freq >= segmentCounts.length * 0.6 && segmentCounts.length >= 2) {
            return true;
          }
        }
      }
    }

    return false;
  }

  /**
   * Extract a div-based table as markdown.
   * Treats each direct child div as a row and text segments within as columns.
   */
  function extractDivTable(container) {
    const children = Array.from(container.children).filter(c => !isHiddenElement(c));
    if (children.length < 2) return null;

    const rows = [];

    for (const child of children) {
      const cells = [];
      // For each row child, get distinct text segments
      const textSegments = extractTextSegments(child);
      if (textSegments.length > 0) {
        cells.push(...textSegments);
      }
      if (cells.length > 0) {
        rows.push(cells);
      }
    }

    if (rows.length < 2) return null;

    // Normalize column count to the maximum found
    const maxCols = Math.max(...rows.map(r => r.length));
    if (maxCols < 2) return null;

    // Build markdown table
    let md = "";
    rows.forEach((row, i) => {
      // Pad row to maxCols
      while (row.length < maxCols) row.push("");
      md += "| " + row.map(c => c.trim()).join(" | ") + " |\n";
      if (i === 0) {
        md += "| " + Array.from({ length: maxCols }, () => "---").join(" | ") + " |\n";
      }
    });

    return md + "\n";
  }

  /**
   * Extract distinct text segments from an element.
   * Used for div-based table cell extraction.
   */
  function extractTextSegments(el) {
    const segments = [];
    const children = el.children;

    if (children.length === 0) {
      const text = (el.textContent || "").trim();
      if (text) segments.push(text);
      return segments;
    }

    for (const child of children) {
      if (isHiddenElement(child)) continue;
      if (isCitationElement(child)) continue;

      const tag = child.tagName.toLowerCase();

      // Recursively extract from nested divs (but not too deep)
      if (tag === "div" && !child.querySelector("div")) {
        const text = (child.textContent || "").trim();
        if (text) segments.push(text);
      } else if (tag === "span" || tag === "p" || tag === "strong" || tag === "em" || tag === "code" || tag === "b") {
        const text = (child.textContent || "").trim();
        if (text) segments.push(text);
      } else if (tag === "pre") {
        // Code block inside table cell — skip for now
        continue;
      } else {
        const text = (child.textContent || "").trim();
        if (text) segments.push(text);
      }
    }

    return segments;
  }

  /* ═══════════════════════════════════════════════════════════════
     DOM-BASED CONVERSATION EXTRACTION
     ═══════════════════════════════════════════════════════════════ */

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

  /* ═══════════════════════════════════════════════════════════════
     EXTRACT TEXT CONTENT FROM A MESSAGE ELEMENT
     ═══════════════════════════════════════════════════════════════ */

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

  /* ═══════════════════════════════════════════════════════════════
     EXTRACT CONTENT PRESERVING CODE BLOCKS & TABLES
     ═══════════════════════════════════════════════════════════════ */

  function extractMarkdownContent(container) {
    let result = "";
    const children = container.children;

    if (children.length === 0) {
      const text = container.innerText || container.textContent || "";
      return cleanExtractedContent(text);
    }

    for (const child of children) {
      // Skip hidden elements — these are streaming artifacts or superseded content
      if (isHiddenElement(child)) continue;

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
        // Skip citation elements
        if (isCitationElement(child)) continue;

        // Check if this is a div-based table
        if (tag === "div" && isDivTable(child)) {
          const tableMd = extractDivTable(child);
          if (tableMd) {
            result += tableMd;
            continue;
          }
        }

        // Check if this contains nested code blocks we should handle separately
        const nestedPre = child.querySelectorAll("pre");
        if (nestedPre.length > 0) {
          result += extractMarkdownContent(child);
        } else {
          const text = child.innerText || child.textContent || "";
          if (text.trim()) {
            // Clean individual text block for citation artifacts
            const cleanedText = removeCitationArtifacts(text.trim());
            if (cleanedText.trim()) {
              result += cleanedText.trim() + "\n\n";
            }
          }
        }
      }
      // Lists
      else if (tag === "ul" || tag === "ol") {
        const items = child.querySelectorAll("li");
        items.forEach(li => {
          if (isHiddenElement(li)) return;
          const text = li.innerText || li.textContent || "";
          const cleaned = removeCitationArtifacts(text.trim());
          if (cleaned) {
            result += "- " + cleaned + "\n";
          }
        });
        result += "\n";
      }
      // Headings
      else if (tag === "h1" || tag === "h2" || tag === "h3") {
        const level = parseInt(tag[1]);
        const text = child.innerText || child.textContent || "";
        result += "#".repeat(level) + " " + text.trim() + "\n\n";
      }
      // Tables (native <table> elements)
      else if (tag === "table") {
        result += extractTable(child);
      }
      // Links — just get the text (skip citation links)
      else if (tag === "a") {
        if (!isCitationElement(child)) {
          const linkText = child.textContent || "";
          if (!isCitationText(linkText)) {
            result += linkText;
          }
        }
      }
      // Everything else
      else {
        if (isCitationElement(child)) continue;
        const text = child.innerText || child.textContent || "";
        if (text.trim()) {
          result += text.trim() + "\n\n";
        }
      }
    }

    // Final cleanup pass: deduplicate + normalize whitespace
    return cleanExtractedContent(result);
  }

  /* ═══════════════════════════════════════════════════════════════
     EXTRACT TABLE AS MARKDOWN
     ═══════════════════════════════════════════════════════════════ */

  function extractTable(tableEl) {
    const rows = tableEl.querySelectorAll("tr");
    if (rows.length === 0) return "";

    let md = "";
    rows.forEach((row, i) => {
      const cells = row.querySelectorAll("th, td");
      const rowText = Array.from(cells)
        .map(c => {
          const text = (c.innerText || c.textContent || "").trim();
          // Clean citation artifacts from table cells
          return removeCitationArtifacts(text);
        })
        .join(" | ");
      md += "| " + rowText + " |\n";
      if (i === 0) {
        md += "| " + Array.from(cells).map(() => "---").join(" | ") + " |\n";
      }
    });
    return md + "\n";
  }

  /* ═══════════════════════════════════════════════════════════════
     DETECT LANGUAGE FROM CODE ELEMENT CLASSES
     ═══════════════════════════════════════════════════════════════ */

  function detectLanguageFromClasses(className) {
    if (!className) return "";
    const match = className.match(/(?:language-|lang-|highlight-)(\w+)/);
    return match ? match[1] : "";
  }

  /* ═══════════════════════════════════════════════════════════════
     GET CONVERSATION TITLE
     ═══════════════════════════════════════════════════════════════ */

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

  /* ═══════════════════════════════════════════════════════════════
     FALLBACK: ALTERNATIVE DOM SELECTORS
     ═══════════════════════════════════════════════════════════════ */

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
        // Skip hidden elements
        if (isHiddenElement(el)) continue;

        // Try to determine role from context
        const isUser = el.querySelector('[data-message-author-role="user"]') ||
                       el.querySelector(".avatar")?.closest("[class*='flex']")?.querySelector(".text-sm") ||
                       el.querySelector(".font-user");

        const content = el.innerText || el.textContent || "";
        if (!content.trim() || content.trim().length < 2) continue;

        // Skip action buttons and UI elements
        if (content.trim().length < 5) continue;
        if (["Copy", "Share", "Regenerate", "Edit", "Like", "Dislike"].includes(content.trim())) continue;

        // Apply citation cleanup to fallback content too
        const cleanedContent = cleanExtractedContent(content.trim());

        messages.push({
          role: isUser ? "user" : "assistant",
          content: cleanedContent,
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
            content: cleanExtractedContent(text.trim()),
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

  /* ═══════════════════════════════════════════════════════════════
     API-BASED FALLBACK (LAST RESORT)
     ═══════════════════════════════════════════════════════════════ */

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

  /* ═══════════════════════════════════════════════════════════════
     MAIN CAPTURE FLOW
     ═══════════════════════════════════════════════════════════════ */

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

  /* ═══════════════════════════════════════════════════════════════
     MESSAGE LISTENER (FROM POPUP)
     ═══════════════════════════════════════════════════════════════ */

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

  console.log("[Context Bridge v5.0.1] ChatGPT scraper loaded (DOM-first + citation filter + dedup).");
})();
