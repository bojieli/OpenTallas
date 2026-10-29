#!/bin/bash
set -euo pipefail
w=/srv/opentallas-scratch2/claude/wt/codex-hbm-selector-gen-1029
r=/srv/opentallas-scratch2/claude/codex-selector-gen-1029
p=/srv/opentallas-scratch2/claude/die-hbm-10/c25b
v=/srv/opentallas-scratch2/claude/hbm-cores-kits-4/k9/views.json
m=$w/results/hbm_cores_kits_3/mp/ot_hbm_idx_selector_static_sel.json
python3 "$w/results/die_hbm_kits_1027/mk_c20.py" "$p" "$v" "$r/slices" "$r/kits" "$w" ot_hbm_idx_selector_static_sel --tag _codex_st1 --avoid-macros "$m" --gen-args "--macro-placement $m --macro-inst-fmt {k}" > "$r/gen.log" 2>&1
python3 - "$r/kits/mk_c20_result.json" <<'CHECK'
import json,sys
r=json.load(open(sys.argv[1])); rows=[x for v in r.values() for x in v]
assert rows and all(x["rc"] == 0 and x.get("kit") for x in rows), rows
CHECK
n=0
for k in "$r"/kits/*;do
 [ -f "$k/freeze.json" ] || continue
 n=$((n+1))
 python3 "$w/tools/die_plan/kit_preflight.py" --contract --plan-dir "$p" --out "$r/preflight.json" "$k" > "$r/preflight.log" 2>&1
done
test "$n" = 1
echo SELECTOR_GEN_PREFLIGHT_DONE
