#!/bin/bash
# Hook Claude Code — Stop (fin de session)
curl -s -X POST http://localhost:7777/event \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"stop\",\"timestamp\":$(date +%s)}" \
  > /dev/null 2>&1 || true
