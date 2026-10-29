#!/bin/bash
# mechanics test (never enqueued): fixture views w/ test provenance -> A0 parent kits -> kit_preflight
set -u
WT=/srv/opentallas-scratch2/claude/wt/qc-a0-kits-7-1028
M=/srv/opentallas-scratch2/claude/qc-a0-kits-7-1028/mech; TAG=${1:-cur}
FX=/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/a0_child_fixture
rm -rf $M/$TAG; mkdir -p $M/$TAG/views $M/$TAG/kits
for c in romleaf:ot_qwen_tile_romleaf rawleaf:ot_qwen_tile_lsl_rawfault_m3 node:ot_qwen_tile_node; do
  d=${c%%:*}; m=${c##*:}; v=$M/$TAG/views/$m; mkdir -p $v
  cp $FX/$d/$m.lef $FX/$d/${m}_tt.lib $FX/$d/${m}_ff.lib $v/
  echo '{"views_status":"signoff","verdict":"SIGNED (MECHANICS TEST ONLY)"}' > $v/provenance.json
  echo '{"view_complete":true}' > $v/gates.json
done
cd $WT/physical/die_plan/qwen_compute/cores/legacy
python3 - "$M/$TAG" <<'P'
import json,sys
t=sys.argv[1]; r=json.load(open("../a0/recipes_a0.json"))
for k in ("qfd_tile_nk_a0c","qfd_tile_nl_a0c"):
    for m in r[k]["hard_children"]["views"]: r[k]["hard_children"]["views"][m]=f"{t}/views/{m}"
json.dump(r,open(f"{t}/recipes_a0.json","w"),indent=1)
P
for p in nk nl; do
  python3 gen_core_kit_qc.py --module qfd_tile_${p}_a0c --recipes $M/$TAG/recipes_a0.json --master-slice ../a0_slices --out $M/$TAG/kits > $M/$TAG/gen_$p.log 2>&1; echo "gen $p rc $?"; tail -2 $M/$TAG/gen_$p.log
  K=$(ls -d $M/$TAG/kits/qfd_tile_${p}_a0c* | head -1)
  python3 $WT/tools/die_plan/kit_preflight.py $K --contract --out $M/$TAG/preflight_$p.json > $M/$TAG/preflight_$p.log 2>&1; echo "preflight $p rc $?"; grep -E "FAIL|issue|ERR" $M/$TAG/preflight_$p.log | head -20
done
