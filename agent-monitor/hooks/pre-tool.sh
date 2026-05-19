#!/bin/bash
# Hook Claude Code — PreToolUse
# Placé dans .claude/hooks/pre-tool.sh
# Déclenché avant chaque appel d'outil

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name','unknown'))" 2>/dev/null || echo "unknown")
MODEL=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('model','unknown'))" 2>/dev/null || echo "unknown")

curl -s -X POST http://localhost:7777/event \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"pre_tool\",\"tool\":\"$TOOL_NAME\",\"model\":\"$MODEL\",\"timestamp\":$(date +%s)}" \
  > /dev/null 2>&1 || true
