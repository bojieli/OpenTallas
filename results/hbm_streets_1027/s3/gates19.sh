#!/bin/bash
# HBM-STREETS-3 C19 (plan 33bd5b58002f): G0 + G0C, tools = worktree claude/hbm-streets3-1027@bb18484e01 (street rule + HC128 overlay schema + PENDING-VIEW merged clock)
cd /srv/opentallas-scratch2/claude/hbm-streets3-1027/c19; mkdir -p gates/g0 gates/g0c
C=/srv/opentallas-scratch2/claude/wt/hbm-streets3-1027/tools/die_plan/check.py
python3 $C die_plan.json --out gates/g0 > gates_g0.log 2>&1; echo $? > gates_g0.exit &
python3 $C die_plan.json --completeness --out gates/g0c --png > gates_g0c.log 2>&1; echo $? > gates_g0c.exit &
wait
