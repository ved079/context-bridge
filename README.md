<br/>
<p align="center">
  <img src="https://img.shields.io/badge/Chrome_Extension-Manifest_V3-4285f4?logo=googlechrome&logoColor=white" alt="Manifest V3"/>
  <img src="https://img.shields.io/badge/Platforms-Claude%20%7C%20ChatGPT%20%7C%20Z.ai-181717?style=flat" alt="Platforms"/>
  <img src="https://img.shields.io/badge/Exports-Markdown%20%7C%20JSON-181717?style=flat" alt="Exports"/>
  <a href="https://github.com/ved079/context-bridge/stargazers"><img src="https://img.shields.io/github/stars/ved079/context-bridge?style=social" alt="Stars"/></a>
</p>

<h1 align="center">Context Bridge</h1>

<p align="center">
  <strong>Capture your AI conversations. Switch agents. Never lose context.</strong><br/>
  <br/>
  One-click export of full Claude, ChatGPT, and Z.ai conversations<br/>
  as clean Markdown or JSON. No accounts, no servers, no bullshit.
</p>

<br/>

<p align="center">
  <a href="#-installation"><strong>Install</strong></a> &nbsp;·&nbsp;
  <a href="#-how-to-use"><strong>How to Use</strong></a> &nbsp;·&nbsp;
  <a href="#-supported-platforms"><strong>Platforms</strong></a> &nbsp;·&nbsp;
  <a href="#-export-formats"><strong>Exports</strong></a>
</p>

---

## 📦 Installation

> Takes 30 seconds. No Chrome Web Store needed.

### Step 1 — Download the extension

[Download ZIP](https://github.com/ved079/context-bridge/archive/refs/heads/main.zip) or clone the repo:

```bash
git clone https://github.com/ved079/context-bridge.git
```

### Step 2 — Unzip (if you downloaded the ZIP)

Extract the ZIP file. You'll get a folder called `context-bridge-main`.

Open that folder and go into the **`context-bridge-v4`** subfolder — that's the extension.

```
context-bridge-main/
  └── context-bridge-v4/    ← this is what you load into Chrome
        ├── manifest.json
        ├── background/
        ├── content/
        ├── popup/
        ├── lib/
        └── icons/
```

### Step 3 — Load into Chrome (or Brave, or Edge, or Arc)

1. Open your browser and go to:

   ```
   chrome://extensions
   ```

   > **Brave**: `brave://extensions` · **Edge**: `edge://extensions` · **Arc**: `arc://extensions`

2. **Enable Developer Mode** — toggle the switch in the top-right corner

3. Click **"Load unpacked"** (top-left button)

4. Select the **`context-bridge-v4`** folder

5. Done. You'll see **Context Bridge** in your extensions list. Pin it to your toolbar.

<p align="center">
  <img src="https://img.shields.io/badge/⚠️_Important-use_context_bridge-v4_folder-not_the_root-eab308?style=for-the-badge" alt="Important"/>
</p>

---

## 🚀 How to Use

1. **Open a conversation** on Claude, ChatGPT, or Z.ai
2. **Click the extension icon** in your toolbar
3. **Click "Capture Conversation"**
4. **Export** as Markdown (full or compact) or JSON

That's it. Three buttons. No setup. No configuration.

---

## 🌐 Supported Platforms

| Platform | URL | Method | Status |
|----------|-----|--------|--------|
| **Claude** | claude.ai/chat/`{id}` | Internal API (`/api/organizations/...`) | ✅ Working |
| **ChatGPT** | chatgpt.com/c/`{id}` | DOM extraction (API is dead) | ✅ Working |
| **Z.ai** | chat.z.ai/c/`{id}` | Internal API (`/api/v1/chats/...`) | ✅ Working |

All three platforms require you to be **logged in**. The extension uses your existing session — no extra accounts or API keys needed.

---

## 📄 Export Formats

| Format | Filename Pattern | Best For |
|--------|-----------------|----------|
| **Full Markdown** | `claude-{title}.md` | Archiving, documentation, sharing |
| **Compact Markdown** | `claude-{title}-compact.md` | Pasting into another AI (token-saving) |
| **JSON** | `claude-{title}.json` | Programmatic use, backups, analysis |

### Example output (Full Markdown)

```markdown
# My Claude Conversation

> **Source**: Claude (Anthropic)
> **Messages**: 6
> **Started**: 6/5/2026, 5:20 PM
> **Ended**: 6/5/2026, 5:22 PM

---

## 👤 User — 5:20 PM

How do I center a div in CSS?

---

## 🤖 Assistant — 5:21 PM

The modern approach:

```css
.container {
  display: grid;
  place-items: center;
}
```

---

<br/>
<p align="center">
  <em>Exported by Context Bridge v4 (Claude, ChatGPT & Z.ai)</em>
</p>
```

---

## 🏗 How It Works

```
[claude.ai / chatgpt.com / chat.z.ai]
            │
            ▼
[Content Script] ── reads DOM or calls internal API ──▶ [Raw conversation data]
            │
            ▼
[Popup] ── parse, format, export ──▶ claude-my-title.md / .json
```

- **Claude**: Fetches structured conversation data via Claude's internal REST API. Gets text, tool calls, code — everything.
- **ChatGPT**: ChatGPT locked down their API (returns 404). So we read the DOM directly — message elements, code blocks, tables, lists. Works perfectly.
- **Z.ai**: Fetches via Open WebUI's internal API. All messages extracted and sorted by timestamp.

**No external servers. No API keys. No data leaves your browser.**

---

## 📂 File Structure

```
context-bridge-v4/
├── manifest.json              # MV3 manifest
├── background/
│   └── service-worker.js      # Message routing + cookie access
├── content/
│   ├── common.js              # Platform detection, conversation ID extraction
│   ├── claude-api.js          # Claude API scraper
│   ├── chatgpt-api.js         # ChatGPT DOM extractor
│   └── zai-api.js             # Z.ai API scraper
├── lib/
│   └── markdown-generator.js  # Full / Compact / JSON export formats
├── popup/
│   ├── popup.html              # UI layout
│   ├── popup.css               # Dark theme styling
│   └── popup.js                # Capture logic + download handler
└── icons/
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

---

## 🔒 Privacy

- **Zero data collection** — no analytics, no telemetry, no tracking
- **No external servers** — everything runs locally in your browser
- **No API keys stored** — uses your existing login session cookies
- **Your conversations stay on your machine** — exports are local files only

---

## ⚠️ Notes

- You must be **logged in** to the AI platform you're trying to capture from
- The extension needs to be loaded from the **`context-bridge-v4`** folder specifically (not the repo root)
- Works on **Chrome, Brave, Edge, Arc, and any Chromium-based browser**
- Claude and Z.ai use API scraping (fast, structured). ChatGPT uses DOM reading (also fast, equally accurate)

---

## License

MIT — use it, fork it, break it, fix it.
