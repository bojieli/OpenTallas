#!/bin/bash
# Q-KVSYS-NETLIST 2026-10-16: STRICT bit-level port bind (tools/die_port_bind.py, opentallas.die_port_bind.v2) of a KV/system
# die netlist.  1. kv_bound_netlist.py rewrites every bound die master into its kv_die.BINDINGS RTL module on the same die
# bits (die-top straps folded and declared, off-chip pads as top inputs, analog hard macros as port models);
# 2. die_port_bind.py on the bound netlist with the relay RTL, the hard models (--allow-model) and the strap list.
# usage: kv_port_bind_v2.sh DIE_V OUTDIR [RELAY_RTL] [EXPAND_JSON]     (exit 0 only when the die binds)
#   RELAY_RTL default DIE_V's dir/qkd_kv_relays.sv; EXPAND_JSON default DIE_V's dir/../expand.json
set -u
D=$(readlink -f "$1"); O=$(mkdir -p "$2" && readlink -f "$2")
R=$(cd "$(dirname "$0")/../.." && pwd)
RLY=${3:-$(dirname $D)/qkd_kv_relays.sv}; EXP=${4:-$(dirname $(dirname $D))/expand.json}
A=(); [ -f "$RLY" ] && A+=(--relay-rtl "$(readlink -f $RLY)"); [ -f "$EXP" ] && A+=(--expanded "$(readlink -f $EXP)")
python3 $R/tools/qwen_kv_die/kv_bound_netlist.py $D "${A[@]}" --out-dir $O > $O/bound_netlist.log 2>&1 || { tail -3 $O/bound_netlist.log; exit 3; }
F=(); [ -f "$RLY" ] && F+=(--rtl-file "$(readlink -f $RLY)")
# Exact per-replica paired zero-input/private-spare-output bits, preserving every other output requirement.
P=(); [ -f "$D.pads.json" ] && P+=(--existing "$D.pads.json")
python3 "$R/tools/qwen_kv_die/kv_output_pads.py" "$O/die_bound.v" "${P[@]}" --out "$O/output_pads.json" \
  > "$O/output_pads.log" 2>&1 || { tail -3 "$O/output_pads.log"; exit 3; }
PADS="$O/output_pads.json"
if [ "${OT_KV_STATIC_DIE:-0}" = 1 ]; then
  [ -f "$EXP" ] || { echo "static head output contract requires expand provenance"; exit 3; }
  python3 "$R/tools/qwen_kv_die/kv_static_head_unused.py" --run "$(dirname "$EXP")" --die "$O/die_bound.v" \
    --root "$R" --existing "$PADS" --out "$O/output_pads.head.json" > "$O/output_pads.head.log" 2>&1 \
    || { tail -3 "$O/output_pads.head.log"; exit 3; }
  PADS="$O/output_pads.head.json"
  python3 "$R/tools/qwen_kv_die/kv_pvw_padding.py" --run "$(dirname "$EXP")" --die "$O/die_bound.v" \
    --root "$R" --existing "$PADS" --out "$O/output_pads.pv.json" > "$O/output_pads.pv.log" 2>&1 \
    || { tail -3 "$O/output_pads.pv.log"; exit 3; }
  PADS="$O/output_pads.pv.json"
  # KV-FUNC-OPENS 10-19 (OT_KV_FUNC_OPENS=1): relay width-padding + landing ties, then PVW residual roles (exact,
  # die/source-pinned contracts). The ASTK/head/ECTL role contract needs a first-pass record (second pass below).
  if [ "${OT_KV_FUNC_OPENS:-0}" = 1 ]; then
    python3 "$R/tools/qwen_kv_die/kv_relay_zero_tail.py" "$O/die_bound.v" --root "$R" --existing "$PADS" \
      --out "$O/output_pads.zt.json" > "$O/output_pads.zt.log" 2>&1 || { tail -3 "$O/output_pads.zt.log"; exit 3; }
    python3 "$R/tools/qwen_kv_die/kv_pvw_residual_roles.py" --die "$O/die_bound.v" --root "$R" \
      --existing "$O/output_pads.zt.json" --out "$O/output_pads.pvwres.json" > "$O/output_pads.pvwres.log" 2>&1 \
      || { tail -3 "$O/output_pads.pvwres.log"; exit 3; }
    PADS="$O/output_pads.pvwres.json"
  fi
