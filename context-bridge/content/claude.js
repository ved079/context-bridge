// Context Bridge v2 - Claude.ai API scraper
// Uses Claude's internal API to extract structured conversation data

(async function ClaudeScraper() {
  // Extract conversation ID from URL: https://claude.ai/chat/{convId}
  function getConversationId() {
    const match = window.location.pathname.match(/\/chat\/([a-f0-9-]+)/);
    return match ? match[1] : null;
  }

  // Try multiple methods to get the org ID
  async function getOrgId() {
    // Method 1: Cookie lastActiveOrg
    const cookie = document.cookie
      .split(';')
      .map(c => c.trim())
      .find(c => c.startsWith('lastActiveOrg='));
    if (cookie) {
      try {
        return JSON.parse(decodeURIComponent(cookie.split('=')[1]));
      } catch (e) {
        // fall through
      }
    }

    // Method 2: Fetch from API - list organizations
    try {
      const resp = await fetch('https://claude.ai/api/organizations', {
        credentials: 'include'
      });
      if (resp.ok) {
        const orgs = await resp.json();
        if (orgs && orgs.length > 0) {
          // Find the active/first org
          const activeOrg = orgs.find(o => o.active) || orgs[0];
          if (activeOrg && activeOrg.uuid) return activeOrg.uuid;
        }
      }
    } catch (e) {
      console.warn('[Context Bridge] Could not fetch orgs list:', e);
    }

    // Method 3: Extract from page context
    try {
      const scripts = document.querySelectorAll('script');
      for (const script of scripts) {
        const text = script.textContent;
        const match = text.match(/"organization":\s*"([a-f0-9-]+)"/);
        if (match) return match[1];
      }
    } catch (e) {
      // fall through
    }

    return null;
  }

  // Fetch conversation data from Claude's API
  async function fetchConversation(convId, orgId) {
    const url = `https://claude.ai/api/organizations/${orgId}/chat_conversations/${convId}`;
    const resp = await fetch(url, { credentials: 'include' });

    if (!resp.ok) {
      throw new Error(`Claude API returned ${resp.status} (${resp.statusText})`);
    }

    return resp.json();
  }

  // Parse Claude's API response into our standard format
  function parseConversation(data) {
    if (!data || !data.chat_messages) {
      throw new Error('No chat_messages found in Claude API response');
    }

    const title = data.name || data.title || 'Untitled Conversation';
    const model = data.model || 'claude-unknown';

    const messages = data.chat_messages
      .filter(msg => msg && (msg.text || msg.content))
      .map(msg => {
        const role = msg.sender === 'human' ? 'user' : 'assistant';
        const content = msg.text || msg.content || '';
        const timestamp = msg.created_at || msg.timestamp || null;

        // Extract tool usage info if present
        const tools = [];
        if (msg.tool_uses && msg.tool_uses.length > 0) {
          for (const tool of msg.tool_uses) {
            tools.push({
              name: tool.name || 'unknown_tool',
              input: tool.input || ''
            });
          }
        }

        return {
          role,
          content,
          timestamp,
          tools: tools.length > 0 ? tools : undefined
        };
      });

    return { title, model, messages };
  }

  // Main capture function exposed globally
  window.CBCapture = async function () {
    const convId = getConversationId();
    if (!convId) {
      throw new Error('No conversation ID found in URL. Make sure you\'re on a Claude conversation page.');
    }

    const orgId = await getOrgId();
    if (!orgId) {
      throw new Error('Could not determine organization ID. Try reloading the page.');
    }

    const rawData = await fetchConversation(convId, orgId);
    const parsed = parseConversation(rawData);

    // Store in chrome storage for popup access
    await CBCommon.clearSession();
    await CBCommon.setSession({
      messages: parsed.messages,
      title: parsed.title,
      model: parsed.model,
      platform: 'claude',
      captured: true,
      timestamp: new Date().toISOString()
    });

    return {
      title: parsed.title,
      model: parsed.model,
      messageCount: parsed.messages.length,
      platform: 'claude'
    };
  };

  console.log('[Context Bridge] Claude scraper loaded (API mode)');
})();
