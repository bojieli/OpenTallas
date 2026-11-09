#!/bin/bash
# usage: post.sh "<kind>" "<tags>" "<body>" ; appends one queue line, commits, verifies on origin
cd /
kind="$1"; tags="$2"; body="$3"
line="- $(date '+%Y-%m-%d %H:%M') PST ${kind} [S81-TYPES-13 -> ${tags}] ${body}"
printf '%s\n' "$line" >> ~/coord/lanes/COORD-REVIEW-QUEUE.md
timeout 280 ~/coord/bin/coord-commit.sh "S81-TYPES-13: ${kind}" lanes/COORD-REVIEW-QUEUE.md 2>&1 | tail -2
git -C ~/coord fetch -q origin coord/state 2>/dev/null
git -C ~/coord show origin/coord/state:lanes/COORD-REVIEW-QUEUE.md | grep -cF -- "$(printf "%s" "$line" | cut -c1-60)"