fi
F+=(--pad-file "$PADS")
# relay standards (OT_KV_RLY_STD=1): the qkd_rlys_* replicas bind their real RTL (not a stub)
grep -q "qkd_rlys_" "$D" && F+=(--rtl-file "$R/rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv")
# KV-CLOCK 10-18 (OT_KV_FWD=1, kv_fwd_lanes.py): forwarded half-cycle lane stations + landings bind their real RTL
grep -qE "qkd_(rlysh0?|landsh0?)_" "$D" && F+=(--rtl-file "$R/rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv" \
  --rtl-file "$R/rtl/qwen_split/qfd_fwd_lane.sv" --rtl-file "$R/rtl/hdc/ot_hdc_cg.sv")
# KV-WIRE2 10-18: the static die's generated tile modules (qkd_kvs_*) exist in one file per design point
# (kv_static_die.RTL_FILE: _hroot / _ff / _ep / _k): bind the ACTIVE point's file (kvw2-6ad1dbb84: the checker resolved the
# tiles AMBIGUOUS to another point's text -> 6 width mismatches, 94 unconnected inputs, 76,364 undriven bits)
if [ "${OT_KV_STATIC_DIE:-0}" = 1 ]; then
  KT=$(cd $R/tools/qwen_kv_die && python3 -c 'import kv_static_die as S; print(S.RTL_FILE)' 2>/dev/null | tail -1)
  [ -n "$KT" ] && [ -f "$R/$KT" ] && F+=(--rtl-file "$R/$KT")
fi
python3 $R/tools/die_port_bind.py $O/die_bound.v "${F[@]}" --rtl-file $O/kv_hard_models.sv --rtl-file $O/kv_relays_dir.sv \
  --rtl-file $R/physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy/ot_qfd_serdes_112g_x12_phy_bb.v \
  --allow-model qkd_hbm3e_phy_pc --allow-model qkd_ckbump --allow-model qkd_fwdbump --allow-model ot_qkvd_ucie_x64_phy \
  --allow-model ot_qfd_serdes_112g_x12_phy --allow-model qkd_pll_analog_model \
  --strap-file $O/straps.json --out $O/port_bind_v2.json > $O/port_bind_v2.txt 2>&1
rc=$?
if [ "${OT_KV_STATIC_DIE:-0}" = 1 ] && [ "${OT_KV_FUNC_OPENS:-0}" = 1 ]; then
  # second pass: misc role contract derived against the first-pass master RTL map of the SAME die
  cp $O/port_bind_v2.json $O/port_bind_v2.pass1.json
  python3 "$R/tools/qwen_kv_die/kv_misc_unused_roles.py" "$O/die_bound.v" --bind-record $O/port_bind_v2.pass1.json \
    --root "$R" --existing "$PADS" --out "$O/output_pads.misc.json" > "$O/output_pads.misc.log" 2>&1 \
    || { tail -3 "$O/output_pads.misc.log"; exit 3; }
  F2=(); for x in "${F[@]}"; do [ "$x" = "$PADS" ] && x="$O/output_pads.misc.json"; F2+=("$x"); done
  python3 $R/tools/die_port_bind.py $O/die_bound.v "${F2[@]}" --rtl-file $O/kv_hard_models.sv --rtl-file $O/kv_relays_dir.sv \
    --rtl-file $R/physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy/ot_qfd_serdes_112g_x12_phy_bb.v \
    --allow-model qkd_hbm3e_phy_pc --allow-model qkd_ckbump --allow-model qkd_fwdbump --allow-model ot_qkvd_ucie_x64_phy \
    --allow-model ot_qfd_serdes_112g_x12_phy --allow-model qkd_pll_analog_model \
    --strap-file $O/straps.json --out $O/port_bind_v2.json > $O/port_bind_v2.txt 2>&1
  rc=$?
fi
# per DIE master: its bound RTL module and instance count (tools/die_completeness.py reports the die masters)
python3 - $O <<'PY'
import json, sys
from pathlib import Path
o = Path(sys.argv[1])
r = json.loads((o / 'port_bind_v2.json').read_text())
b = json.loads((o / 'bound_netlist.json').read_text())
r['die_masters'] = {m: dict(module=v['module'], instances=v['instances'], how=v['how']) for m, v in b['masters'].items()}
r['bound_netlist'] = dict(record=str(o / 'bound_netlist.json'), die_v=b['die_v'], die_sha256=b['die_sha256'],
                          constant_nets_by_class=b['constant_nets_by_class'], off_chip_inputs=b['off_chip_inputs'])
(o / 'port_bind_v2.json').write_text(json.dumps(r, indent=1) + '\n')
PY
tail -1 $O/port_bind_v2.txt
exit $rc
