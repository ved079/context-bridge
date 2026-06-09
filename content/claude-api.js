/**
 * Context Bridge — Claude API Scraper (v4)
 * Fetches complete conversation data from Claude's internal REST API.
 * Gets everything: text, tool calls, file contents, code — zero DOM scraping.
 *
 * Claude URL:  https://claude.ai/chat/{convId}
 * Claude API:  GET /api/organizations/{orgId}/chat_conversations/{convId}
 * Auth:        Same-origin cookies (automatic with credentials: "include")
 */

(() => {
  "use strict";

  /* ── Org ID Detection (3 fallback methods) ──────────────── */

  async function getOrgId() {
    // Method 1: Cookie — Claude stores active org in a cookie
    try {
      const cookies = document.cookie;
      // Try multiple known cookie names
      const patterns = [
        /lastActiveOrg=([^;]+)/,
        /currentOrgId=([^;]+)/,
        /organizationId=([^;]+)/,
        /orgId=([^;]+)/
      ];
      for (const pattern of patterns) {
        const match = cookies.match(pattern);
        if (match && match[1].length > 5) return match[1];
      }
    } catch (e) {
      console.log("[CB] Cookie scan failed:", e.message);
    }

    // Method 2: Fetch organizations list from API
    try {
      const resp = await fetch("/api/organizations", {
        credentials: "include",
        headers: { "Accept": "application/json" }
      });
      if (resp.ok) {
        const data = await resp.json();
        // The API might return an array or an object with an array field
        let orgs = null;
        if (Array.isArray(data)) orgs = data;
        else if (data.data && Array.isArray(data.data)) orgs = data.data;
        else if (data.organizations && Array.isArray(data.organizations)) orgs = data.organizations;
        else if (data.results && Array.isArray(data.results)) orgs = data.results;

        if (orgs && orgs.length > 0) {
          const org = orgs[0];
          return org.uuid || org.id || org.organization_id || null;
        }
      }
    } catch (e) {
      console.log("[CB] Org API fetch failed:", e.message);
    }

    // Method 3: Scrape from page's JavaScript context (Next.js/React)
    try {
      // Claude uses Next.js — check for org data in __NEXT_DATA__
      if (window.__NEXT_DATA__) {
        const searchForUUID = (obj, depth) => {
          if (!obj || typeof obj !== "object" || depth > 5) return null;
          for (const [key, value] of Object.entries(obj)) {
            if (/^(uuid|org|organization)_?id$/i.test(key) &&
                typeof value === "string" && /^[0-9a-f-]{20,}$/.test(value)) {
              return value;
            }
            if (typeof value === "object") {
              const found = searchForUUID(value, depth + 1);
              if (found) return found;
            }
          }
          return null;
        };
        const orgId = searchForUUID(window.__NEXT_DATA__, 0);
        if (orgId) return orgId;
      }

      // Also check for a global org variable that Claude might expose
      const globals = ["__CLAUDE_ORG_ID", "CLAUDE_ORG", "currentOrgId"];
      for (const g of globals) {
        if (window[g] && typeof window[g] === "string") return window[g];
      }
    } catch (e) {
      console.log("[CB] Page context scan failed:", e.message);
    }

    return null;
  }

  /* ── Fetch Conversation ─────────────────────────────────── */

  async function fetchConversation() {
    const convId = CBCommon.getConversationId();
    if (!convId) {
      throw new Error("No conversation found. Please open a Claude chat first.");
    }

    const orgId = await getOrgId();
    if (!orgId) {
      throw new Error(
        "Could not detect your Claude organization ID.\n" +
        "Make sure you are logged into claude.ai and have an active conversation open."
      );
    }

    console.log(`[CB] Fetching Claude conversation: org=${orgId.slice(0,8)}... conv=${convId.slice(0,8)}...`);

    // Fetch with tree=true for full conversation structure
    const url = `/api/organizations/${orgId}/chat_conversations/${convId}?tree=true&rendering_mode=messages&render_all_tools=true`;

    const resp = await fetch(url, {
      credentials: "include",
      headers: {
        "Accept": "application/json",
        "Content-Type": "application/json"
      }
    });

    if (!resp.ok) {
      const status = resp.status;
      if (status === 401) throw new Error("Authentication failed. Please log into claude.ai first.");
      if (status === 403) throw new Error("Access denied — you may not have permission for this conversation.");
      if (status === 404) throw new Error("Conversation not found (404). The chat may have been deleted.");
      throw new Error(`Claude API returned ${status} ${resp.statusText}`);
    }

    const data = await resp.json();
    console.log(`[CB] API response received — keys: ${Object.keys(data).join(", ")}`);

    return data;
  }

  /* ── Parse API Response ─────────────────────────────────── */

  function parseConversation(apiData) {
    // Claude's API returns: { uuid, name, model, chat_messages: [...], tree: {...}, ... }
    const title = apiData.name || apiData.title || "Untitled Conversation";
    const model = apiData.model || apiData.llm || "claude";
    const messages = [];

    // Use chat_messages (flat list) — most reliable
    let rawMessages = apiData.chat_messages || [];

    // If no chat_messages but there's a tree, try to flatten it
    if (rawMessages.length === 0 && apiData.tree) {
      rawMessages = flattenTree(apiData.tree);
    }

    console.log(`[CB] Parsing ${rawMessages.length} raw messages`);

    for (let mi = 0; mi < rawMessages.length; mi++) {
      const msg = rawMessages[mi];
      const sender = msg.sender || msg.author || msg.role;
      const role = (sender === "human" || sender === "user") ? "user" : "assistant";
      const timestamp = msg.created_at || msg.updated_at || msg.timestamp || null;

      const parsed = { role, content: "", timestamp };
      const contentBlocks = msg.content;
      const textParts = [];

      // ── 1. Extract files from msg.attachments ──
      // Claude stores user-uploaded files in msg.attachments[] with:
      //   { id, file_name, file_size, file_type, extracted_content }
      // The actual file text is in extracted_content (already decoded by Claude).
      // Large attachments (>50 lines) are wrapped in collapsible <details> to keep the export readable.
      // Code files are fenced with language detection from the filename extension.
      if (Array.isArray(msg.attachments) && msg.attachments.length > 0) {
        for (const att of msg.attachments) {
          if (att.extracted_content) {
            const displayName = att.file_name || "Uploaded file";
            const lang = CBCommon.detectLangFromPath(att.file_name);
            const sizeLabel = att.file_size ? `${(att.file_size / 1024).toFixed(1)} KB` : `${att.extracted_content.length} chars`;
            const lines = att.extracted_content.split("\n");

            if (lines.length > 50) {
              // Large file — collapsible to avoid wall-of-text
              textParts.push(
                `📎 **${displayName}** (${sizeLabel})\n\n` +
                `<details>\n<summary>Expand to view full file (${lines.length} lines)</summary>\n\n` +
                `\`\`\`${lang}\n${att.extracted_content}\n\`\`\`\n\n` +
                `</details>`
              );
            } else {
              // Small file — show inline with code fence
              const fenced = lang
                ? `\`\`\`${lang}\n${att.extracted_content}\n\`\`\``
                : att.extracted_content;
              textParts.push(`📎 **${displayName}** (${sizeLabel})\n\n${fenced}`);
            }
          } else if (att.file_name) {
            // Attachment exists but no extracted content (binary, image, etc.)
            textParts.push(`📎 **${att.file_name}** (${att.file_type || "unknown"}, ${att.file_size || "?"} bytes)`);
          }
        }
      }

      // ── 2. Extract files from msg.files (Claude Code tool-generated files) ──
      // Claude Code's tool outputs appear here with: { success, file_name, path, size_bytes, ... }
      if (Array.isArray(msg.files) && msg.files.length > 0) {
        for (const f of msg.files) {
          if (f.file_name) {
            const sizeNote = f.size_bytes ? ` (${(f.size_bytes / 1024).toFixed(1)} KB)` : "";
            textParts.push(`📎 **${f.file_name}**${sizeNote}`);
          }
        }
      }

      // ── 3. Parse content blocks from msg.content ──
      const tools = [];
      const toolResults = [];
      const thinkingParts = [];

      if (Array.isArray(contentBlocks) && contentBlocks.length > 0) {
        // Structured content blocks (API format)
        for (const block of contentBlocks) {
          switch (block.type) {
            case "text":
              if (block.text) textParts.push(block.text);
              break;

            case "tool_use":
              // Claude calling a tool (e.g., create_file, bash_tool, view, etc.)
              tools.push({
                name: block.name || "unknown",
                id: block.id || null,
                input: block.input || {}
              });
              break;

            case "tool_result":
              // Tool execution result — store output separately
              toolResults.push({
                toolUseId: block.tool_use_id || null,
                isError: block.is_error || false,
                content: extractToolResultContent(block.content)
              });
              break;

            case "thinking":
              // Claude's thinking block (extended thinking mode)
              // Standard API uses block.thinking, some internal formats use block.text
              if (block.thinking && block.thinking.trim()) {
                thinkingParts.push(block.thinking.trim());
              } else if (block.text && block.text.trim()) {
                thinkingParts.push(block.text.trim());
              }
              break;

            case "document":
            case "file":
            case "image":
              // File uploads — user attached a file to the conversation.
              // When multiple files are uploaded, each arrives as its own block.
              // Claude API wraps uploaded files in a source object with varying types:
              //   { type: "text",   data: "..." }           — plain-text files
              //   { type: "base64", media_type, data }      — binary / image files
              //   { type: "file",   file_id, media_type }   — files uploaded via Files API
              {
                const fileSource = block.source || {};

                // Resolve the display name: prefer explicit fields, fall back to source media type
                const fileName =
                  block.file_name ||
                  block.name ||
                  block.title ||
                  fileSource.file_name ||
                  fileSource.name ||
                  "Uploaded file";

                // Resolve the MIME / file type: don't use block.type — that's always the
                // switch key ("document" / "file" / "image"), not the actual file type.
                const fileType =
                  block.file_type ||
                  block.media_type ||
                  fileSource.media_type ||
                  null;

                const typeLabel = fileType ? ` (${fileType})` : "";

                if (fileSource.type === "text" && fileSource.data) {
                  // Inline text content — render in a fenced code block with lang detection
                  const lang = CBCommon.detectLangFromPath(fileName);
                  textParts.push(`📎 **${fileName}**${typeLabel}\n\n\`\`\`${lang}\n${fileSource.data}\n\`\`\``);

                } else if (fileSource.type === "base64" && fileSource.data) {
                  // Binary / image — can't inline the bytes, note it was attached
                  textParts.push(`📎 **${fileName}**${typeLabel} *(base64 encoded)*`);

                } else if (fileSource.type === "file") {
                  // Files API upload — file content is referenced by ID, not inlined.
                  // This is the common case for multi-file uploads via the paperclip UI.
                  const fileId = fileSource.file_id || fileSource.id || "";
                  const idNote = fileId ? ` · \`${fileId}\`` : "";
                  textParts.push(`📎 **${fileName}**${typeLabel}${idNote}`);

                } else if (block.content) {
                  const lang = CBCommon.detectLangFromPath(fileName);
                  textParts.push(`📎 **${fileName}**${typeLabel}\n\n\`\`\`${lang}\n${block.content}\n\`\`\``);

                } else if (block.text) {
                  // Fallback text — fence it too
                  const lang = CBCommon.detectLangFromPath(fileName);
                  textParts.push(`📎 **${fileName}**\n\n\`\`\`${lang}\n${block.text}\n\`\`\``);

                } else {
                  // Last resort — at minimum show the file name
                  textParts.push(`📎 **${fileName}**${typeLabel}`);
                }
              }
              break;

            default:
              // Unknown block type — try to extract any text or file content
              if (block.text) {
                textParts.push(block.text);
              } else if (block.file_name || block.name) {
                // Catch-all for unexpected file-like blocks
                const name = block.file_name || block.name;
                textParts.push(`📎 **${name}**`);
              }
              break;
          }
        }

      } else if (!textParts.length) {
        // No content blocks AND no attachments — fallback to msg.text
        parsed.content = (msg.text || "").trim();
      }

      // Merge all collected text (attachments + content blocks + text)
      if (textParts.length > 0) {
        parsed.content = textParts.join("\n\n").trim();
      }
      if (tools.length > 0) parsed.tools = tools;
      if (toolResults.length > 0) parsed.toolResults = toolResults;
      if (thinkingParts.length > 0) parsed.thinking = thinkingParts.join("\n\n").trim();

      // Only include messages that have actual content or tools
      if (parsed.content || (parsed.tools && parsed.tools.length > 0)) {
        messages.push(parsed);
      }
    }

    // Clean up: merge consecutive assistant messages that don't have separate tool boundaries
    // (Sometimes the API splits a single response into multiple messages)
    const merged = mergeConsecutiveAssistantMessages(messages);

    return {
      title,
      model,
      messages: merged,
      rawMessageCount: rawMessages.length,
      platform: "claude",
      exportTimestamp: new Date().toISOString()
    };
  }

  /**
   * Extract text content from a tool_result's content field.
   * The content can be a string, an array of blocks, or nested objects.
   */
  function extractToolResultContent(content) {
    if (!content) return "";
    if (typeof content === "string") return content;

    if (Array.isArray(content)) {
      return content
        .filter(b => b.type === "text" && b.text)
        .map(b => b.text)
        .join("\n");
    }

    return JSON.stringify(content);
  }

  /**
   * Flatten Claude's tree structure into a linear message list.
   * Follows the main branch (first child at each node).
   */
  function flattenTree(tree) {
    const messages = [];

    function traverse(node) {
      if (!node) return;
      if (node.message) messages.push(node.message);
      if (node.children && node.children.length > 0) {
        traverse(node.children[0]); // follow main branch
      }
    }

    if (Array.isArray(tree)) {
      tree.forEach(traverse);
    } else {
      traverse(tree);
    }

    return messages;
  }

  /**
   * Merge consecutive assistant messages that don't have tool calls.
   * This handles API quirks where Claude's text gets split into multiple messages.
   * We merge when: both are assistant, neither has tools, and they're adjacent.
   */
  function mergeConsecutiveAssistantMessages(messages) {
    if (messages.length <= 1) return messages;

    const merged = [];
    for (let i = 0; i < messages.length; i++) {
      const current = messages[i];
      const prev = merged[merged.length - 1];

      if (
        prev &&
        prev.role === "assistant" &&
        current.role === "assistant" &&
        !prev.tools &&
        !current.tools &&
        !current.toolResults
      ) {
        // Merge into previous
        prev.content = (prev.content + "\n\n" + current.content).trim();
      } else {
        merged.push({ ...current });
      }
    }

    return merged;
  }

  /* ── Message Listener (from popup) ──────────────────────── */

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.target !== "content-claude") return;

    switch (msg.action) {
      case "ping":
        sendResponse({ alive: true, platform: "claude" });
        return false;

      case "detect":
        sendResponse({
          platform: "claude",
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
        return true; // async

      default:
        return false;
    }
  });

  console.log("[Context Bridge v5] Claude API scraper loaded.");
})();
