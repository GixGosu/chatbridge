#!/usr/bin/env python3
"""Test that onboarding channel context loads correctly."""
from pathlib import Path
from core import build_system_prompt

workspace = Path("/home/brine/claude-bridge-workspace")
channel_name = "onboarding-meridian"

system_prompt = build_system_prompt(workspace, "Mattermost", channel_name)

print(f"System prompt length: {len(system_prompt)} chars")
print("=" * 80)
print(system_prompt)
print("=" * 80)

# Check if channel context is present
if "Meridian Labs" in system_prompt:
    print("✅ Channel context loaded successfully!")
    print("✅ Found 'Meridian Labs' in system prompt")
else:
    print("❌ Channel context NOT loaded")
    print("❌ 'Meridian Labs' not found in system prompt")

if "Channel context: #onboarding-meridian" in system_prompt:
    print("✅ Channel context header present")
else:
    print("❌ Channel context header missing")
