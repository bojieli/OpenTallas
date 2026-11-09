#!/bin/bash
# DIE-S81-85 2026-11-09: re-sign of t47 station ECO i1 (S81-TYPES-13, --owner-override one iteration, LOCAL_PASS_NEEDS_PARENT TT +86.11 FF +0.26, routed LEC EQ) on the current S81 tag; copy of epyc2 pass dir on epyc6 (md5 of 6_final.odb equal).
TAG=flow-20261109-fb-s81; TR=/srv/opentallas-scratch3/claude/auto-resign/tools/$TAG
K=/srv/opentallas-scratch2/claude/die-s81-85/t47eco/i1
O=/srv/opentallas-scratch2/claude/die-s81-85/resign/slice_station__t47__$TAG
exec ~/.local/bin/ot-run --mem 32 --threads 8 --hosts epyc6 --no-spill --disk 2 --dir /srv/opentallas-scratch2/claude/die-s81-85 --priority die --crit -- python3 -I $TR/resign_driver.py run --auto --kit $K --run-dir $K/run --routed-db $K/run/results/asap7/dp_slice_station__t47/base/6_final.odb --tag $TAG --repo $TR/tag_manifest.json --tools $TR/tools/die_plan --out $O --lane DIE-S81-85 --note "t47 ECO i1 (S81-TYPES-13, OWNER RULING 17:5x --owner-override, one iteration) LOCAL_PASS_NEEDS_PARENT TT 86.11 FF 0.26 DRV 0 DRC 0 routed LEC EQ" --lec-mem 32g
