/**
 * Context Bridge — Markdown Generator (v5)
 * Converts API-fetched conversation data into clean, readable exports.
 *
 * Supports: Claude, ChatGPT, Z.ai
 *
 * Key principle: TEXT content and TOOL calls are SEPARATED.
 * - `content` = only what the AI said to the user (text blocks)
 * - `tools`   = tool calls (file ops, bash, etc.) — shown separately
 * - No DOM noise, no leaked UI elements, no truncated streaming artifacts.
 *
 * Three export formats:
 *  1. Full Markdown — structured header, numbered messages, tools in collapsible sections
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

    // ── Title ────────────────────────────────────────────────
    lines.push(`# ${title || "Conversation Export"}`);
    lines.push("");

    // ── Metadata header (blockquote table) ──────────────────
    // Clean two-column layout that renders well on GitHub, VS Code, etc.
    const source = formatPlatform(model, platform);
    const totalTools = messages.reduce((n, m) => n + (m.tools ? m.tools.length : 0), 0);
    const userCount = messages.filter(m => m.role === "user").length;
    const asstCount = messages.filter(m => m.role === "assistant").length;

    lines.push(`> **Source** · ${source}`);
    if (model) lines.push(`> **Model** · ${model}`);
    lines.push(`> **Messages** · ${messages.length} (${userCount} user · ${asstCount} assistant)`);

    if (messages.length > 0) {
      const firstTs = messages[0].timestamp;
      const lastTs = messages[messages.length - 1].timestamp;
      if (firstTs && lastTs) {
        lines.push(`> **Duration** · ${formatDateShort(firstTs)} → ${formatDateShort(lastTs)}`);
      } else if (firstTs) {
        lines.push(`> **Started** · ${formatDateShort(firstTs)}`);
      }
    }

    if (totalTools > 0) {
      lines.push(`> **Tool Calls** · ${totalTools}`);
    }

    lines.push(`> **Exported** · ${formatDateShort(new Date().toISOString())}`);
    lines.push("");
    lines.push("---");
    lines.push("");

    // ── Messages ─────────────────────────────────────────────
    if (messages.length === 0) {
      lines.push("*No messages captured.*");
      lines.push("");
    }

    messages.forEach((msg, i) => {
      const label = formatRole(msg.role);
      const time = msg.timestamp ? ` · ${formatTime(msg.timestamp)}` : "";
      const num = i + 1;

      // Message header — bold inline, not H2 (less visual noise)
      lines.push(`**[${num}] ${label}**${time}`);
      lines.push("");

      // Text content — auto-collapse if very large (>100 lines)
      if (msg.content) {
        lines.push(formatContent(msg.content));
        lines.push("");
      } else if (msg.role === "assistant") {
        lines.push("*[No text response — only tool calls]*");
        lines.push("");
      }

      // Tool calls (collapsible details)
      if (msg.tools && msg.tools.length > 0) {
        const toolNames = msg.tools.map(t => t.name || "unknown");
        // Unique tool names with counts
        const toolSummary = summarizeToolList(toolNames);
        lines.push(`<details>`);
        lines.push(`<summary>${toolSummary}</summary>`);
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
    const { messages = [], title, model, platform } = data;
    const lines = [];
    const source = formatPlatformShort(platform);

    // Brief context header
    lines.push(`## ${title || "Untitled"}`);
    lines.push(`*${source}${model ? " · " + model : ""} · ${messages.length} messages*`);
    lines.push("");
    lines.push("---");
    lines.push("");

    // Messages — minimal formatting, maximum context
    messages.forEach((msg) => {
      const label = msg.role === "user" ? "**User**" : "**Assistant**";
      lines.push(`${label}:`);
      lines.push("");

      if (msg.content) {
        lines.push(msg.content);
      }

      // Include tool call info briefly
      if (msg.tools && msg.tools.length > 0) {
        const toolNames = msg.tools.map(t => t.name || "unknown");
        const toolSummary = summarizeToolList(toolNames);
        lines.push("");
        lines.push(`*${toolSummary}*`);
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

    const output = {
      title: title || "Untitled Conversation",
      model: model || "unknown",
      platform: platform || "unknown",
      messages: messages.map((msg) => {
        const clean = {
          role: msg.role,
          content: msg.content || "",
          timestamp: msg.timestamp || null
        };

        if (msg.tools && msg.tools.length > 0) {
          clean.tools = msg.tools.map((t) => {
            const tool = { name: t.name };
            if (t.input) tool.input = t.input;
            if (t.id) tool.id = t.id;
            return tool;
          });
        }

        if (msg.toolResults && msg.toolResults.length > 0) {
          clean.toolResults = msg.toolResults.map((r) => ({
            toolUseId: r.toolUseId || null,
            isError: r.isError || false,
            content: r.content || null
          }));
        }

        return clean;
      }),
      metadata: {
        messageCount: messages.length,
        userMessages: messages.filter(m => m.role === "user").length,
        assistantMessages: messages.filter(m => m.role === "assistant").length,
        toolCalls: messages.reduce((n, m) => n + (m.tools ? m.tools.length : 0), 0),
        wordCount: messages.reduce((n, m) => n + (m.content || "").split(/\s+/).filter(Boolean).length, 0)
      }
    };

    output.exportedBy = "Context Bridge v5";
    output.repo = "https://github.com/ved079/context-bridge";
    output.exportTimestamp = new Date().toISOString();

    return JSON.stringify(output, null, 2);
  }

  /* ═══════════════════════════════════════════════════════════════
     HELPERS
     ═══════════════════════════════════════════════════════════════ */

  function formatRole(role) {
    switch (role) {
      case "user":      return "User";
      case "assistant": return "Assistant";
      default:          return role || "Message";
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

  function formatPlatformShort(platform) {
    switch (platform) {
      case "claude":  return "Claude";
      case "chatgpt": return "ChatGPT";
      case "zai":     return "Z.ai";
      default:        return "Unknown";
    }
  }

  function formatDateShort(isoStr) {
    try {
      const d = new Date(isoStr);
      const opts = { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", hour12: true };
      return d.toLocaleString("en-US", opts);
    } catch {
      return isoStr || "";
    }
  }

  function formatDate(isoStr) {
    try { return new Date(isoStr).toLocaleString(); } catch { return isoStr || ""; }
  }

  function formatTime(isoStr) {
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
    } catch {
      return "";
    }
  }

  /**
   * Build a concise summary for the <details> tag.
   * e.g. "🔧 5 tool calls (create_file ×2, bash ×2, view)"
   */
  function summarizeToolList(names) {
    if (!names || names.length === 0) return "🔧 0 tool calls";

    const counts = {};
    for (const n of names) {
      const key = n || "unknown";
      counts[key] = (counts[key] || 0) + 1;
    }

    const parts = Object.entries(counts).map(([name, count]) => {
      return count > 1 ? `${name} x${count}` : name;
    });

    const total = names.length;
    const suffix = total > 1 ? ` (${parts.join(", ")})` : ` — ${parts[0]}`;
    return `🔧 ${total} tool call${total > 1 ? "s" : ""}${suffix}`;
  }

  /**
   * Format message content — returns it as-is unless it's extremely long,
   * in which case we wrap it in a collapsible <details> block.
   * This catches any large content that the scraper didn't already collapse
   * (e.g. massive log dumps, raw pasted text, DOM-scraped walls).
   * Threshold: 100 lines.
   */
  function formatContent(content) {
    const lines = content.split("\n");
    if (lines.length <= 100) return content;

    return [
      `<details>`,
      `<summary>Expand to view (${lines.length} lines)</summary>`,
      "",
      content,
      "",
      `</details>`
    ].join("\n");
  }

  /**
   * Detect language from file path extension.
   */
  function detectLang(path) {
    const ext = (path || "").split(".").pop().toLowerCase();
    const map = {
      py:"python",js:"javascript",ts:"typescript",tsx:"tsx",jsx:"jsx",
      rb:"ruby",go:"go",rs:"rust",java:"java",cpp:"cpp",c:"c",
      cs:"csharp",php:"php",html:"html",css:"css",sql:"sql",
      sh:"bash",bash:"bash",yml:"yaml",yaml:"yaml",json:"json",
      md:"markdown",swift:"swift",kt:"kotlin",dart:"dart",
      lua:"lua",scala:"scala",toml:"toml",xml:"xml",
      vue:"vue",svelte:"svelte",dockerfile:"dockerfile",makefile:"makefile"
    };
    return map[ext] || "";
  }

  /**
   * Format a tool call as readable markdown.
   * Handles Claude Code tools (create_file, bash_tool, view, etc.)
   */
  function formatToolCall(tool) {
    const name = tool.name || "unknown";
    const input = tool.input || {};

    switch (name) {
      case "create_file":
      case "write_file":
      case "CreateFile":
      case "WriteFile":
        {
          const filePath = input.path || input.file_path || "unknown";
          const lang = detectLang(filePath);
          const content = input.file_text || input.content || input.new_string || "(empty file)";
          return [
            `**create_file** — \`${filePath}\``,
            "```" + (lang || ""),
            content,
            "```"
          ].join("\n");
        }

      case "edit_file":
      case "EditFile":
        {
          const parts = [`**edit_file** — \`${input.file_path || "unknown"}\``];
          if (input.old_string) {
            parts.push("");
            parts.push("*Old:*");
            parts.push("```diff");
            parts.push(input.old_string);
            parts.push("```");
          }
          if (input.new_string) {
            parts.push("");
            parts.push("*New:*");
            parts.push("```diff");
            parts.push(input.new_string);
            parts.push("```");
          }
          if (input.content) {
            parts.push("");
            parts.push("*Content:*");
            parts.push("```diff");
            parts.push(input.content);
            parts.push("```");
          }
          return parts.join("\n");
        }

      case "bash_tool":
      case "TerminalCommand":
      case "Bash":
        {
          const cmd = input.command || input.command_string || "";
          return [
            "**bash**",
            "```bash",
            cmd,
            "```"
          ].join("\n");
        }

      case "view":
      case "ReadFile":
        return `**view** — \`${input.path || input.file_path || "unknown"}\``;

      case "present_files":
      case "PresentFiles":
        {
          const paths = input.filepaths || input.paths || [];
          return `**present_files** — ${paths.map(p => `\`${p}\``).join(", ")}`;
        }

      default:
        {
          const inputPreview = Object.keys(input).length > 0
            ? "\n```json\n" + JSON.stringify(input, null, 2).slice(0, 1000) + "\n```"
            : "";
          return `**${name}**${inputPreview}`;
        }
    }
  }

  /* ── Footer constants ─────────────────────────────────────── */

  const FOOTER = `---

*Exported by [Context Bridge](https://github.com/ved079/context-bridge) — clean conversation exports, zero noise.*`;

  const FOOTER_COMPACT = `---
*Captured with [Context Bridge](https://github.com/ved079/context-bridge)*`;

  /* ── Public API ───────────────────────────────────────────── */

  return {
    generate,
    generateCompact,
    generateJSON
  };
})();
