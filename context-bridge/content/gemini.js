/**
 * Context Bridge — Google Gemini Content Script
 * 
 * Captures conversation messages from gemini.google.com and sends them
 * to the background service worker for storage and export.
 * 
 * DOM Structure (as of 2025):
 *   - User query input: typically in a form/textarea area
 *   - Model responses: rendered in containers with role="model" or class-based selectors
 *   - Message content: often in `.markdown-main-content` or similar prose containers
 *   - Gemini may use custom web components or shadow DOM in some areas
 */

(function () {
  'use strict';

  // ─── Configuration ───────────────────────────────────────────────
  const PLATFORM = 'gemini';

  // Multiple selector strategies for Gemini's various DOM versions
  const USER_SELECTORS = [
    // Modern Gemini (2024-2025) — user query containers
    '.user-query-text',
    '[class*="user-query"]',
    '.query-text',
    // Gemini uses data attributes in some versions
    '[data-role="user"]',
    'message-content[sender="user"]',
    '[class*="UserMessage"]',
    // Fallback: look for containers preceding model responses
    '.turn-container:has(+ .model-response)',
  ];

  const ASSISTANT_SELECTORS = [
    // Modern Gemini — model response containers
    '.model-response',
    '[class*="model-response"]',
    '.markdown-main-content',
    // Gemini data attributes
    '[data-role="model"]',
    'message-content[sender="model"]',
    '[class*="ModelResponse"]',
    // Response text area
    '.response-container',
    '[class*="response-text"]',
  ];

  const CONTENT_SELECTORS = [
    '.markdown-main-content',
    '.markdown',
    '.prose',
    '.message-content',
    '[class*="response-text"]',
    '[class*="content-text"]',
    '.whitespace-pre-wrap',
  ];

  // ─── State ─────────────────────────────────────────────────────
  let isRecording = false;
  let capturedMessages = [];
  let observer = null;
  let messageCount = 0;
  const seenMessageIds = new Set();

  // ─── Logging ────────────────────────────────────────────────────
  function log(...args) {
    console.log(`[Context Bridge:${PLATFORM}]`, ...args);
  }

  // ─── HTML → Markdown Conversion ────────────────────────────────
  function htmlToMarkdown(html) {
    if (!html || typeof html !== 'string' || html.trim().length === 0) return '';
    try {
      return window.ContextBridgeHTML2MD(html);
    } catch (e) {
      log('Markdown conversion error:', e);
      return html.replace(/<[^>]*>/g, '').trim();
    }
  }

  // ─── Query with Fallback Selectors ─────────────────────────────
  function queryAll(selectorList) {
    for (const sel of selectorList) {
      try {
        const elements = document.querySelectorAll(sel);
        if (elements.length > 0) return elements;
      } catch (e) {
        // Invalid selector — skip
      }
    }
    return [];
  }

  // ─── Extract Content from a Gemini Message Element ────────────────
  function extractContent(element) {
    let contentEl = null;

    for (const sel of CONTENT_SELECTORS) {
      const el = element.querySelector(sel);
      if (el && el.textContent?.trim().length > 5) {
        contentEl = el;
        break;
      }
    }

    if (!contentEl) {
      // Try the element itself, stripping UI chrome
      const clone = element.cloneNode(true);
      const uiEls = clone.querySelectorAll(
        'button, [class*="copy"], [class*="action"], [class*="toolbar"], svg, [class*="source"], [class*="chip"], [class*="suggestion"]'
      );
      uiEls.forEach((el) => el.remove());
      contentEl = clone;
    }

    const text = contentEl.textContent?.trim() || '';
    if (text.length === 0 || text.length < 3) return null;

    return htmlToMarkdown(contentEl.innerHTML);
  }

  // ─── Find All Message Turns ──────────────────────────────────────
  function findAllMessages() {
    const messages = [];

    // Strategy 1: Find user queries
    const userEls = queryAll(USER_SELECTORS);
    userEls.forEach((el) => {
      messages.push({ element: el, role: 'user' });
    });

    // Strategy 2: Find model responses
    const asstEls = queryAll(ASSISTANT_SELECTORS);
    asstEls.forEach((el) => {
      // Avoid duplicating if the element is a sub-container of an already found one
      const isDuplicate = messages.some((m) => m.element.contains(el) || el.contains(m.element));
      if (!isDuplicate) {
        messages.push({ element: el, role: 'assistant' });
      }
    });

    // Strategy 3: Look for general conversation containers if nothing found yet
    if (messages.length === 0) {
      const conversationEls = document.querySelectorAll(
        '[class*="conversation-turn"], [class*="chat-turn"], [class*="turn-container"], .turn'
      );
      conversationEls.forEach((el) => {
        const classes = el.className || '';
        let role = null;
        if (classes.includes('user') || classes.includes('query') || classes.includes('human')) {
          role = 'user';
        } else if (classes.includes('model') || classes.includes('response') || classes.includes('assistant')) {
          role = 'assistant';
        }
        if (role) messages.push({ element: el, role });
      });
    }

    return messages;
  }

  // ─── Generate Stable ID ────────────────────────────────────────
  function getMessageId(element, role) {
    const id = element.getAttribute('data-message-id')
      || element.getAttribute('id')
      || element.getAttribute('data-turn-id');

    if (id) return `gemini-${id}`;

    const siblings = Array.from(element.parentElement?.children || []);
    const index = siblings.indexOf(element);
    const textLen = (element.textContent || '').length;
    return `gemini-${role}-${index}-${textLen}`;
  }

  // ─── Capture a Single Message ───────────────────────────────────
  function captureMessage(element, role) {
    const id = getMessageId(element, role);
    if (seenMessageIds.has(id)) return;

    const content = extractContent(element);
    if (!content) return;

    const message = {
      role,
      content,
      timestamp: Date.now(),
    };

    seenMessageIds.add(id);
    capturedMessages.push(message);
    messageCount++;

    log(`Captured ${role} message #${messageCount}`, content.substring(0, 80) + '...');

    try {
      chrome.runtime.sendMessage({
        type: 'new_message',
        platform: PLATFORM,
        message,
      });
    } catch (e) {
      // Extension context invalidated
    }
  }

  // ─── Capture All Existing Messages ──────────────────────────────
  function captureExistingMessages() {
    const messages = findAllMessages();

    // Sort by DOM position
    messages.sort((a, b) => {
      const pos = a.element.compareDocumentPosition(b.element);
      if (pos & Node.DOCUMENT_POSITION_FOLLOWING) return -1;
      if (pos & Node.DOCUMENT_POSITION_PRECEDING) return 1;
      return 0;
    });

    messages.forEach(({ element, role }) => captureMessage(element, role));
    log(`Captured ${messageCount} existing messages`);
  }

  // ─── MutationObserver ───────────────────────────────────────────
  function startObserving() {
    if (observer) return;

    observer = new MutationObserver((mutations) => {
      if (!isRecording) return;

      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType !== Node.ELEMENT_NODE) continue;

          // Check if it's a user message
          let matched = false;
          for (const sel of USER_SELECTORS) {
            try {
              if (node.matches?.(sel)) {
                captureMessage(node, 'user');
                matched = true;
                break;
              }
            } catch (e) { /* skip */ }
          }

          // Check if it's an assistant message
          if (!matched) {
            for (const sel of ASSISTANT_SELECTORS) {
              try {
                if (node.matches?.(sel)) {
                  captureMessage(node, 'assistant');
                  matched = true;
                  break;
                }
              } catch (e) { /* skip */ }
            }
          }

          // Look for messages inside the new node
          if (node.querySelectorAll) {
            const userMsgs = queryAll(USER_SELECTORS).filter((el) => node.contains(el));
            const asstMsgs = queryAll(ASSISTANT_SELECTORS).filter((el) => node.contains(el));

            userMsgs.forEach((el) => captureMessage(el, 'user'));
            asstMsgs.forEach((el) => captureMessage(el, 'assistant'));
          }
        }

        // Handle streaming updates
        if (mutation.type === 'characterData' || mutation.type === 'childList') {
          updateStreamingAssistant();
        }
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
    });

    log('Started observing DOM mutations');
  }

  function stopObserving() {
    if (observer) {
      observer.disconnect();
      observer = null;
      log('Stopped observing DOM mutations');
    }
  }

  // ─── Update Streaming Assistant Message ────────────────────────
  function updateStreamingAssistant() {
    if (capturedMessages.length === 0) return;

    const lastMsg = capturedMessages[capturedMessages.length - 1];
    if (lastMsg.role !== 'assistant') return;

    const asstEls = queryAll(ASSISTANT_SELECTORS);
    if (asstEls.length === 0) return;

    const lastEl = asstEls[asstEls.length - 1];
    const content = extractContent(lastEl);
    if (!content || content === lastMsg.content) return;

    lastMsg.content = content;
    lastMsg.timestamp = Date.now();

    try {
      chrome.runtime.sendMessage({
        type: 'update_message',
        platform: PLATFORM,
        message: lastMsg,
        messageIndex: capturedMessages.length - 1,
      });
    } catch (e) {
      // Extension context invalidated
    }
  }

  // ─── Start Recording ────────────────────────────────────────────
  function startRecording() {
    if (isRecording) return;
    isRecording = true;
    capturedMessages = [];
    messageCount = 0;
    seenMessageIds.clear();

    setTimeout(() => {
      captureExistingMessages();
      startObserving();
      log('Recording started');
    }, 500);
  }

  // ─── Stop Recording ────────────────────────────────────────────
  function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    stopObserving();

    log(`Recording stopped. ${messageCount} messages captured.`);
    return { platform: PLATFORM, messages: capturedMessages, messageCount };
  }

  // ─── Get Status ────────────────────────────────────────────────
  function getStatus() {
    return {
      type: 'status',
      platform: PLATFORM,
      isRecording,
      messageCount,
      url: window.location.href,
    };
  }

  // ─── Listen for Messages ────────────────────────────────────────
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    switch (message.type) {
      case 'start_recording':
        startRecording();
        sendResponse({ success: true });
        break;
      case 'stop_recording':
        const result = stopRecording();
        sendResponse({ success: true, ...result });
        break;
      case 'get_status':
        sendResponse(getStatus());
        break;
      case 'ping':
        sendResponse({ alive: true, platform: PLATFORM });
        break;
    }
    return true;
  });

  log('Content script loaded, waiting for commands...');
})();
