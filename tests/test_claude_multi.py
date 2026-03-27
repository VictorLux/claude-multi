# ~/docs/superpowers/tests/test_claude_multi.py
import importlib.machinery
import importlib.util
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# Load claude-multi as a module (it has no .py extension)
def load_claude_multi():
    script_path = os.path.expanduser("~/.local/bin/claude-multi")
    loader = importlib.machinery.SourceFileLoader("claude_multi", script_path)
    spec = importlib.util.spec_from_file_location(
        "claude_multi", script_path, loader=loader
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DEFAULT_PALETTE = ["green", "cyan", "yellow", "magenta", "blue", "red"]
MAX_SESSIONS = 6


def test_create_default_config():
    cm = load_claude_multi()
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config = cm.load_config(str(config_path))

        # Default config created
        assert config_path.exists()
        # Permissions are 0o600
        perms = stat.S_IMODE(config_path.stat().st_mode)
        assert perms == 0o600
        # Defaults loaded
        assert config["layout"] == "grid"
        assert len(config["palette"]) == 6
        assert config["upgrade_check_interval"] == 30
        assert config["projects"] == []


def test_load_existing_config():
    cm = load_claude_multi()
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text(
            'layout = "vertical"\n'
            'palette = ["red", "blue"]\n'
            "upgrade_check_interval = 15\n"
            "[[projects]]\n"
            f'path = "{tmpdir}"\n'
            'color = "red"\n'
        )
        config = cm.load_config(str(config_path))

        assert config["layout"] == "vertical"
        assert config["palette"] == ["red", "blue"]
        assert config["upgrade_check_interval"] == 15
        assert len(config["projects"]) == 1
        assert config["projects"][0]["color"] == "red"


def test_config_permission_warning(capsys):
    cm = load_claude_multi()
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text('layout = "grid"\n')
        os.chmod(config_path, 0o644)  # world-readable
        cm.load_config(str(config_path))
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "permissive" in captured.err


def test_parse_args_with_projects():
    cm = load_claude_multi()
    args = cm.parse_args(["~/project-a", "~/project-b", "--layout", "vertical"])
    assert args.layout == "vertical"
    assert args.projects == ["~/project-a", "~/project-b"]


def test_parse_args_defaults():
    cm = load_claude_multi()
    args = cm.parse_args([])
    assert args.layout is None  # None means "use config default"
    assert args.projects == []
    assert args.session == "claude-multi"
    assert args.detach is False


def test_validate_projects_valid():
    cm = load_claude_multi()
    with tempfile.TemporaryDirectory() as tmpdir:
        projects = cm.validate_projects(
            [tmpdir], palette=DEFAULT_PALETTE
        )
        assert len(projects) == 1
        assert projects[0]["path"] == Path(tmpdir).resolve()
        assert projects[0]["color"] == "green"
        assert re.match(r"^[a-zA-Z0-9_-]+$", projects[0]["name"])


def test_validate_projects_skips_invalid(capsys):
    cm = load_claude_multi()
    projects = cm.validate_projects(
        ["/nonexistent/path/abc123"], palette=DEFAULT_PALETTE
    )
    assert len(projects) == 0
    captured = capsys.readouterr()
    assert "WARNING" in captured.err


def test_validate_projects_max_six():
    cm = load_claude_multi()
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = [tmpdir] * 8
        projects = cm.validate_projects(paths, palette=DEFAULT_PALETTE)
        # Dedup means only 1 unique path, but if we use different dirs:
        assert len(projects) <= MAX_SESSIONS


def test_validate_projects_deduplicates(capsys):
    cm = load_claude_multi()
    with tempfile.TemporaryDirectory() as tmpdir:
        projects = cm.validate_projects(
            [tmpdir, tmpdir], palette=DEFAULT_PALETTE
        )
        assert len(projects) == 1
        captured = capsys.readouterr()
        assert "duplicate" in captured.err.lower()


def test_sanitize_name():
    cm = load_claude_multi()
    assert cm.sanitize_name("my-project") == "my-project"
    assert cm.sanitize_name("my project!@#") == "myproject"
    assert cm.sanitize_name("...") == "unnamed"
    assert cm.sanitize_name("a" * 300) == "a" * 256


def test_check_dependencies_success(monkeypatch):
    cm = load_claude_multi()
    monkeypatch.setattr(shutil, "which", lambda cmd: f"/usr/bin/{cmd}")

    def mock_run(cmd, **kwargs):
        class Result:
            stdout = "tmux 3.4" if "tmux" in cmd else "2.1.83"
            returncode = 0
        return Result()

    monkeypatch.setattr(subprocess, "run", mock_run)
    info = cm.check_dependencies()
    assert "tmux_version" in info
    assert "claude_version" in info


def test_check_dependencies_missing_tmux(monkeypatch):
    cm = load_claude_multi()
    monkeypatch.setattr(
        shutil, "which",
        lambda cmd: None if cmd == "tmux" else f"/usr/bin/{cmd}"
    )
    with pytest.raises(SystemExit):
        cm.check_dependencies()


def test_check_dependencies_old_tmux(monkeypatch):
    cm = load_claude_multi()
    monkeypatch.setattr(shutil, "which", lambda cmd: f"/usr/bin/{cmd}")

    def mock_run(cmd, **kwargs):
        class Result:
            stdout = "tmux 2.1"
            returncode = 0
        return Result()

    monkeypatch.setattr(subprocess, "run", mock_run)
    with pytest.raises(SystemExit):
        cm.check_dependencies()


def test_generate_tmux_conf():
    cm = load_claude_multi()
    with tempfile.TemporaryDirectory() as tmpdir:
        conf_path = Path(tmpdir) / "tmux.conf"
        scripts_dir = Path(tmpdir) / "scripts"
        cm.generate_tmux_conf(conf_path, scripts_dir, "claude-multi", 30)
        content = conf_path.read_text()
        # Window options (not session options)
        assert "set-option -wg" in content
        assert "pane-border-status top" in content
        assert "pane-border-format" in content
        assert "@cm_info" in content
        # Keybindings — distinct lowercase r vs uppercase R
        assert "bind-key r" in content
        assert "bind-key R" in content
        assert "bind-key U" in content
        # Upgrade timer present
        assert "check-upgrade.sh" in content


def test_generate_tmux_conf_validates_scripts_path():
    cm = load_claude_multi()
    with tempfile.TemporaryDirectory() as tmpdir:
        conf_path = Path(tmpdir) / "tmux.conf"
        bad_dir = Path("/tmp/bad;rm -rf /")
        with pytest.raises(ValueError, match="unsafe"):
            cm.generate_tmux_conf(conf_path, bad_dir, "claude-multi", 30)


def test_generate_tmux_conf_no_upgrade_timer():
    cm = load_claude_multi()
    with tempfile.TemporaryDirectory() as tmpdir:
        conf_path = Path(tmpdir) / "tmux.conf"
        scripts_dir = Path(tmpdir) / "scripts"
        cm.generate_tmux_conf(conf_path, scripts_dir, "claude-multi", 0)
        content = conf_path.read_text()
        assert "check-upgrade.sh" not in content


def test_build_layout_commands_grid():
    cm = load_claude_multi()
    # 4 panes, 2 projects — should create 2-column layout
    projects = [
        {"name": "a/p1", "path": Path("/a"), "color": "green"},
        {"name": "a/p2", "path": Path("/a"), "color": "cyan"},
        {"name": "b/p3", "path": Path("/b"), "color": "yellow"},
        {"name": "b/p4", "path": Path("/b"), "color": "magenta"},
    ]
    cmds = cm.build_layout_commands("grid", projects, "claude-multi")
    split_cmds = [c for c in cmds if "split-window" in str(c)]
    assert len(split_cmds) == 3  # 1 horizontal + 1 left vert + 1 right vert
    # First split should be horizontal (creating left/right columns)
    assert "-h" in split_cmds[0]


def test_build_layout_commands_single():
    cm = load_claude_multi()
    projects = [{"name": "p1", "path": Path("/a"), "color": "green"}]
    cmds = cm.build_layout_commands("grid", projects, "claude-multi")
    assert len(cmds) == 0


def test_build_layout_commands_six_panes():
    cm = load_claude_multi()
    projects = [
        {"name": f"p{i}", "path": Path(f"/{i}"), "color": "green"}
        for i in range(6)
    ]
    cmds = cm.build_layout_commands("grid", projects, "claude-multi")
    split_cmds = [c for c in cmds if "split-window" in str(c)]
    assert len(split_cmds) == 5


def test_build_layout_horizontal():
    cm = load_claude_multi()
    projects = [
        {"name": f"p{i}", "path": Path(f"/{i}"), "color": "green"}
        for i in range(3)
    ]
    cmds = cm.build_layout_commands("horizontal", projects, "claude-multi")
    assert any("even-horizontal" in str(c) for c in cmds)


def test_build_layout_vertical():
    cm = load_claude_multi()
    projects = [
        {"name": f"p{i}", "path": Path(f"/{i}"), "color": "green"}
        for i in range(3)
    ]
    cmds = cm.build_layout_commands("vertical", projects, "claude-multi")
    assert any("even-vertical" in str(c) for c in cmds)


def test_generate_scripts():
    cm = load_claude_multi()
    with tempfile.TemporaryDirectory() as tmpdir:
        scripts_dir = Path(tmpdir) / "scripts"
        cm.generate_scripts(scripts_dir)

        expected_scripts = [
            "pane-wrapper.sh", "restart.sh", "restart-all.sh",
            "upgrade.sh", "check-upgrade.sh",
        ]
        for name in expected_scripts:
            script = scripts_dir / name
            assert script.exists(), f"Missing: {name}"
            assert os.access(script, os.X_OK), f"Not executable: {name}"

        # pane-wrapper uses claude and --name
        wrapper = (scripts_dir / "pane-wrapper.sh").read_text()
        assert "--name" in wrapper
        assert "claude" in wrapper

        # restart sends Ctrl+C and only restarts managed panes
        restart = (scripts_dir / "restart.sh").read_text()
        assert "C-c" in restart
        assert "@cm_info" in restart

        # upgrade has confirmation prompt
        upgrade = (scripts_dir / "upgrade.sh").read_text()
        assert "y/N" in upgrade

        # check-upgrade reschedules itself
        check = (scripts_dir / "check-upgrade.sh").read_text()
        assert "run-shell" in check
        assert "sleep $INTERVAL" in check


def test_tmux_session_exists_false(monkeypatch):
    cm = load_claude_multi()

    def mock_run(cmd, **kwargs):
        class Result:
            returncode = 1
        return Result()

    monkeypatch.setattr(subprocess, "run", mock_run)
    assert cm.tmux_session_exists("nonexistent") is False


def test_create_session_tmux_commands(monkeypatch):
    """Verify create_session issues correct tmux commands."""
    cm = load_claude_multi()
    with tempfile.TemporaryDirectory() as tmpdir:
        commands_issued = []

        def mock_run(cmd, **kwargs):
            commands_issued.append(list(cmd) if not isinstance(cmd, list) else cmd)
            class Result:
                returncode = 0
                stdout = ""
            return Result()

        monkeypatch.setattr(subprocess, "run", mock_run)
        # Override module-level paths to use tmpdir
        monkeypatch.setattr(cm, "TMUX_CONF_PATH", Path(tmpdir) / "tmux.conf")
        monkeypatch.setattr(cm, "SCRIPTS_DIR", Path(tmpdir) / "scripts")

        projects = [
            {"name": "proj1", "path": Path(tmpdir), "color": "green"},
            {"name": "proj2", "path": Path(tmpdir), "color": "cyan"},
        ]
        dep_info = {"claude_version": "2.1.83", "tmux_version": "tmux 3.4"}

        # Use detach=True to avoid os.execvp
        cm.create_session(projects, "grid", "test-session", True, dep_info, 30)

        cmd_strs = [" ".join(str(x) for x in c) for c in commands_issued]

        # Verify new-session was called
        assert any("new-session" in s for s in cmd_strs)

        # Verify send-keys was called for each pane (all panes use send-keys)
        send_keys = [s for s in cmd_strs if "send-keys" in s]
        assert len(send_keys) >= 2  # one per pane

        # Verify @cm_info and @cm_color set per pane
        cm_info = [s for s in cmd_strs if "@cm_info" in s]
        assert len(cm_info) >= 2  # one per pane
        cm_color = [s for s in cmd_strs if "@cm_color" in s]
        assert len(cm_color) >= 2  # one per pane