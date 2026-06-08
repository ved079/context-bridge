/**
 * Context Bridge — Background Service Worker (v5)
 * 
 * Responsibilities:
 * 1. Fetch ChatGPT conversations (bypasses page-level Service Worker interception)
 * 2. Extract Z.ai token via chrome.scripting (MAIN world localStorage access)
 * 3. Route messages between popup ↔ content scripts
 */

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.target !== "background") return false;

  /* ═══════════════════════════════════════════════════════════════
     1. CHATGPT FETCH — Runs in background to bypass page SW
     ═══════════════════════════════════════════════════════════════ */

  if (msg.action === "fetchChatgpt" && msg.convId) {
    const convId = msg.convId;
    console.log(`[CB Background] Fetching ChatGPT conversation: ${convId}`);

    fetchChatgptFromBackground(convId)
      .then(data => {
        console.log(`[CB Background] ChatGPT fetch OK — keys: ${Object.keys(data).join(", ")}`);
        sendResponse({ ok: true, data: data });
      })
      .catch(err => {
        console.error(`[CB Background] ChatGPT fetch failed:`, err);
        sendResponse({ ok: false, error: err.message });
      });

    return true; // async
  }

  /* ═══════════════════════════════════════════════════════════════
     2. Z.AI TOKEN — Extract from page localStorage via MAIN world
     ═══════════════════════════════════════════════════════════════ */

  if (msg.action === "getZaiToken") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs[0];
      if (!tab || !tab.url || !tab.url.includes("z.ai")) {
        sendResponse({ token: null });
        return;
      }
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        world: "MAIN",
        func: () => {
          try { return localStorage.getItem('token'); }
          catch(e) { return null; }
        }
      }).then((results) => {
        const token = results && results[0] && results[0].result;
        sendResponse({ token: token || null });
      }).catch((err) => {
        console.error("[CB] scripting.executeScript failed:", err);
        sendResponse({ token: null });
      });
    });
    return true; // async
  }

  /* ═══════════════════════════════════════════════════════════════
     3. DOWNLOAD — Handle data URL downloads
     ═══════════════════════════════════════════════════════════════ */

  if (msg.action === "download") {
    fetch(msg.dataUrl)
      .then(resp => resp.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob);
        chrome.downloads.download({
          url: url,
          filename: msg.filename,
          saveAs: true
        }, (downloadId) => {
          if (downloadId) {
            sendResponse({ ok: true, downloadId });
          } else {
            sendResponse({ error: chrome.runtime.lastError?.message || "Download failed" });
          }
        });
      })
      .catch(err => sendResponse({ error: err.message }));
    return true; // async
  }

  /* ═══════════════════════════════════════════════════════════════
     4. FALLTHROUGH — Route to content script
     ═══════════════════════════════════════════════════════════════ */

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs[0];
    if (!tab || !tab.url || !tab.url.startsWith("http")) {
      sendResponse({ error: "No supported page open" });
      return;
    }

    let target;
    if (tab.url.includes("claude.ai")) {
      target = "content-claude";
    } else if (tab.url.includes("chatgpt.com") || tab.url.includes("chat.openai.com")) {
      target = "content-chatgpt";
    } else if (tab.url.includes("z.ai")) {
      target = "content-zai";
    } else {
      sendResponse({ error: "Not a supported AI chat page" });
      return;
    }

    const forwardMsg = { ...msg };
    delete forwardMsg.target;

    chrome.tabs.sendMessage(tab.id, forwardMsg, (response) => {
      if (chrome.runtime.lastError) {
        sendResponse({ error: "Could not reach content script. Try refreshing the chat page." });
      } else {
        sendResponse(response);
      }
    });
  });

  return true; // async response
});

/* ═══════════════════════════════════════════════════════════════
   CHATGPT BACKGROUND FETCH IMPLEMENTATION
   ═══════════════════════════════════════════════════════════════ */

