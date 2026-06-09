/**
 * Context Bridge — Markdown Generator
 * 
 * Takes session data and produces well-structured Markdown exports.
 * Supports both "full" and "condensed" export modes.
 * 
 * Usage:
 *   const full = ContextBridgeMarkdown.generateFull(session);
 *   const condensed = ContextBridgeMarkdown.generateCondensed(session);
 * 
 * Session format:
 *   {
 *     platform: "chatgpt",
 *     messages: [{ role: "user"|"assistant", content: "markdown string", timestamp: 1704326400000 }],
 *     startedAt: 1704326400000
 *   }
 */

const ContextBridgeMarkdown = (() => {
  'use strict';

  // ─── Constants ───────────────────────────────────────────────────

  const PLATFORM_LABELS = {
    chatgpt: 'ChatGPT',
    claude: 'Claude',
    gemini: 'Google Gemini',
    copilot: 'Microsoft Copilot',
    perplexity: 'Perplexity',
  };

  const ROLE_LABELS = {
    user: 'User',
    assistant: 'Assistant',
    system: 'System',
  };

  // Pleasantries / filler to strip in condensed mode
  const PLEASANTRY_PATTERNS = [
    /^(thanks|thank you|thx|ty|cheers|great|awesome|perfect|excellent|nice|cool|wonderful|amazing|fantastic|brilliant|super)[\s!.,]*$/i,
    /^(sure|of course|no problem|you're welcome|my pleasure|happy to help|glad i could help|certainly|absolutely)[\s!.,]*$/i,
    /^(hi|hello|hey|greetings|good morning|good afternoon|good evening|howdy)[\s!.,]*$/i,
    /^(ok|okay|got it|understood|makes sense|i see|right|alright)[\s!.,]*$/i,
  ];

  const PLEASANTRY_STARTERS = [
    /^(thanks|thank you|thx|ty|i appreciate)[\s]/i,
    /^(sure|of course|no problem|you're welcome|my pleasure|happy to help)[\s]/i,
    /^(great|awesome|perfect|excellent|nice|wonderful|amazing|that's great|that's awesome|that's perfect)[\s]/i,
  ];

  // ─── Helpers ─────────────────────────────────────────────────────

  /**
   * Format a timestamp to a readable date/time string
   */
  function formatDateTime(timestamp) {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    const pad = (n) => String(n).padStart(2, '0');

    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
  }

  /**
   * Format duration from milliseconds to human-readable string
   */
  function formatDuration(startMs, endMs) {
    if (!startMs || !endMs) return 'Unknown';
    const diffMs = Math.max(0, endMs - startMs);
    const totalSec = Math.floor(diffMs / 1000);
    const hours = Math.floor(totalSec / 3600);
    const minutes = Math.floor((totalSec % 3600) / 60);
    const seconds = totalSec % 60;

    if (hours > 0) {
      return `~${hours}h ${minutes}m`;
    }
    if (minutes > 0) {
      return `~${minutes} minutes`;
    }
    return `~${seconds} seconds`;
  }

  /**
   * Format a timestamp to HH:MM for inline message timestamps
   */
  function formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }

  /**
   * Check if a message is primarily a pleasantry/filler
   */
  function isPleasantry(content) {
    const trimmed = content.trim();
    // Single-line message matching a pleasantries pattern
    if (!trimmed.includes('\n')) {
      for (const pattern of PLEASANTRY_PATTERNS) {
        if (pattern.test(trimmed)) return true;
      }
    }
    // Multi-line message that starts with a pleasantries pattern
    for (const pattern of PLEASANTRY_STARTERS) {
      if (pattern.test(trimmed)) return true;
    }
    return false;
  }

  /**
   * Check if a message likely contains code
   */
  function containsCode(content) {
    return /```[\s\S]*?```/.test(content) || /`[^`]+`/.test(content);
  }

  /**
   * Extract file mentions from message content
   */
  function extractFileMentions(content) {
    const matches = content.match(/`?[\w./~][\w./\-~]*\.\w{1,10}`?/g) || [];
    return matches.filter((m) => {
      // Filter out obvious non-file patterns
      return !/\.(com|org|net|io|ai|co|dev|http|html)$/i.test(m) && m.length > 3;
    });
  }

  /**
   * Check if content likely contains an error message
   */
  function containsError(content) {
    const patterns = [
      /\berror\b/i,
      /\bexception\b/i,
      /\bfailed\b/i,
      /\bfailure\b/i,
      /\btraceback\b/i,
      /\bstack\s*trace\b/i,
      /\bunhandled\b/i,
      /\bTypeError\b/i,
      /\bReferenceError\b/i,
      /\bSyntaxError\b/i,
      /exit code \d+/i,
      /command not found/i,
      /permission denied/i,
      /ENOENT/i,
      /EACCES/i,
    ];
    return patterns.some((p) => p.test(content));
  }

  // ─── Full Export ──────────────────────────────────────────────────

  /**
   * Generate a full, detailed Markdown export of a session
   */
  function generateFull(session) {
    const platform = PLATFORM_LABELS[session.platform] || session.platform || 'Unknown';
    const messages = session.messages || [];
    const exportedAt = Date.now();
    const msgCount = messages.length;
    const duration = formatDuration(session.startedAt, exportedAt);

    // ── Header ──
    let md = '';
    md += `# Context Bridge — Session Export\n\n`;
    md += `**Platform:** ${platform}\n`;
    md += `**Exported:** ${formatDateTime(exportedAt)}\n`;
    md += `**Messages:** ${msgCount}\n`;
    md += `**Duration:** ${duration}\n\n`;
    md += `---\n\n`;

    // ── Summary ──
    md += generateSummary(session);

    // ── Full Conversation ──
    md += `## Full Conversation\n\n`;

    for (let i = 0; i < messages.length; i++) {
      const msg = messages[i];
      const roleLabel = ROLE_LABELS[msg.role] || msg.role;
      const timeStr = formatTime(msg.timestamp);

      md += `### ${roleLabel}`;
      if (timeStr) md += ` _(${timeStr})_`;
      md += `\n\n`;

      // Ensure content is properly separated
      const content = msg.content || '';
      md += content;
      if (!content.endsWith('\n')) md += '\n';
      md += '\n';

      // Add separator between messages (except after the last one)
      if (i < messages.length - 1) {
        md += `---\n\n`;
      }
    }

    // ── Footer ──
    md += `\n---\n\n`;
    md += `_Exported by Context Bridge v1.0.0 on ${formatDateTime(exportedAt)}_\n`;

    return md;
  }

  /**
   * Generate the auto-generated summary section
   */
  function generateSummary(session) {
    const messages = session.messages || [];
    const userMsgs = messages.filter((m) => m.role === 'user');
    const asstMsgs = messages.filter((m) => m.role === 'assistant');

    let md = `## Conversation Summary\n\n`;

    if (userMsgs.length === 0) {
      md += `> No user messages captured.\n\n`;
      return md;
    }

    // Extract first few user queries as overview
    const firstUserMsgs = userMsgs.slice(0, Math.min(3, userMsgs.length));
    md += `> **Topics discussed:**\n>\n`;

    firstUserMsgs.forEach((msg, i) => {
      const preview = (msg.content || '').substring(0, 120).replace(/\n/g, ' ').trim();
      md += `> ${i + 1}. ${preview}${preview.length >= 120 ? '...' : ''}\n>\n`;
    });

    if (userMsgs.length > 3) {
      md += `> ... and ${userMsgs.length - 3} more messages\n>\n`;
    }

    md += `\n`;

    return md;
  }

  // ─── Condensed Export ─────────────────────────────────────────────

  /**
   * Generate a condensed, actionable summary export
   * Strips pleasantries and focuses on substance
   */
  function generateCondensed(session) {
    const platform = PLATFORM_LABELS[session.platform] || session.platform || 'Unknown';
    const messages = session.messages || [];
    const exportedAt = Date.now();
    const msgCount = messages.length;
    const duration = formatDuration(session.startedAt, exportedAt);

    // ── Header ──
    let md = '';
    md += `# Context Bridge — Condensed Export\n\n`;
    md += `**Platform:** ${platform}\n`;
    md += `**Exported:** ${formatDateTime(exportedAt)}\n`;
    md += `**Original Messages:** ${msgCount}\n`;
    md += `**Duration:** ${duration}\n\n`;
    md += `---\n\n`;

    // Filter out pleasantries for condensed view
    const substantial = messages.filter((m) => !isPleasantry(m.content));

    // ── Key Topics / Decisions ──
    md += `## Key Topics & Decisions\n\n`;

    const userSubstantial = substantial.filter((m) => m.role === 'user');
    if (userSubstantial.length === 0) {
      md += `> No substantive user messages found.\n\n`;
    } else {
      md += `> **Topics raised:**\n>\n`;
      userSubstantial.forEach((msg, i) => {
        const preview = (msg.content || '').substring(0, 150).replace(/\n/g, ' ').trim();
        md += `> ${i + 1}. ${preview}${preview.length >= 150 ? '...' : ''}\n>\n`;
      });
      md += `\n`;
    }

    // ── Code Changes Discussed ──
    md += `## Code Discussed\n\n`;
    const codeMsgs = substantial.filter((m) => containsCode(m.content));

    if (codeMsgs.length === 0) {
      md += `> No code blocks found in conversation.\n\n`;
    } else {
      let codeIdx = 0;
      for (const msg of codeMsgs) {
        // Extract just the code blocks from this message
        const codeBlocks = extractCodeBlocks(msg.content);
        for (const block of codeBlocks) {
          codeIdx++;
          const roleLabel = ROLE_LABELS[msg.role] || msg.role;
          md += `### Code Block ${codeIdx} _(${roleLabel})_\n\n`;
          md += `${block.lang ? `\`${block.lang}\`` : 'Code'}:\n\n`;
          md += `${block.code}\n\n`;
        }
      }
    }

    // ── Files Mentioned ──
    md += `## Files Mentioned\n\n`;
    const allFiles = new Set();
    substantial.forEach((m) => {
      extractFileMentions(m.content).forEach((f) => allFiles.add(f));
    });

    if (allFiles.size === 0) {
      md += `> No file paths detected.\n\n`;
    } else {
      Array.from(allFiles).sort().forEach((f) => {
        md += `- \`${f}\`\n`;
      });
      md += `\n`;
    }

    // ── Error Messages ──
    md += `## Errors & Issues\n\n`;
    const errorMsgs = substantial.filter((m) => containsError(m.content));

    if (errorMsgs.length === 0) {
      md += `> No error messages detected.\n\n`;
    } else {
      errorMsgs.forEach((msg, i) => {
        const roleLabel = ROLE_LABELS[msg.role] || msg.role;
        const preview = (msg.content || '').substring(0, 300).replace(/\n/g, '\n> ');
        md += `> **${roleLabel}** (message ${i + 1}):\n> ${preview}...\n>\n`;
      });
      md += `\n`;
    }

    // ── Pending Tasks / Questions ──
    md += `## Substantive Conversation\n\n`;
    md += `> The following messages exclude pleasantries and filler.\n\n`;

    for (let i = 0; i < substantial.length; i++) {
      const msg = substantial[i];
      const roleLabel = ROLE_LABELS[msg.role] || msg.role;
      const timeStr = formatTime(msg.timestamp);

      md += `### ${roleLabel}`;
      if (timeStr) md += ` _(${timeStr})_`;
      md += `\n\n`;

      md += msg.content || '';
      if (!msg.content?.endsWith('\n')) md += '\n';
      md += '\n';

      if (i < substantial.length - 1) {
        md += `---\n\n`;
      }
    }

    // ── Footer ──
    md += `\n---\n\n`;
    md += `_Condensed export by Context Bridge v1.0.0 on ${formatDateTime(exportedAt)}_\n`;
    md += `_Filtered ${msgCount - substantial.length} pleasantries from ${msgCount} original messages_\n`;

    return md;
  }

  /**
   * Extract code blocks from markdown content
   */
  function extractCodeBlocks(content) {
    const blocks = [];
    const regex = /```(\w*)\n([\s\S]*?)```/g;
    let match;

    while ((match = regex.exec(content)) !== null) {
      blocks.push({
        lang: match[1] || '',
        code: match[2].trim(),
      });
    }

    return blocks;
  }

  // ─── Public API ──────────────────────────────────────────────────

  return {
    generateFull,
    generateCondensed,
    formatDateTime,
    formatDuration,
    PLATFORM_LABELS,
    ROLE_LABELS,
  };
})();

// Also expose as a global for use in the popup (since it's loaded via script tag)
if (typeof window !== 'undefined') {
  window.ContextBridgeMarkdown = ContextBridgeMarkdown;
}
