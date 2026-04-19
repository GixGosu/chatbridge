#!/usr/bin/env python3
import subprocess
import json

# Simulate exactly what the bridge does
cmd = ["claude", "-p", "--output-format", "json", "--model", "claude-opus-4-6"]
cmd.extend(["--append-system-prompt", "Test system prompt"])
cmd.append("Hello, are you working?")

print(f"Running: {' '.join(cmd)}")
print("-" * 80)

result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

print(f"Exit code: {result.returncode}")
print(f"\nSTDOUT:\n{result.stdout}")
print(f"\nSTDERR:\n{result.stderr}")

if result.returncode != 0:
    print(f"\n❌ FAILED - Exit code {result.returncode}")
else:
    print(f"\n✅ SUCCESS")
    try:
        data = json.loads(result.stdout)
        print(f"Response: {data.get('result', 'N/A')}")
    except json.JSONDecodeError:
        print("Could not parse JSON response")
