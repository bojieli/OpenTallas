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
python3 $R/tools/die_port_bind.py $O/die_bound.v "${F[@]}" --rtl-file $O/kv_hard_models.sv --rtl-file $O/kv_relays_dir.sv \
  --rtl-file $R/physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy/ot_qfd_serdes_112g_x12_phy_bb.v \
  --allow-model qkd_hbm3e_phy_pc --allow-model qkd_ckbump --allow-model qkd_fwdbump --allow-model ot_qkvd_ucie_x64_phy \
  --allow-model ot_qfd_serdes_112g_x12_phy --allow-model qkd_pll_analog_model \
  --strap-file $O/straps.json --out $O/port_bind_v2.json > $O/port_bind_v2.txt 2>&1
rc=$?
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
