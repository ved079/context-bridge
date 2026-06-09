/**
 * Context Bridge — Popup Controller (v4)
 * Flow: Detect platform (Claude / ChatGPT / Z.ai) → Capture → Export
 * Supports: Claude, ChatGPT, Z.ai via internal API scraping.
 */

(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const el = {
    statusCard: $("statusCard"),
    statusIcon: $("statusIcon"),
    statusTitle: $("statusTitle"),
    statusSubtitle: $("statusSubtitle"),
    btnCapture: $("btnCapture"),
    captureIcon: $("captureIcon"),
    captureText: $("captureText"),
    captureHint: $("captureHint"),
    resultsPanel: $("resultsPanel"),
    resultsLabel: $("resultsLabel"),
    resultsTitle: $("resultsTitle"),
    statMessages: $("statMessages"),
    statTools: $("statTools"),
    statWords: $("statWords"),
    btnExportMd: $("btnExportMd"),
    btnExportCompact: $("btnExportCompact"),
    btnExportJson: $("btnExportJson"),
    btnTogglePreview: $("btnTogglePreview"),
    previewContent: $("previewContent"),
    loadingOverlay: $("loadingOverlay"),
    loadingText: $("loadingText"),
    errorBox: $("errorBox"),
    errorMsg: $("errorMsg")
  };

  let platform = null;      // "claude" | "chatgpt" | "zai"
  let captureData = null;  // last captured conversation data

  // Local helpers (popup can't access content script globals like CBCommon)
  function sanitizeFilename(str) {
    return (str || "untitled").toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 50).replace(/-$/, "");
  }

  /* ── Init ────────────────────────────────────────────────── */

  async function init() {
    await detectPlatform();
  }

  /* ── Platform Detection ───────────────────────────────────── */

  async function detectPlatform() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

      if (!tab || !tab.url || !tab.url.startsWith("http")) {
        setStatus("error", "No page detected", "Navigate to Claude, ChatGPT or Z.ai");
        return;
      }

      const url = tab.url;
      const platformNames = { claude: "Claude", chatgpt: "ChatGPT", zai: "Z.ai" };

      if (url.includes("claude.ai")) {
        platform = "claude";
      } else if (url.includes("chatgpt.com") || url.includes("chat.openai.com")) {
        platform = "chatgpt";
      } else if (url.includes("z.ai")) {
        platform = "zai";
      } else {
        platform = null;
        setStatus("error", "Not supported", "Navigate to Claude, ChatGPT or Z.ai");
        return;
      }

      // Check if content script is alive and has a conversation
      try {
        const ping = await sendToContentScript("ping");
        if (ping && ping.alive) {
          const hasConv = /([0-9a-f]{8}-[0-9a-f]{4}-)/i.test(url);
          if (hasConv) {
            setStatus("ready", platformNames[platform], "API mode — ready to capture");
          } else {
            setStatus("ready", platformNames[platform], "New chat — no conversation ID in URL");
          }
        } else {
          const hasConv = /([0-9a-f]{8}-[0-9a-f]{4}-)/i.test(url);
          if (hasConv) {
            setStatus("ready", platformNames[platform], "API mode — ready to capture");
          } else {
            setStatus("ready", platformNames[platform], "Open a conversation first");
          }
        }
      } catch (e) {
        const hasConv = /([0-9a-f]{8}-[0-9a-f]{4}-)/i.test(url);
        if (hasConv) {
          setStatus("ready", platformNames[platform], "API mode — ready to capture");
        } else {
          setStatus("ready", platformNames[platform], "Open a conversation first");
        }
      }
    } catch (err) {
      setStatus("error", "Error", "Could not detect platform: " + err.message);
    }
  }

  function setStatus(state, title, subtitle) {
    el.statusCard.className = "status-card" + (state === "ready" ? " ready" : state === "error" ? " error" : "");
    el.statusTitle.textContent = title;
    el.statusSubtitle.textContent = subtitle;
    el.btnCapture.disabled = state === "error";
    el.captureHint.textContent = state === "error" ? "Navigate to a supported page" : "Click to fetch via internal API";
  }

  /* ── Capture ───────────────────────────────────────────────── */

  async function captureConversation() {
    if (!platform) return;

    const platformNames = { claude: "Claude", chatgpt: "ChatGPT", zai: "Z.ai" };

    el.btnCapture.classList.add("loading");
    el.btnCapture.disabled = true;
    el.captureText.textContent = "Fetching...";
    el.loadingOverlay.style.display = "flex";
    el.loadingText.textContent = platform === "chatgpt"
      ? "Reading page content..."
      : platform === "zai"
        ? "Contacting Z.ai API..."
        : `Contacting Claude API...`;
    el.errorBox.style.display = "none";
    el.resultsPanel.style.display = "none";

    try {
      const response = await sendToContentScript("scrape");

      if (!response) {
        showError("No response from content script. Please refresh the chat page and try again.");
        return;
      }

      if (response.ok === false && response.error) {
        showError(response.error);
        return;
      }

      if (response.ok && response.data) {
        captureData = response.data;

        // If 0 messages but has debug info (Z.ai structure mismatch), show diagnostic
        if (response.data.messages.length === 0 && response.data.debugInfo) {
          showResults(response.data);
          showToast("Captured 0 messages — check console (F12) for debug info", "warning");
          // Also log to console from popup side
          console.warn("[CB Popup] Debug info:", response.data.debugInfo);
          if (response.data.rawResponseKeys) {
            console.warn("[CB Popup] Response keys:", response.data.rawResponseKeys);
          }
          if (response.data.responseSnippet) {
            console.log("[CB Popup] Response snippet:", response.data.responseSnippet);
          }
        } else {
          showResults(response.data);
          showToast(`Captured ${response.data.messages.length} messages!`, "success");
        }
      } else {
        showError("Unexpected response from content script.");
      }
    } catch (err) {
      showError("Capture failed: " + err.message);
    } finally {
      resetCaptureButton();
      el.loadingOverlay.style.display = "none";
    }
  }

  function resetCaptureButton() {
    el.btnCapture.classList.remove("loading");
    el.btnCapture.disabled = !platform;
    el.captureText.textContent = "Capture Conversation";
  }

  function showError(message) {
    el.errorBox.style.display = "flex";
    el.errorMsg.textContent = message;
  }

  /* ── Show Results ─────────────────────────────────────────── */

  function showResults(data) {
    el.resultsPanel.style.display = "block";

    el.resultsTitle.textContent = data.title || "Conversation";

    // Show capture method for ChatGPT
    if (data.method === "dom") {
      el.statusSubtitle.textContent = "DOM extraction (read from page)";
    } else if (data.method === "dom-fallback") {
      el.statusSubtitle.textContent = "DOM fallback extraction";
    } else if (data.method === "api") {
      el.statusSubtitle.textContent = "API extraction (backend fetch)";
    } else if (data.method) {
      el.statusSubtitle.textContent = `via ${data.method}`;
    }

    const msgCount = data.messages.length;
    let toolCount = 0;
    let wordCount = 0;

    data.messages.forEach((msg) => {
      wordCount += (msg.content || "").split(/\s+/).filter(Boolean).length;
      if (msg.tools) toolCount += msg.tools.length;
    });

    el.statMessages.textContent = msgCount;
    el.statTools.textContent = toolCount;
    el.statWords.textContent = wordCount >= 1000 ? (wordCount / 1000).toFixed(1) + "k" : wordCount;

    el.previewContent.style.display = "none";
    el.btnTogglePreview.textContent = "Show";

    setTimeout(() => {
      el.resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  }

  /* ── Export ────────────────────────────────────────────────── */

  function exportAs(format) {
    if (!captureData) {
      showToast("Nothing to export. Capture first!", "error");
      return;
    }

    let content, filename, mimeType;

    switch (format) {
      case "md":
        content = MarkdownGenerator.generate(captureData);
        filename = `${platform}-${sanitizeFilename(captureData.title)}.md`;
        mimeType = "text/markdown";
        break;
      case "compact":
        content = MarkdownGenerator.generateCompact(captureData);
        filename = `${platform}-${sanitizeFilename(captureData.title)}-compact.md`;
        mimeType = "text/markdown";
        break;
      case "json":
        content = MarkdownGenerator.generateJSON(captureData);
        filename = `${platform}-${sanitizeFilename(captureData.title)}.json`;
        mimeType = "application/json";
        break;
    }

    triggerDownload(content, filename, mimeType);
  }

  function triggerDownload(content, filename, mimeType) {
    // TextEncoder-based base64 to handle emoji/unicode safely
    const bytes = new TextEncoder().encode(content);
    let binary = "";
    bytes.forEach(b => binary += String.fromCharCode(b));
    const base64 = btoa(binary);
    const dataUrl = "data:" + mimeType + ";charset=utf-8;base64," + base64;

    chrome.downloads.download(
      { url: dataUrl, filename: filename, saveAs: true },
      (downloadId) => {
        if (downloadId) {
          showToast("Download started!", "success");
        } else {
          showToast("Download failed: " + (chrome.runtime.lastError?.message || "unknown"), "error");
        }
      }
    );
  }

  /* ── Preview ──────────────────────────────────────────────── */

  function togglePreview() {
    if (!captureData) return;
    const isVisible = el.previewContent.style.display !== "none";

    if (isVisible) {
      el.previewContent.style.display = "none";
      el.btnTogglePreview.textContent = "Show";
    } else {
      const md = MarkdownGenerator.generateCompact(captureData);
      el.previewContent.textContent = md.slice(0, 2500) + (md.length > 2500 ? "\n\n... (truncated)" : "");
      el.previewContent.style.display = "block";
      el.btnTogglePreview.textContent = "Hide";
    }
  }

  /* ── Messaging ────────────────────────────────────────────── */

  function sendToContentScript(action, data) {
    return new Promise((resolve) => {
      if (!platform) { resolve(null); return; }

      // Map platform to content script target
      const targetMap = {
        claude: "content-claude",
        chatgpt: "content-chatgpt",
        zai: "content-zai"
      };
      const target = targetMap[platform];
      const message = { target, action, ...data };

      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const tab = tabs[0];
        if (!tab || !tab.url || !tab.url.startsWith("http")) {
          resolve(null);
          return;
        }

        try {
          chrome.tabs.sendMessage(tab.id, message, (response) => {
            void chrome.runtime.lastError;
            resolve(response || null);
          });
        } catch (e) {
          resolve(null);
        }
      });
    });
  }

  /* ── Toast ─────────────────────────────────────────────────── */

  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    toast.style.background =
      type === "error" ? "#ef4444" :
      type === "success" ? "#10b981" :
      type === "warning" ? "#f59e0b" : "#6366f1";
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 2500);
  }

  /* ── Event Listeners ────────────────────────────────────────── */

  el.btnCapture.addEventListener("click", captureConversation);
  el.btnExportMd.addEventListener("click", () => exportAs("md"));
  el.btnExportCompact.addEventListener("click", () => exportAs("compact"));
  el.btnExportJson.addEventListener("click", () => exportAs("json"));
  el.btnTogglePreview.addEventListener("click", togglePreview);

  /* ── Start ──────────────────────────────────────────────────── */

  init();
})();
