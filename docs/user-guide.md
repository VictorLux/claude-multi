# User Guide

## Getting Started

### 1. Install dependencies

```bash
# macOS
brew install tmux python@3.11

# Ubuntu/Debian
sudo apt install tmux python3.11

# Verify
tmux -V        # needs 2.3+
python3 --version  # needs 3.11+
claude --version   # Claude Code must be installed
```

### 2. Install claude-multi

```bash
git clone https://github.com/VictorLux/claude-multi.git
cd claude-multi
cp claude-multi ~/.local/bin/claude-multi
chmod +x ~/.local/bin/claude-multi
```

### 3. First launch

```bash
# Simple: pass project directories
claude-multi ~/project-a ~/project-b

# Or set up config first (see Configuration below)
claude-multi
```

## Configuration

Edit `~/.config/claude-multi/config.toml` (auto-created on first run):

### Basic setup — two projects

```toml
layout = "grid"

[[projects]]
path = "~/frontend"
color = "green"

[[projects]]
path = "~/backend"
color = "cyan"
```

### With skills and models

```toml
layout = "grid"

[[projects]]
path = "~/my-app"
skill = "architect"
model = "opus"
effort = "high"
color = "green"

[[projects]]
path = "~/my-app"
skill = "frontend"
model = "sonnet"
effort = "medium"
color = "yellow"

[[projects]]
path = "~/my-app"
skill = "test-auto"
model = "sonnet"
effort = "medium"
color = "red"

[[projects]]
path = "~/my-app"
skill = "security"
model = "haiku"
effort = "low"
color = "magenta"
```

### Custom system prompts

```toml
[[projects]]
path = "~/my-app"
system_prompt = "You are an expert in Solana blockchain development using the Anchor framework"
label = "solana"
model = "opus"
effort = "high"
color = "green"
```

## Daily Usage

### Starting your session

```bash
# From config
claude-multi

# Or specify projects
claude-multi ~/project-a ~/project-b ~/project-c
```

### Navigating between panes

| Method | How |
|---|---|
| Arrow keys | `Ctrl+B` then `arrow` |
| Mouse | Click on a pane |
| Pane numbers | `Ctrl+B` then `q`, then press number |

### Zooming a pane

Press `Ctrl+B` then `z` to fullscreen the active pane.
Press again to return to the grid.

### Restarting Claude

| Action | Keybinding |
|---|---|
| Restart current pane | `Ctrl+B` then `r` |
| Restart all panes | `Ctrl+B` then `R` |

Restart uses `claude --continue` so your conversation is preserved.

### Upgrading Claude Code

Press `Ctrl+B` then `U`. A confirmation prompt appears:

```
=== Claude Code Upgrade ===

This will run: npm update -g @anthropic-ai/claude-code
This affects Claude Code globally on this system.

Proceed? [y/N]
```

After upgrade, all panes restart with the new version.

### Detaching and re-attaching

```bash
# Detach (session keeps running in background)
# Press Ctrl+B then d

# Re-attach later
claude-multi              # auto-detects existing session
tmux attach -t claude-multi   # or directly
```

### Closing panes and sessions

| Action | How |
|---|---|
| Close one pane | `Ctrl+B` then `x` (confirms) |
| Kill entire session | `tmux kill-session -t claude-multi` |
| Exit Claude in a pane | Type `exit` in Claude, then `Ctrl+C` |

### Multiple instances

```bash
claude-multi --session work ~/work-project-a ~/work-project-b
claude-multi --session personal ~/side-project
tmux ls   # lists both sessions
```

## Tips

- **Opus for thinking, Sonnet for doing**: Use opus with high effort for architecture and complex reasoning. Use sonnet with medium effort for implementation and fast iteration.
- **Haiku for reviews**: Code reviews and documentation don't need deep reasoning — haiku with low effort is fast and cheap.
- **Same project, different experts**: Having a security expert and a test expert looking at the same codebase catches issues neither would find alone.
- **Zoom when focused**: Press `Ctrl+B z` when you need to focus on one pane, press again to return.
- **Detach overnight**: If you're running long tasks, detach with `Ctrl+B d` and come back later.

## Troubleshooting

### "ERROR: tmux is not installed"

Install tmux: `brew install tmux` (macOS) or `sudo apt install tmux` (Ubuntu)

### Pane headers not showing

Make sure you have tmux 2.3+. Run `tmux -V` to check.

### Mouse clicks not working

If you attached to the session before the config was sourced, re-source it:
```bash
tmux source-file ~/.config/claude-multi/tmux.conf
```

### Session already exists

`claude-multi` auto-attaches to existing sessions. To start fresh:
```bash
tmux kill-session -t claude-multi
claude-multi
```
