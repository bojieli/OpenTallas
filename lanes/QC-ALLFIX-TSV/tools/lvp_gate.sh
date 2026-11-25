#!/bin/bash
# QC-ALLFIX-TSV lvp_gate.sh: BLOCKING ledger-vs-plan gate (COORD 11-25 06:2x item 3). Run before every QC launch/cut.
# usage: lvp_gate.sh PLAN.json LAUNCH_TREE [--drop-list GATE_DROPS.txt ...]   (env LVP_MANIFEST, LVP_TSV override defaults)
#   defaults: manifest + TSV from the hub (~/coord/lanes/QC-ALLFIX-TSV/tools/manifest_current.json, ~/coord/lanes/ALLFIX-QC.tsv),
#   fetched to the lane dir so the run reads a frozen copy. Run it on a build host via
#   ot-run --priority die --crit --mem 64 --threads 1 --dir <lane dir> -- bash lvp_gate.sh ...
# rc 0 = PASS. rc 1 = a TSV row claimed in-plan is ABSENT/PARTIAL (not DEFERRED), NO-SOURCE or ERROR. rc 2 = a manifest
# source file is missing. Launch only on rc 0.
set -uo pipefail
PLAN=$1 TREE=$2 HERE=$(cd "$(dirname "$0")" && pwd)
shift 2
MAN=${LVP_MANIFEST:-$HERE/manifest_current.json} TSV=${LVP_TSV:-$HERE/ALLFIX-QC.tsv}
ST=$(TZ=America/Los_Angeles date +%m%d%H%M)
python3 -I -u "$HERE/ledger_vs_plan.py" --plan "$PLAN" --tree "$TREE" --tsv "$TSV" --manifest "$MAN" --json "$HERE/lvp_gate_$ST.json" "$@"
rc=$?
echo "LVP_GATE rc=$rc plan=$(sha256sum "$PLAN" | cut -c1-12) tsv=$(sha256sum "$TSV" | cut -c1-12) manifest=$(sha256sum "$MAN" | cut -c1-12) json=$HERE/lvp_gate_$ST.json"
exit $rc