async function fetchChatgptFromBackground(convId) {
  // Strategy: Try multiple endpoint patterns with proper headers
  // The background SW has host_permissions for chatgpt.com, so fetch
  // will include cookies automatically (no Service Worker interception)

  const endpoints = [
    `/backend-api/conversations/${convId}`,
    `/backend-api/conversation/${convId}`,
  ];

  // Build headers that ChatGPT expects
  const headers = {
    "Accept": "application/json",
  };

  // Try to get oai-did from cookies (ChatGPT device ID)
  try {
    const cookies = await chrome.cookies.getAll({ domain: ".chatgpt.com" });
    const oaiDid = cookies.find(c => c.name === "oai-did");
    if (oaiDid && oaiDid.value) {
      headers["oai-device-id"] = oaiDid.value;
      console.log("[CB Background] Found oai-did cookie");
    }
  } catch (e) {
    // cookies API might fail in some contexts
    console.log("[CB Background] Could not read cookies:", e.message);
  }

  // Try each endpoint
  for (const endpoint of endpoints) {
    console.log(`[CB Background] Trying: ${endpoint}`);

    try {
      const resp = await fetch(`https://chatgpt.com${endpoint}`, {
        method: "GET",
        credentials: "include",
        headers: headers
      });

      console.log(`[CB Background] Response: ${resp.status} ${resp.statusText}`);

      if (resp.ok) {
        const data = await resp.json();
        console.log(`[CB Background] ChatGPT API success — keys: ${Object.keys(data).join(", ")}`);
        return data;
      }

      // Read error body for diagnostics
      let errorBody = "";
      try { errorBody = await resp.text(); } catch(e) {}

      console.log(`[CB Background] ${resp.status} on ${endpoint} — body: "${errorBody}"`);

      // 404 on both endpoints → try fallback approaches
      if (resp.status === 404) {
        continue; // try next endpoint
      }

      // 401/403 is terminal — no point trying other endpoints
      if (resp.status === 401) {
        throw new Error(
          "Authentication failed (401). Please log into ChatGPT and refresh the page. " +
          "Then click the extension again."
        );
      }
      if (resp.status === 403) {
        throw new Error(
          "Access denied (403). ChatGPT blocked the background request. " +
          "Try refreshing the ChatGPT page first."
        );
      }

      throw new Error(`ChatGPT API error ${resp.status}: ${errorBody.slice(0, 200)}`);
    } catch (err) {
      if (err.message.startsWith("Authentication") || err.message.startsWith("Access denied") || err.message.startsWith("ChatGPT API error")) {
        throw err; // re-throw our custom errors
      }
      console.log(`[CB Background] Fetch error on ${endpoint}:`, err.message);
      // Network error — try next endpoint
    }
  }

  // All standard endpoints returned 404. Try fallback: page context fetch
  console.log("[CB Background] Standard endpoints returned 404. Trying page-context fetch...");

  try {
    const data = await fetchViaPageContext(convId);
    if (data) return data;
  } catch (e) {
    console.log("[CB Background] Page context fetch also failed:", e.message);
  }

  // Final fallback: try to extract conversation data from the page's DOM
  console.log("[CB Background] Trying DOM-based extraction...");
  try {
    const data = await fetchViaDOM(convId);
    if (data) return data;
  } catch (e) {
    console.log("[CB Background] DOM extraction also failed:", e.message);
  }

  throw new Error(
    `ChatGPT returned 404 for conversation "${convId}". ` +
    "This may mean: (1) the conversation was deleted, " +
    "(2) it's a shared/public conversation, or " +
    "(3) you need to refresh the ChatGPT page first."
  );
}

/**
 * Fallback 1: Fetch from the page's own context using chrome.scripting.
 * This runs fetch() INSIDE the page's JavaScript context, bypassing any
 * extension-specific restrictions but inheriting the page's auth/cookies.
 */
