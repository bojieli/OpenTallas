#!/usr/bin/env bash
# Slot cell qkd_kvwq_leaf_s_w129_m: bit-exact bench through the die buses (and the mutant with a 2nd argument).
#   bench.sh OUT_DIR [mut]
# Prints "PASS kvwq_leaf_slot ..." (rc 0) or "FAIL kvwq_leaf_slot ..." (rc 1).
set -u
OUT=$1; MUT=${2:-}
R=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
# field offsets from the die's bind convention (kv_die.BINDINGS, LSB first), independent of the wrapper
python3 - "$R" > "$OUT/kvwq_leaf_slot_map.vh" <<'PY' || { echo "FAIL kvwq_leaf_slot map"; exit 1; }
import sys
sys.path.insert(0, sys.argv[1] + '/tools/qwen_kv_die')
import kv_die
W = dict(c_v=1, c_d=256, c_sec=24, c_lane=3, c_tag=9, n_v=1, n_d=256, n_sec=24, n_lane=3, n_tag=9, dn_v=1, dn_bad=1,
         dp_v=1, dp_bad=1, w_v=1, w_sec=24, w_data=256, w_tag=9, w_room=1, wd_v=1, wd_tag=9)
MAC = dict(c_v='C_V', c_d='C_D', c_sec='C_SEC', c_lane='C_LANE', c_tag='C_TAG', dn_v='DN_V', dn_bad='DN_BAD',
           dp_v='DP_V', dp_bad='DP_BAD', w_v='W_V', w_sec='W_SEC', w_data='W_DATA', w_tag='W_TAG', w_room='WR_ROOM',
           wd_v='WR_WDV', wd_tag='WR_WDTAG')
P = kv_die.BINDINGS['qkd_kvwq_leaf_s_w129_m']['ports']
for dp, tot in (('c', 293), ('n', 293), ('dn', 2), ('dp', 2), ('w', 290), ('wr', 11)):
    o = 0
    for rp in P[dp]:
        if rp in MAC:
            print('`define %s %d' % (MAC[rp], o))
        o += W[rp]
    assert o == tot, (dp, o)
assert [p[2:] for p in P['n']] == [p[2:] for p in P['c']]
PY
D=""; [ -n "$MUT" ] && D="-DOT_QKD_KVWQ_LEAF_MUT"
iverilog -g2012 $D -I "$OUT" -o "$OUT/tb" "$R/rtl/test/tb_qkd_kvwq_leaf_slot.sv" \
    "$R/rtl/qwen_sys/kv_die_20261009/qkd_kvwq_leaf_slot.sv" "$R/rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_tiles.sv" > "$OUT/build.log" 2>&1 \
    || { cat "$OUT/build.log"; echo "FAIL kvwq_leaf_slot build"; exit 1; }
vvp "$OUT/tb" > "$OUT/run.log" 2>&1
L=$(grep -E '^(PASS|FAIL) kvwq_leaf_slot' "$OUT/run.log" | tail -1)
case "$L" in
  PASS*) echo "$L"; exit 0 ;;
  FAIL*) echo "FAIL kvwq_leaf_slot${MUT:+ mutant detected} ${L#FAIL kvwq_leaf_slot }"; exit 1 ;;
  *) tail -5 "$OUT/run.log"; echo "FAIL kvwq_leaf_slot no verdict"; exit 1 ;;
esac
