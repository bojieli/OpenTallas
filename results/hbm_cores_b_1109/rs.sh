#!/bin/bash
# DIE-S81-85 2026-11-09: relaunch of S81-TYPES-13 re-signs ar-cc92f4ce0489 / ar-b91c1fe19588 (disk-refused on epyc4 scratch3 since 00:13); same tag, DB, build commit; out on epyc4 scratch2.
N=$1; T=$2; C=$3
TAG=flow-20261108-eu-s81; TR=/srv/opentallas-scratch3/claude/auto-resign/tools/$TAG
K=/srv/opentallas-scratch2/claude/kw37/eco/$T/i1
O=/srv/opentallas-scratch2/claude/die-s81-85/resign/slice_station__${N}__${TAG}
exec ~/.local/bin/ot-run --mem 32 --threads 8 --hosts epyc4 --no-spill --disk 10 --dir /srv/opentallas-scratch2/claude/die-s81-85/resign --priority die --crit -- python3 -I $TR/resign_driver.py run --auto --kit $K --run-dir $K/run --routed-db $K/run/results/asap7/dp_slice_station__${N}/base/6_final.odb --tag $TAG --repo $TR/tag_manifest.json --tools $TR/tools/die_plan --out $O --build-commit 9d13c8cce9df19dbd554ef09ea5d24a0fbfc9e87 --lane DIE-S81-85 --note "$C" --lec-mem 32g
