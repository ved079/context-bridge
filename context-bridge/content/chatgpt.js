// Context Bridge v2 - ChatGPT API scraper
// Uses ChatGPT's backend-api with mapping tree traversal

(async function ChatGPTScraper() {
  // Extract conversation ID from URL: /c/{uuid}
  function getConversationId() {
    const match = window.location.pathname.match(/\/c\/([a-f0-9-]+)/);
    return match ? match[1] : null;
  }

  // Fetch conversation data from ChatGPT's backend API
  async function fetchConversation(convId) {
    // Try the conversations endpoint that returns the mapping tree
    const url = `https://chatgpt.com/backend-api/conversations/${convId}`;

    const resp = await fetch(url, {
      credentials: 'include',
      headers: {
        'Accept': 'application/json'
      }
    });

    if (!resp.ok) {
      // Fallback: try the shared conversations endpoint
      const fallbackUrl = `https://chatgpt.com/backend-api/conversation/${convId}`;
      const fallbackResp = await fetch(fallbackUrl, {
        credentials: 'include'
      });
      if (!fallbackResp.ok) {
        throw new Error(`ChatGPT API returned ${resp.status} (${resp.statusText})`);
      }
      return fallbackResp.json();
    }

    return resp.json();
  }

  // Find the root message node in the mapping tree
  function findRootNode(mapping) {
    // The mapping is keyed by message IDs, root has no parent
    const ids = Object.keys(mapping);
    for (const id of ids) {
      const node = mapping[id];
      // Check if this node is referenced as a child by another node
      let isChild = false;
      for (const otherId of ids) {
        const otherNode = mapping[otherId];
        if (otherNode.children && otherNode.children.includes(id)) {
          isChild = true;
          break;
        }
      }
      if (!isChild) return id;
    }
    // Fallback: return first key
    return ids[0];
  }

  // Traverse the mapping tree and extract messages in order
  function traverseMapping(mapping) {
    if (!mapping || typeof mapping !== 'object') return [];

    const messages = [];
    const visited = new Set();

    function walk(id) {
      if (!id || visited.has(id)) return;
      visited.add(id);

      const node = mapping[id];
      if (!node) return;

      const message = node.message;
      if (message && message.content && message.content.parts) {
        const role = message.author?.role === 'user' ? 'user' : 'assistant';
        const parts = message.content.parts;

        // Separate text content and tool calls
        let textContent = '';
        const tools = [];

        for (const part of parts) {
          if (typeof part === 'string') {
            textContent += part;
          } else if (part && typeof part === 'object') {
            // Tool call / function call
            if (part.content_type === 'text') {
              textContent += part.text || '';
            } else if (part.name) {
              tools.push({
                name: part.name,
                input: JSON.stringify(part, null, 2),
                description: part.description || ''
              });
            } else {
              textContent += JSON.stringify(part, null, 2);
            }
          }
        }

        if (textContent.trim() || tools.length > 0) {
          messages.push({
            role,
            content: textContent.trim(),
            timestamp: message.create_time ? new Date(message.create_time * 1000).toISOString() : null,
            tools: tools.length > 0 ? tools : undefined
          });
        }
      }

      // Follow children
      if (node.children && Array.isArray(node.children)) {
        for (const childId of node.children) {
          walk(childId);
        }
      }
    }

    const rootNodeId = findRootNode(mapping);
    walk(rootNodeId);

    return messages;
  }

  // Parse ChatGPT's API response
  function parseConversation(data) {
    // ChatGPT response has a "mapping" object (tree structure)
    if (data.mapping) {
      const messages = traverseMapping(data.mapping);
      const title = data.title || 'Untitled Conversation';
      const model = data.model_slug || data.model || 'gpt-unknown';
      return { title, model, messages };
    }

    // Fallback: flat messages array (older format)
    if (data.messages && Array.isArray(data.messages)) {
      const messages = data.messages
        .filter(msg => msg.content)
        .map(msg => ({
          role: msg.author?.role === 'user' ? 'user' : 'assistant',
          content: msg.content.parts ? msg.content.parts.filter(p => typeof p === 'string').join('\n') : msg.content.text || '',
          timestamp: msg.create_time ? new Date(msg.create_time * 1000).toISOString() : null
        }));
      return {
        title: data.title || 'Untitled Conversation',
        model: data.model_slug || 'gpt-unknown',
        messages
      };
    }

    throw new Error('Could not parse ChatGPT conversation data');
  }

  // Main capture function exposed globally
  window.CBCapture = async function () {
    const convId = getConversationId();
    if (!convId) {
      throw new Error('No conversation ID found in URL. Make sure you\'re on a ChatGPT conversation page (/c/...).');
    }

    const rawData = await fetchConversation(convId);
    const parsed = parseConversation(rawData);

    // Store in chrome storage for popup access
    await CBCommon.clearSession();
    await CBCommon.setSession({
      messages: parsed.messages,
      title: parsed.title,
      model: parsed.model,
      platform: 'chatgpt',
      captured: true,
      timestamp: new Date().toISOString()
    });

    return {
      title: parsed.title,
      model: parsed.model,
      messageCount: parsed.messages.length,
      platform: 'chatgpt'
    };
  };

  console.log('[Context Bridge] ChatGPT scraper loaded (API mode)');
})();
