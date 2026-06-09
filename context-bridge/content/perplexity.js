/**
 * Context Bridge — Perplexity Content Script
 * 
 * Captures conversation messages from perplexity.ai and sends them
 * to the background service worker for storage and export.
 * 
 * DOM Structure (as of 2025):
 *   - Perplexity shows user queries at the top, then AI-generated answers
 *   - Answers include inline citations, sources, and follow-up sections
 *   - Messages are often in containers with specific data attributes
 *   - Perplexity has a "Pro Search" mode with more complex DOM
 */

(function () {
  'use strict';

  // ─── Configuration ───────────────────────────────────────────────
  const PLATFORM = 'perplexity';

  const USER_SELECTORS = [
    // Modern Perplexity (2024-2025)
    '[class*="query-text"]',
    '[class*="user-query"]',
    '[class*="prompt-query"]',
    '.pb-6 > div:first-child', // Perplexity's flex-based layout
    '[data-testid="query-container"]',
    '[class*="question-container"]',
    // Generic fallbacks
    '.message.user',
    '[data-role="user"]',
    '[class*="UserMessage"]',
  ];

  const ASSISTANT_SELECTORS = [
    '[class*="answer-container"]',
    '[class*="answer-content"]',
    '[class*="response-body"]',
    '[class*="main-answer"]',
    '[data-testid="answer-container"]',
    '.cited-response',
    '[class*="PerplexityAnswer"]',
    // Generic fallbacks
    '.message.assistant',
    '[data-role="assistant"]',
    '[class*="AssistantMessage"]',
  ];

  const CONTENT_SELECTORS = [
    '[class*="answer-content"]',
    '[class*="main-answer"]',
    '.prose',
    '.markdown',
    '[class*="response-text"]',
    '[class*="answer-text"]',
    '[class*="rich-content"]',
    '.whitespace-pre-wrap',
  ];

  // Source/citation elements to strip from content
  const SOURCE_SELECTORS = [
    '[class*="citation"]',
    '[class*="source"]',
    '[class*="reference"]',
    '[class*="related"]',
    '[class*="follow-up"]',
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
      } catch (e) { /* skip */ }
    }
    return [];
  }

  // ─── Extract Content ───────────────────────────────────────────
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
      const clone = element.cloneNode(true);
      // Remove UI chrome, source panels, and citation footers
      const uiEls = clone.querySelectorAll(
        'button, svg, [class*="copy"], [class*="action"], [class*="toolbar"], ' +
        '[class*="share"], [class*="rewrite"], [class*="follow-up-questions"], ' +
        '[class*="sources-panel"], [class*="related-questions"]'
      );
      uiEls.forEach((el) => el.remove());

      // Keep citations in content but clean them up for readability
      // Perplexity citations are valuable context
      contentEl = clone;
    }

    const text = contentEl.textContent?.trim() || '';
    if (text.length === 0 || text.length < 3) return null;

    return htmlToMarkdown(contentEl.innerHTML);
  }

  // ─── Find All Messages ──────────────────────────────────────────
  function findAllMessages() {
    const messages = [];

    const userEls = queryAll(USER_SELECTORS);
    userEls.forEach((el) => messages.push({ element: el, role: 'user' }));

    const asstEls = queryAll(ASSISTANT_SELECTORS);
    asstEls.forEach((el) => {
      const isDuplicate = messages.some((m) => m.element.contains(el) || el.contains(m.element));
      if (!isDuplicate) {
        messages.push({ element: el, role: 'assistant' });
      }
    });

    // Fallback: generic turn containers
    if (messages.length === 0) {
      const turns = document.querySelectorAll(
        '[class*="chat-turn"], [class*="conversation-turn"], [class*="message-row"], [class*="query-answer-pair"]'
      );
      turns.forEach((el) => {
        const classes = el.className || '';
        let role = null;
        if (classes.includes('query') || classes.includes('user') || classes.includes('question')) {
          role = 'user';
        } else if (classes.includes('answer') || classes.includes('response') || classes.includes('assistant')) {
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
    if (id) return `perplexity-${id}`;

    const siblings = Array.from(element.parentElement?.children || []);
    const index = siblings.indexOf(element);
    const textLen = (element.textContent || '').length;
    return `perplexity-${role}-${index}-${textLen}`;
  }

  // ─── Capture ────────────────────────────────────────────────────
  function captureMessage(element, role) {
    const id = getMessageId(element, role);
    if (seenMessageIds.has(id)) return;

    const content = extractContent(element);
    if (!content) return;

    const message = { role, content, timestamp: Date.now() };
    seenMessageIds.add(id);
    capturedMessages.push(message);
    messageCount++;

    log(`Captured ${role} message #${messageCount}`, content.substring(0, 80) + '...');

    try {
      chrome.runtime.sendMessage({ type: 'new_message', platform: PLATFORM, message });
    } catch (e) { /* ignore */ }
  }

  // ─── Capture All Existing ──────────────────────────────────────
  function captureExistingMessages() {
    const messages = findAllMessages();
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

          for (const sel of USER_SELECTORS) {
            try { if (node.matches?.(sel)) { captureMessage(node, 'user'); break; } } catch (e) { /* skip */ }
          }
          for (const sel of ASSISTANT_SELECTORS) {
            try { if (node.matches?.(sel)) { captureMessage(node, 'assistant'); break; } } catch (e) { /* skip */ }
          }

          if (node.querySelectorAll) {
            queryAll(USER_SELECTORS).filter((el) => node.contains(el)).forEach((el) => captureMessage(el, 'user'));
            queryAll(ASSISTANT_SELECTORS).filter((el) => node.contains(el)).forEach((el) => captureMessage(el, 'assistant'));
          }
        }

        if (mutation.type === 'characterData' || mutation.type === 'childList') {
          updateStreamingAssistant();
        }
      }
    });

    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    log('Started observing DOM mutations');
  }

  function stopObserving() {
    if (observer) { observer.disconnect(); observer = null; log('Stopped observing'); }
  }

  // ─── Update Streaming ──────────────────────────────────────────
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
      chrome.runtime.sendMessage({ type: 'update_message', platform: PLATFORM, message: lastMsg, messageIndex: capturedMessages.length - 1 });
    } catch (e) { /* ignore */ }
  }

  // ─── Recording Control ──────────────────────────────────────────
  function startRecording() {
    if (isRecording) return;
    isRecording = true;
    capturedMessages = [];
    messageCount = 0;
    seenMessageIds.clear();
    setTimeout(() => { captureExistingMessages(); startObserving(); log('Recording started'); }, 500);
  }

  function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    stopObserving();
    log(`Recording stopped. ${messageCount} messages.`);
    return { platform: PLATFORM, messages: capturedMessages, messageCount };
  }

  function getStatus() {
    return { type: 'status', platform: PLATFORM, isRecording, messageCount, url: window.location.href };
  }

  // ─── Message Listener ──────────────────────────────────────────
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    switch (message.type) {
      case 'start_recording': startRecording(); sendResponse({ success: true }); break;
      case 'stop_recording': sendResponse({ success: true, ...stopRecording() }); break;
      case 'get_status': sendResponse(getStatus()); break;
      case 'ping': sendResponse({ alive: true, platform: PLATFORM }); break;
    }
    return true;
  });

  log('Content script loaded, waiting for commands...');
})();
