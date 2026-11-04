#!/bin/bash
cd /srv/opentallas-scratch2/claude/dh58/proto && python3 /srv/opentallas-scratch2/claude/dh58/proto/wt/tools/clk/ot_clk.py kit clk/head_l48rf.yaml --out clk/kit_l48rf --die-trial /srv/opentallas-scratch2/claude/dh56-cland/src/tools/die_plan/die_trial.py > clk/kit_l48rf.log 2>&1; echo KIT rc=$? >> clk/kit_l48rf.log
