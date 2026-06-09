/**
 * Context Bridge — Markdown Generator (v4)
 * Converts API-fetched conversation data into clean exports.
 *
 * Supports: Claude, ChatGPT, Z.ai
 *
 * Key principle: TEXT content and TOOL calls are SEPARATED.
 * - `content` = only what the AI said to the user (text blocks)
 * - `tools` = tool calls (file ops, bash, etc.) — shown separately
 * - No DOM noise, no leaked UI elements, no truncated streaming artifacts.
 *
 * Three export formats:
 *  1. Full Markdown — headers, timestamps, tools in collapsible sections
 *  2. Compact Markdown — minimal, token-saving for pasting into another AI
 *  3. JSON — structured data with all tool details preserved
 */

const MarkdownGenerator = (() => {

  /* ═══════════════════════════════════════════════════════════════
     1. FULL MARKDOWN — Complete export with metadata & tool details
     ═══════════════════════════════════════════════════════════════ */

  function generate(data) {
    const { messages = [], title, model, platform } = data;
    const lines = [];

    // ── Header ───────────────────────────────────────────────
    lines.push(`# ${title || "Conversation Export"}`);
    lines.push("");
    lines.push(`> **Source**: ${formatPlatform(model, platform)}`);
    lines.push(`> **Messages**: ${messages.length}`);

    if (messages.length > 0) {
      const firstTs = messages[0].timestamp;
      const lastTs = messages[messages.length - 1].timestamp;
      if (firstTs) lines.push(`> **Started**: ${formatDate(firstTs)}`);
      if (lastTs) lines.push(`> **Ended**: ${formatDate(lastTs)}`);
    }

    // Count tools
    const totalTools = messages.reduce((n, m) => n + (m.tools ? m.tools.length : 0), 0);
    if (totalTools > 0) {
      lines.push(`> **Tool Calls**: ${totalTools}`);
    }

    lines.push("");
    lines.push("---");
    lines.push("");

    // ── Messages ─────────────────────────────────────────────
    messages.forEach((msg, i) => {
      const label = formatRole(msg.role);
      const time = msg.timestamp ? ` — ${formatTime(msg.timestamp)}` : "";

      lines.push(`## ${label}${time}`);
      lines.push("");

      // Text content
      if (msg.content) {
        lines.push(msg.content);
        lines.push("");
      } else if (msg.role === "assistant") {
        lines.push("*[No text response — only tool calls]*");
        lines.push("");
      }

      // Tool calls (shown as collapsible details)
      if (msg.tools && msg.tools.length > 0) {
        lines.push(`<details>`);
        lines.push(`<summary>🔧 ${msg.tools.length} tool call${msg.tools.length > 1 ? "s" : ""}</summary>`);
        lines.push("");

        for (const tool of msg.tools) {
          lines.push(formatToolCall(tool));
          lines.push("");
        }

        lines.push(`</details>`);
        lines.push("");
      }

      // Tool results (if present)
      if (msg.toolResults && msg.toolResults.length > 0) {
        lines.push(`<details>`);
        lines.push(`<summary>📋 ${msg.toolResults.length} tool result${msg.toolResults.length > 1 ? "s" : ""}</summary>`);
        lines.push("");

        for (const result of msg.toolResults) {
          if (result.content) {
            const preview = result.content.length > 500
              ? result.content.slice(0, 500) + "\n... (truncated)"
              : result.content;
            lines.push("```");
            lines.push(preview);
            lines.push("```");
            lines.push("");
          }
        }

        lines.push(`</details>`);
        lines.push("");
      }

      // Separator between messages
      if (i < messages.length - 1) {
        lines.push("---");
        lines.push("");
      }
    });

    // ── Footer ───────────────────────────────────────────────
    lines.push(FOOTER);

    return lines.join("\n");
  }

  /* ═══════════════════════════════════════════════════════════════
     2. COMPACT MARKDOWN — Token-saving for pasting into another AI
     ═══════════════════════════════════════════════════════════════ */

  function generateCompact(data) {
    const { messages = [], title } = data;
    const lines = [];

    lines.push(`Here's my previous conversation titled "${title || "Untitled"}". Please continue from where we left off.`);
    lines.push("");

    messages.forEach((msg) => {
      const label = msg.role === "user" ? "**User**" : "**Assistant**";
      lines.push(`${label}:`);
      lines.push("");

      if (msg.content) {
        lines.push(msg.content);
      }

      // Include tool call info briefly (for Claude Code conversations)
      if (msg.tools && msg.tools.length > 0) {
        lines.push("");
        lines.push(`*[Used ${msg.tools.length} tool${msg.tools.length > 1 ? "s" : ""}: ${msg.tools.map(t => t.name).join(", ")}]*`);
      }

      lines.push("");
    });

    lines.push(FOOTER_COMPACT);

    return lines.join("\n");
  }

  /* ═══════════════════════════════════════════════════════════════
     3. JSON — Structured data with all details
     ═══════════════════════════════════════════════════════════════ */

  function generateJSON(data) {
    const { messages = [], title, model, platform } = data;

    // Build clean JSON structure
    const output = {
      messages: messages.map((msg) => {
        const clean = {
          role: msg.role,
          content: msg.content || "",
          timestamp: msg.timestamp || null
        };

        // Include tools array for assistant messages
        if (msg.tools && msg.tools.length > 0) {
          clean.tools = msg.tools.map((t) => {
            const tool = { name: t.name };
            if (t.input) tool.input = t.input;
            if (t.id) tool.id = t.id;
            return tool;
          });
        }

        return clean;
      }),
      title: title || "Untitled Conversation",
      model: model || "unknown",
      platform: platform || "unknown"
    };

    // Add Context Bridge metadata
    output.exportedBy = "Context Bridge v4";
    output.repo = "https://github.com/ved079/context-bridge";
    output.exportTimestamp = new Date().toISOString();

    return JSON.stringify(output, null, 2);
  }

  /* ═══════════════════════════════════════════════════════════════
     HELPERS
     ═══════════════════════════════════════════════════════════════ */

  function formatRole(role) {
    switch (role) {
      case "user": return "\u{1F464} User";
      case "assistant": return "\u{1F916} Assistant";
      default: return "\u{1F4AC} Message";
    }
  }

  function formatPlatform(model, platform) {
    if (platform === "zai") return "Z.ai (Zhipu AI)";
    if (model && model.toLowerCase().includes("claude")) return "Claude (Anthropic)";
    if (model && (model.toLowerCase().includes("gpt") || model.toLowerCase().includes("o1") || model.toLowerCase().includes("o3"))) return "ChatGPT (OpenAI)";
    if (platform === "claude") return "Claude (Anthropic)";
    if (platform === "chatgpt") return "ChatGPT (OpenAI)";
    if (model && model.toLowerCase().includes("glm")) return "Z.ai (Zhipu AI)";
    return model || "Unknown";
  }

  function formatDate(isoStr) {
    try { return new Date(isoStr).toLocaleString(); } catch { return isoStr || ""; }
  }

  function formatTime(isoStr) {
    try { return new Date(isoStr).toLocaleTimeString(); } catch { return ""; }
  }

  /**
   * Format a tool call as readable markdown.
   * Handles Claude Code tools (create_file, bash_tool, view, etc.)
   */
  function detectLang(path) {
    const ext = (path || "").split(".").pop().toLowerCase();
    const map = {
      py:"python",js:"javascript",ts:"typescript",tsx:"tsx",jsx:"jsx",
      rb:"ruby",go:"go",rs:"rust",java:"java",cpp:"cpp",c:"c",
      cs:"csharp",php:"php",html:"html",css:"css",sql:"sql",
      sh:"bash",bash:"bash",yml:"yaml",yaml:"yaml",json:"json",
      md:"markdown",swift:"swift",kt:"kotlin",dart:"dart",
      lua:"lua",scala:"scala",toml:"toml",xml:"xml"
    };
    return map[ext] || "";
  }

  function formatToolCall(tool) {
    const name = tool.name || "unknown";
    const input = tool.input || {};

    switch (name) {
      case "create_file":
      case "write_file":
      case "CreateFile":
      case "WriteFile":
        const filePath = input.path || input.file_path || "unknown";
        const lang = detectLang(filePath);
        return [
          `**${name}**: \`${filePath}\``,
          "```" + (lang || ""),
          input.file_text || input.content || input.new_string || "(empty file)",
          "```"
        ].join("\n");

      case "edit_file":
      case "EditFile":
        return [
          `**${name}**: \`${input.file_path || "unknown"}\``,
          input.old_string ? `Old:\n\`\`\`\n${input.old_string}\n\`\`\`` : "",
          input.new_string ? `New:\n\`\`\`\n${input.new_string}\n\`\`\`` : "",
          input.content ? `Content:\n\`\`\`\n${input.content}\n\`\`\`` : ""
        ].filter(Boolean).join("\n");

      case "bash_tool":
      case "TerminalCommand":
      case "Bash":
        const cmd = input.command || input.command_string || "";
        return `**bash**: \`${cmd}\``;

      case "view":
      case "ReadFile":
        return `**view**: \`${input.path || input.file_path || "unknown"}\``;

      case "present_files":
      case "PresentFiles":
        const paths = input.filepaths || input.paths || [];
        return `**present_files**: ${paths.map(p => `\`${p}\``).join(", ")}`;

      default:
        const inputPreview = Object.keys(input).length > 0
          ? "\n```json\n" + JSON.stringify(input, null, 2).slice(0, 1000) + "\n```"
          : "";
        return `**${name}**: ${inputPreview}`;
    }
  }

  /* ── Footer constants ─────────────────────────────────────── */

  const FOOTER = `---

<br/>

<p align="center">
  <strong>Built with</strong> <a href="https://github.com/ved079/context-bridge">Context Bridge</a> &mdash; clean conversation exports, zero noise.<br/>
  <em>Capture your AI conversations. Switch agents. Never lose context.</em>
</p>

<p align="center">
  <a href="https://github.com/ved079/context-bridge"><img src="https://img.shields.io/badge/GitHub-ved079%2Fcontext%20bridge-181717?logo=github&logoColor=white" alt="GitHub"/></a>
  <a href="https://github.com/ved079/context-bridge/stargazers"><img src="https://img.shields.io/github/stars/ved079/context-bridge?style=social" alt="Stars"/></a>
</p>

*Exported by Context Bridge v4 (Claude, ChatGPT & Z.ai)*`;

  const FOOTER_COMPACT = `---
*Captured with [Context Bridge](https://github.com/ved079/context-bridge) — give it a star on GitHub!*`;

  /* ── Public API ───────────────────────────────────────────── */

  return {
    generate,
    generateCompact,
    generateJSON
  };
})();
