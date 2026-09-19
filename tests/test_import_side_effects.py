from __future__ import annotations

import subprocess
import sys


def test_importing_package_performs_no_network_process_or_git_side_effects() -> None:
    """Import in a fresh interpreter with network sockets and subprocess spawning
    patched to raise, proving import alone touches neither.
    """
    probe = (
        "import socket, subprocess\n"
        "def _deny_socket(*a, **k):\n"
        "    raise AssertionError('import must not open a network socket')\n"
        "def _deny_popen(*a, **k):\n"
        "    raise AssertionError('import must not spawn a process')\n"
        "socket.socket = _deny_socket\n"
        "subprocess.Popen = _deny_popen\n"
        "import agentic_harness\n"
        "print('OK', agentic_harness.__version__)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("OK ")


def test_importing_package_creates_no_new_files(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())
    result = subprocess.run(
        [sys.executable, "-c", "import agentic_harness"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    after = set(tmp_path.iterdir())
    assert before == after
