/**
 * Context Bridge — Common Utilities (v2)
 * Shared helpers for content scripts: storage, detection, badge.
 */

const CBCommon = (() => {
  const CAPTURES_KEY = "cb_captures";

  /* ── Conversation ID Detection ───────────────────────────── */

  function getConversationId() {
    const path = window.location.pathname;

    // Method 1: UUID pattern (Claude, ChatGPT, Z.ai)
    const uuidMatch = path.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
    if (uuidMatch) return uuidMatch[1];

    // Method 2: ChatGPT /c/{anyHex} — ChatGPT sometimes uses non-UUID hex IDs
    const chatgptMatch = path.match(/\/c\/([a-f0-9]{8,})/i);
    if (chatgptMatch) return chatgptMatch[1];

    return null;
  }

  function getPlatform() {
    const host = window.location.hostname;
    if (host.includes("claude.ai")) return "claude";
    if (host.includes("chatgpt.com") || host.includes("chat.openai.com") || host.includes("openai.com")) return "chatgpt";
    if (host.includes("z.ai")) return "zai";
    return null;
  }

  function isChatPage() {
    return !!getConversationId();
  }

  /* ── Storage ──────────────────────────────────────────────── */

  async function getAllCaptures() {
    const result = await chrome.storage.local.get(CAPTURES_KEY);
    return result[CAPTURES_KEY] || [];
  }

  async function saveCapture(captureData) {
    const captures = await getAllCaptures();
    const entry = {
      id: "cap_" + Date.now() + "_" + Math.random().toString(36).slice(2, 6),
      savedAt: new Date().toISOString(),
      ...captureData
    };
    captures.unshift(entry); // newest first
    await chrome.storage.local.set({ [CAPTURES_KEY]: captures });
    return entry;
  }

  async function deleteCapture(id) {
    const captures = await getAllCaptures();
    const filtered = captures.filter(c => c.id !== id);
    await chrome.storage.local.set({ [CAPTURES_KEY]: filtered });
  }

  /* ── Badge ──────────────────────────────────────────────── */

  function setBadge(text, color) {
    chrome.action.setBadgeText({ text: String(text || "") });
    chrome.action.setBadgeBackgroundColor({ color: color || "#6366f1" });
  }

  /* ── Utility ────────────────────────────────────────────── */

  function sanitizeFilename(str) {
    return (str || "untitled").toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 50).replace(/-$/, "");
  }

  function detectLangFromPath(filePath) {
    const ext = (filePath || "").split(".").pop().toLowerCase();
    const map = {
      py: "python", js: "javascript", ts: "typescript", tsx: "tsx", jsx: "jsx",
      rb: "ruby", go: "go", rs: "rust", java: "java", cpp: "cpp", c: "c",
      cs: "csharp", php: "php", html: "html", css: "css", sql: "sql",
      sh: "bash", bash: "bash", yml: "yaml", yaml: "yaml", json: "json",
      md: "markdown", r: "r", swift: "swift", kt: "kotlin", dart: "dart",
      lua: "lua", scala: "scala", toml: "toml", xml: "xml", csv: "csv",
      dockerfile: "dockerfile", makefile: "makefile", tf: "hcl", vue: "vue"
    };
    return map[ext] || "";
  }

  /* ── Download Handler ──────────────────────────────────── */
  // Content scripts have full DOM access and persist after popup closes.
  // This is why we do downloads HERE instead of in the popup (which gets killed).

  function triggerDownload(content, filename, mimeType) {
    try {
      const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      // Clean up after a tick (popup may already be gone, but content script persists)
      setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }, 500);
      return true;
    } catch (err) {
      console.error('[CB] Download failed:', err);
      return false;
    }
  }

  // Listen for download requests from popup
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.action === 'download' && msg.content) {
      const ok = triggerDownload(msg.content, msg.filename || 'download.txt', msg.mimeType || 'text/plain');
      sendResponse({ ok });
    }
    return false;
  });

  /* ── Public API ──────────────────────────────────────────── */

  return {
    getConversationId,
    getPlatform,
    isChatPage,
    getAllCaptures,
    saveCapture,
    deleteCapture,
    setBadge,
    sanitizeFilename,
    detectLangFromPath,
    triggerDownload
  };
})();
