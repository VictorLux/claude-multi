# claude-multi

Run up to 6 [Claude Code](https://claude.ai/claude-code) sessions side-by-side in a single terminal using tmux.

Each pane gets a persistent header showing project name, Claude version, model, effort level, and session status. Assign different **skill presets** (quant, security, devops, etc.) and **model/effort combos** per pane.

![Grid layout with 6 panes](docs/images/grid-layout-placeholder.png)

> **DISCLAIMER:** This is an independent, community-built tool. It is **not** an official Anthropic product. It is not affiliated with, endorsed by, or supported by Anthropic. Claude Code is a trademark of Anthropic. Use at your own risk. This tool launches Claude Code sessions on your behalf and may incur API usage costs depending on your plan. The authors are not responsible for any costs, damages, or issues arising from use of this tool.

## Features

- **Multi-session**: Up to 6 Claude Code sessions in one terminal
- **Skill presets**: 26 built-in expert personas (quant, security, devops, architect, etc.)
- **Per-pane model**: Assign different Claude models (opus, sonnet, haiku) per pane
- **Per-pane effort**: Set effort level (low, medium, high, max) per pane
- **Smart restart**: Restart panes with `claude --continue` to preserve conversation
- **Upgrade detection**: Notifies when a new Claude Code version is available
- **Colored headers**: Active pane highlighted with green border and arrow
- **Help bar**: Keybindings displayed at the bottom of the screen
- **Zero dependencies**: Python 3.11+ stdlib only (uses `tomllib`)

## Requirements

- **Python 3.11+**
- **tmux 2.3+** (3.0+ recommended for full feature support)
- **Claude Code CLI** (`claude` command available in PATH)

## Installation

```bash
# Clone the repo
git clone https://github.com/VictorLux/claude-multi.git
cd claude-multi

# Copy the script to your PATH
cp claude-multi ~/.local/bin/claude-multi
chmod +x ~/.local/bin/claude-multi

# Verify installation
claude-multi --version
```

Make sure `~/.local/bin` is in your `PATH`. Add to your shell profile if needed:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Quick Start

```bash
# Launch with project paths
claude-multi ~/project-a ~/project-b

# Launch with a specific layout
claude-multi --layout grid ~/project-a ~/project-b ~/project-c ~/project-d

# Launch in background (detached)
claude-multi --detach ~/project-a ~/project-b

# Use config file (no args needed)
claude-multi
```

## Configuration

On first run, a config file is created at `~/.config/claude-multi/config.toml`:

```toml
layout = "grid"
palette = ["green", "cyan", "yellow", "magenta", "blue", "red"]
upgrade_check_interval = 30

# Example: same project with different expert roles
[[projects]]
path = "~/my-app"
skill = "architect"
model = "opus"
effort = "high"
color = "green"

[[projects]]
path = "~/my-app"
skill = "test-auto"
model = "sonnet"
effort = "medium"
color = "yellow"

[[projects]]
path = "~/my-app"
skill = "security"
model = "sonnet"
effort = "medium"
color = "red"

[[projects]]
path = "~/other-project"
skill = "fullstack"
model = "opus"
effort = "high"
color = "cyan"
```

### Project options

| Option | Description | Example |
|---|---|---|
| `path` | Project directory (required) | `"~/my-project"` |
| `color` | Pane color | `"green"` |
| `skill` | Skill preset name | `"quant"` |
| `model` | Claude model | `"opus"`, `"sonnet"`, `"haiku"` |
| `effort` | Effort level | `"low"`, `"medium"`, `"high"`, `"max"` |
| `system_prompt` | Custom system prompt (overrides skill) | `"You are a..."` |
| `label` | Custom header label (overrides skill label) | `"my-role"` |

## Layouts

```
Grid (default)              Horizontal                Vertical
┌────────┬────────┐    ┌────┬────┬────┐    ┌──────────────────┐
│ pane 1 │ pane 2 │    │  1 │  2 │  3 │    │      pane 1      │
├────────┼────────┤    └────┴────┴────┘    ├──────────────────┤
│ pane 3 │ pane 4 │                        │      pane 2      │
├────────┼────────┤                        ├──────────────────┤
│ pane 5 │ pane 6 │                        │      pane 3      │
└────────┴────────┘                        └──────────────────┘
```

```bash
claude-multi --layout grid ~/a ~/b ~/c ~/d
claude-multi --layout horizontal ~/a ~/b ~/c
claude-multi --layout vertical ~/a ~/b
```

## Keybindings

All keybindings use the tmux prefix (default: `Ctrl+B`):

| Keybinding | Action |
|---|---|
| `Ctrl+B` + `arrows` | Navigate between panes |
| `Ctrl+B` + `z` | Zoom (fullscreen) current pane |
| `Ctrl+B` + `r` | Restart current pane (`claude --continue`) |
| `Ctrl+B` + `R` | Restart ALL panes |
| `Ctrl+B` + `U` | Upgrade Claude Code (with confirmation) |
| `Ctrl+B` + `x` | Close current pane |
| `Ctrl+B` + `d` | Detach (session keeps running) |
| Mouse click | Switch to clicked pane |

```bash
# Show keybinding reference anytime
claude-multi --keys
```

## Skill Presets

26 built-in expert personas covering the full IT project lifecycle:

```bash
# List all available skills
claude-multi --skills
```

| Category | Skills |
|---|---|
| **Project & Analysis** | `pm`, `ba`, `functional`, `technical` |
| **Architecture** | `architect`, `db` |
| **Development** | `backend`, `frontend`, `fullstack`, `rust`, `python`, `mobile` |
| **Domain** | `quant`, `crypto`, `data`, `ai` |
| **Testing & QA** | `qa`, `test-auto`, `perf` |
| **Security** | `security` |
| **Infrastructure** | `devops`, `cloud`, `prod-support` |
| **Maintenance** | `maintenance`, `reviewer`, `docs` |

You can also create fully custom roles:

```toml
[[projects]]
path = "~/my-project"
system_prompt = "You are a Solana blockchain expert specializing in program development with Anchor framework"
label = "solana"
model = "opus"
```

## CLI Reference

```
claude-multi [OPTIONS] [PROJECT_PATHS...]

Arguments:
  PROJECT_PATHS           Project directories (overrides config)

Options:
  --layout {grid,h,v}    Pane layout (default: from config)
  --session NAME          Tmux session name (default: claude-multi)
  --detach                Create in background
  --config PATH           Config file path
  --keys                  Show keybinding reference
  --skills                Show available skill presets
  --version               Show version
  --help                  Show help
```

### Multiple instances

```bash
claude-multi --session work ~/project-a ~/project-b
claude-multi --session personal ~/side-project
```

### Re-attach after detach

```bash
claude-multi                    # auto-attaches if session exists
tmux attach -t claude-multi     # or directly
```

### Kill a session

```bash
tmux kill-session -t claude-multi
```

## How It Works

See [docs/architecture.md](docs/architecture.md) for the full technical architecture.

**Overview:** `claude-multi` is a Python script that orchestrates tmux. It creates a tmux session, splits it into panes, generates helper shell scripts for restart/upgrade functionality, and launches Claude Code in each pane with the configured model, effort, and system prompt.

## Security

- **No shell injection**: All subprocess calls use argument lists, never `shell=True`
- **Path validation**: Paths validated and sanitized before use in shell contexts
- **Config permissions**: Created with `0o600`, warns if too permissive
- **No secrets in config**: Only paths, colors, layout preferences
- **SIGTERM graceful shutdown**: Panes restart cleanly preserving conversation state
- **Input sanitization**: Tmux names stripped to `[a-zA-Z0-9_-]`

## Contributing

Contributions welcome! Please open an issue first to discuss what you'd like to change.

## License

[MIT](LICENSE)

---

**This project is not affiliated with or endorsed by Anthropic.** Claude Code is a product of Anthropic. This is a community tool that wraps the Claude Code CLI.
