#!/bin/bash
cd /srv/opentallas-scratch2/claude/qct12/repo || exit 2
set -x
git config user.name "QC-TYPES-12" ; git config user.email "noreply@anthropic.com"
git fetch -q origin main 2>&1 | tail -1
for s in 685b58b80c3 a1bd215ec93 b9065f3dddc; do git rev-parse --verify -q $s^{commit} || echo MISSING $s; done
git checkout -q -B qct12-compose 685b58b80c3 2>&1 | tail -2
for p in a1bd215ec93 b9065f3dddc bf29a7a50e cbd4c6adfd9 fea7df0c0a6 958a7d6d7fe; do
  git merge -q --no-edit -m "compose $p" $p 2>&1 | tail -3 || { echo CONFLICT $p; git status --short | head -30; exit 3; }
  git rev-parse HEAD
done