async function fetchViaPageContext(convId) {
  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs[0];
      if (!tab || !tab.url || !tab.url.includes("chatgpt.com")) {
        reject(new Error("No ChatGPT tab"));
        return;
      }

      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        world: "MAIN",
        func: async (convId) => {
          try {
            // Fetch from the page's own context (same-origin, includes all cookies/headers)
            const endpoints = [
              `/backend-api/conversations/${convId}`,
              `/backend-api/conversation/${convId}`,
            ];

            for (const endpoint of endpoints) {
              try {
                const resp = await fetch(endpoint, {
                  credentials: "include",
                  headers: { "Accept": "application/json" }
                });

                if (resp.ok) {
                  return await resp.json();
                }
              } catch (e) {
                // continue to next endpoint
              }
            }
            return null;
          } catch (e) {
            return { __error: e.message };
          }
        },
        args: [convId]
      }).then((results) => {
        const data = results && results[0] && results[0].result;
        if (data && data.__error) {
          reject(new Error(data.__error));
        } else if (data && data.mapping) {
          resolve(data);
        } else {
          reject(new Error("Page context fetch returned no data"));
        }
      }).catch(err => {
        reject(err);
      });
    });
  });
}

/**
 * Fallback 2: Extract conversation data from the page's React state.
 * ChatGPT stores conversation data in React component state.
 * We walk the React fiber tree to find it.
 */
async function fetchViaDOM(convId) {
  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs[0];
      if (!tab || !tab.url || !tab.url.includes("chatgpt.com")) {
        reject(new Error("No ChatGPT tab"));
        return;
      }

      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        world: "MAIN",
        func: () => {
          try {
            // ChatGPT uses Next.js/React. Try to find conversation data in:
            // 1. window.__NEXT_DATA__
            // 2. React fiber tree

            if (window.__NEXT_DATA__ && window.__NEXT_DATA__.props) {
              const props = window.__NEXT_DATA__.props;
              // The conversation data might be in various locations
              if (props.pageProps && props.pageProps.conversation) {
                return props.pageProps.conversation;
              }
            }

            // Walk React fiber tree looking for conversation data
            function findInFiber(node, depth) {
              if (depth > 20) return null;
              if (!node) return null;

              // Check memoizedState and memoizedProps for conversation-like data
              if (node.memoizedProps) {
                const props = node.memoizedProps;
                // ChatGPT stores messages in various prop structures
                if (props.messages && Array.isArray(props.messages)) {
                  return { messages: props.messages, source: "fiber-props" };
                }
                if (props.conversation && props.conversation.mapping) {
                  return props.conversation;
                }
                if (props.mapping) {
                  return props;
                }
              }

              // Recurse into children
              if (node.child) {
                const result = findInFiber(node.child, depth + 1);
                if (result) return result;
              }
              if (node.sibling) {
                const result = findInFiber(node.sibling, depth + 1);
                if (result) return result;
              }

              return null;
            }

            // Find root fiber
            const rootEl = document.getElementById("__next");
            if (rootEl && rootEl._reactRootContainer) {
              const fiber = rootEl._reactRootContainer._internalRoot?.current;
              if (fiber) {
                return findInFiber(fiber, 0);
              }
            }

            return null;
          } catch (e) {
            return { __error: e.message };
          }
        }
      }).then((results) => {
        const data = results && results[0] && results[0].result;
        if (data && data.__error) {
          reject(new Error(data.__error));
        } else if (data && (data.mapping || data.messages)) {
          resolve(data);
        } else {
          reject(new Error("Could not extract conversation from page DOM"));
        }
      }).catch(err => {
        reject(err);
      });
    });
  });
}

/* ── Init ────────────────────────────────────────────────────── */

chrome.runtime.onInstalled.addListener(() => {
  console.log("[Context Bridge v5] Extension installed/updated.");
});

console.log("[Context Bridge v5] Background service worker started.");
