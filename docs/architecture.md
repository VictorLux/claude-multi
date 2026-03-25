# Architecture

## Overview

`claude-multi` is a single Python script (~1000 lines) with zero external dependencies that orchestrates tmux to run multiple Claude Code sessions side by side.

```
┌─────────────────────────────────────────────────┐
│                  claude-multi                    │
│              (Python orchestrator)               │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  Config   │  │   CLI    │  │  Dependency   │  │
│  │  Loader   │  │  Parser  │  │   Checker     │  │
│  └────┬─────┘  └────┬─────┘  └──────┬────────┘  │
│       └──────────────┴───────────────┘           │
│                      │                           │
│              ┌───────▼───────┐                   │
│              │  Orchestrator │                   │
│              │   (main)      │                   │
│              └───────┬───────┘                   │
│                      │                           │
│       ┌──────────────┼──────────────┐            │
│       ▼              ▼              ▼            │
│  ┌─────────┐  ┌───────────┐  ┌───────────┐      │
│  │  Tmux   │  │  Layout   │  │  Script   │      │
│  │  Config │  │  Builder  │  │ Generator │      │
│  │  Gen    │  │           │  │           │      │
│  └─────────┘  └───────────┘  └───────────┘      │
└─────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│                   tmux session                   │
│                                                  │
│  ┌──────────────────┬──────────────────┐         │
│  │ pane-wrapper.sh  │ pane-wrapper.sh  │         │
│  │  → claude --name │  → claude --name │         │
│  │  --model opus    │  --model sonnet  │         │
│  │  --effort high   │  --effort medium │         │
│  │  --system-prompt │  --system-prompt │         │
│  └──────────────────┴──────────────────┘         │
│                                                  │
│  Status bar: keybinding help                     │
└─────────────────────────────────────────────────┘
```

## Components

### 1. CLI Entry Point (`parse_args`, `main`)

Parses command-line arguments and orchestrates the startup sequence:
1. Parse args
2. Load config (TOML)
3. Check dependencies (tmux, claude)
4. Validate project paths
5. Create tmux session with panes

### 2. Config Loader (`load_config`)

- Reads `~/.config/claude-multi/config.toml`
- Creates default config on first run with `0o600` permissions
- Warns if existing config has overly permissive permissions
- Validates layout value

### 3. Skill Resolver (`resolve_skill`)

Maps skill presets to system prompts:
- 26 built-in presets covering full IT lifecycle
- Custom `system_prompt` overrides skill preset
- Custom `label` overrides skill label
- Per-pane `model` and `effort` configuration

### 4. Project Validator (`validate_projects`)

- Resolves and validates paths (`Path.expanduser().resolve()`)
- Deduplicates by path+skill+model combo (same path with different skills is allowed)
- Assigns colors from palette or config
- Enforces max 6 sessions
- Sanitizes names for tmux compatibility

### 5. Dependency Checker (`check_dependencies`)

- Verifies tmux is installed (>= 2.3)
- Verifies Claude Code CLI is installed
- Extracts version numbers for display

### 6. Tmux Config Generator (`generate_tmux_conf`)

Generates `~/.config/claude-multi/tmux.conf` on each launch:
- Pane border format with `@cm_info` user option (not `pane_title`, which Claude overwrites)
- Active/inactive pane styling (green vs grey)
- Mouse support
- Keybindings for restart (`r`/`R`), upgrade (`U`)
- Self-rescheduling upgrade check timer
- Status bar with help shortcuts

### 7. Layout Builder (`build_layout_commands`)

Builds tmux split-window + select-layout commands:
- **Grid**: Uses tmux `tiled` layout
- **Horizontal**: Uses `even-horizontal`
- **Vertical**: Uses `even-vertical`
- Applies layout after each split to handle any pane count

### 8. Script Generator (`generate_scripts`)

Generates helper shell scripts in `~/.config/claude-multi/scripts/`:

| Script | Purpose |
|---|---|
| `pane-wrapper.sh` | Per-pane loop: launches Claude, handles restart, updates header |
| `restart.sh` | SIGTERM to Claude process, SIGKILL after 5s, triggers wrapper restart |
| `restart-all.sh` | Restarts all panes in parallel |
| `upgrade.sh` | Confirmation prompt, npm upgrade, restart all |
| `check-upgrade.sh` | Silent version check, self-rescheduling via tmux `run-shell` |

### 9. Session Creator (`create_session`)

1. Generates tmux.conf and helper scripts
2. Creates tmux session with `new-session`
3. Sources config explicitly (`source-file`)
4. Creates additional panes via layout builder
5. For each pane: sets `@cm_info`, sets border color, launches wrapper via `send-keys`
6. Passes `CM_MODEL`, `CM_EFFORT`, `CM_SYSTEM_PROMPT` as environment variables
7. Attaches or stays detached

## File Layout

```
~/.local/bin/claude-multi                       # Main executable
~/.config/claude-multi/
  config.toml                                   # User configuration
  tmux.conf                                     # Generated tmux config (regenerated each launch)
  scripts/
    pane-wrapper.sh                             # Per-pane Claude launcher
    restart.sh                                  # Single pane restart (SIGTERM)
    restart-all.sh                              # All panes restart
    upgrade.sh                                  # Upgrade with confirmation
    check-upgrade.sh                            # Background upgrade checker
```

## Security Model

### Shell Injection Prevention
- All `subprocess.run()` calls use argument lists (never `shell=True` with interpolation)
- Paths validated against `SAFE_PATH_RE` before interpolation into tmux config
- Session/pane names sanitized to `[a-zA-Z0-9_-]`

### Process Management
- `restart.sh` uses SIGTERM with 5-second grace period, then SIGKILL
- Claude Code saves conversation state on SIGTERM, enabling `--continue` on restart
- Clean shutdown via `tmux kill-session`

### Config Security
- Created with `0o600` (owner read/write only)
- Warns on overly permissive existing config
- TOML parsed with `tomllib` (read-only, no code execution)

## Design Decisions

1. **`@cm_info` over `pane_title`**: Claude Code continuously updates the terminal title with its own status. Using tmux per-pane user options (`@cm_info`) prevents Claude from overwriting our header.

2. **`send-keys` for all panes**: All panes launched consistently via `send-keys` rather than having the first pane use `new-session`'s shell command. This ensures consistent behavior across panes.

3. **Tmux `tiled` layout for grid**: Instead of manually tracking pane indices (which break when tmux renumbers after splits), we use tmux's built-in `tiled` layout and let it handle pane arrangement.

4. **Self-rescheduling timer**: The upgrade checker uses `tmux run-shell -b "sleep N && bash self"` instead of a Python background thread, because the Python process is replaced by `tmux attach` via `os.execvp`.

5. **Environment variables for skill config**: `CM_MODEL`, `CM_EFFORT`, and `CM_SYSTEM_PROMPT` are passed as env vars to the pane wrapper, avoiding complex argument quoting in `send-keys`.

6. **Version detection on restart**: The pane wrapper runs `claude --version` on each restart cycle, so upgrading Claude and pressing `Ctrl+B r` shows the new version immediately.
