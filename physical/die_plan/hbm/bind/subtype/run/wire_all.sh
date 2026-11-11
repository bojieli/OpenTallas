#!/bin/bash
# BIND-SUBTYPE-2: wiring check of every type touched by the subtype bind + one-bit-swap negative control.
set -o pipefail
L=${BST_L:-/srv/opentallas-scratch2/claude/bind-subtype-1111}
NEW=$L/bind_p11t_taps_cyc_vK5d_c12_subtype
OLD=${BST_OLD:-/srv/opentallas-scratch2/claude/die-hbm-97-taps/bind/bind_p11t_taps_cyc_vK5d_c12}
T=$L/src_ov/tools/die_plan/subtype_wiring_check.py
[ -f "$T" ] || T=$L/wiring_check.py
W=$L/wiring; mkdir -p "$W"; touch "$W/DO_NOT_COUNT"
python3 -I -c "import json,sys;json.dump(json.load(open('$NEW/asbuilt_subtype.json'))['subtype_bind'][0],open('$W/rule_sfu.json','w'),indent=1)"
TYPES=$(grep -l "ot_hgi_sfu_split3_lane_core__idpin__bsub" "$NEW"/rtl/hbm_arch_*.sv | sed -E 's#.*/hbm_arch_(.*)\.sv#\1#' | sort)
echo "TYPES $(echo $TYPES | wc -w): $TYPES"
for t in $TYPES; do
  python3 -I "$T" "$OLD/rtl/hbm_arch_$t.sv" "$NEW/rtl/hbm_arch_$t.sv" "$W/rule_sfu.json" --out "$W/$t.json" | sed "s/^/$t /"
done
# negative control: swap bits 0/1 of the first substituted instance's .sfu_vi_q connection in a copy of NEW q_b110
python3 -I - "$NEW/rtl/hbm_arch_q_b110.sv" "$W/neg_q_b110.sv" <<'EOF'
import re, sys
t = open(sys.argv[1]).read()
m = re.search(r"\.sfu_vi_q\s*\(", t)
i = m.end(); d = 1; j = i
while d:
    d += {"(": 1, ")": -1}.get(t[j], 0); j += 1
e = t[i:j - 1].strip()
n, hi, lo = re.fullmatch(r"(\w+)\[(\d+):(\d+)\]", e).groups()
hi, lo = int(hi), int(lo)
neg = "{%s[%d:%d], %s[%d], %s[%d]}" % (n, hi, lo + 2, n, lo, n, lo + 1)   # bits 0 and 1 exchanged
open(sys.argv[2], "w").write(t[:i] + neg + t[j - 1:])
print("NEG swapped", e[:80])
EOF
python3 -I "$T" "$OLD/rtl/hbm_arch_q_b110.sv" "$W/neg_q_b110.sv" "$W/rule_sfu.json" --out "$W/neg_q_b110.json" | sed "s/^/NEG q_b110 /"; echo "NEG_RC ${PIPESTATUS[0]}"
