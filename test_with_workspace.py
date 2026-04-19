#!/usr/bin/env python3
"""Test Claude CLI with the exact system prompt the bridge uses."""
import subprocess
from pathlib import Path
from core import build_system_prompt

workspace = Path("/home/brine/.openclaw/workspace")
system_prompt = build_system_prompt(workspace, "Mattermost", "town-square")

print(f"System prompt length: {len(system_prompt)} chars")
print("=" * 80)

cmd = ["claude", "-p", "--output-format", "json", "--model", "claude-opus-4-6"]
cmd.extend(["--append-system-prompt", system_prompt])
cmd.append("Hello, test message")

result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

print(f"Exit code: {result.returncode}")
if result.stderr:
    print(f"STDERR: {result.stderr}")
if result.returncode != 0:
    print(f"STDOUT: {result.stdout}")
else:
    print("✅ Success")
