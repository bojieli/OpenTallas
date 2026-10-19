#!/bin/bash
# QXF-SEAMK 2026-10-18 (TOKEN-XDIE-QWEN F6): the KV die chain's RELAY_CHECK -- never SKIPPED.
#   kv_relay_check.sh RUN SRC        (die_chain.sh runs it after the strict bind; usable offline on any prep RUN)
# 1. die-run table RUN/relay_stages_netlist.json[.gz]: tools/qwen_layerbench/netlist_relay_stages.py on the bound GEN netlist
#    RUN/port_bind_v2/die_bound.v (the generator-model export case_kv/relay_stages.json is not used: kvs14c never wrote
#    one, and the netlist is what is built);
# 2. schedule: $OT_RELAY_SCHEDULE when it names a table; else the calendar compiler against THIS die,
#    tools/qwen_layerbench/layer_compile.py --kv-stages <1.> --compute-stages $OT_COMPUTE_RELAY_STAGES (default the
#    committed dv2f14bn table) -> RUN/layer_compile/ (relay_schedule/kv_compiled.json*, d2d calendars, TXDP, KV programme);
# 3. tools/die_relay_chain_step.sh: tools/die_relay_check.py -> RUN/relay_check.json (stage diffs + torn record bundles).
# OT_RELAY_SCHEDULE=skip prints RELAY_CHECK SKIPPED (explicit, never by default).  Last line RELAY_CHECK PASS|FAIL|SKIPPED.
set -u
R=$(readlink -f "$1"); SRC=$(readlink -f "$2")
C=$R/case_kv; B=$R/port_bind_v2
SCHED=${OT_RELAY_SCHEDULE:-}
if [ "$SCHED" = skip ]; then echo "RELAY_CHECK SKIPPED by OT_RELAY_SCHEDULE=skip (explicit)"; exit 0; fi
[ -s "$B/die_bound.v" ] && [ -s "$B/port_bind_v2.json" ] || { echo "RELAY_CHECK FAIL no bound netlist $B/die_bound.v / port_bind_v2.json (kv_port_bind_v2.sh)"; exit 1; }
COMMIT=$(cat "$C/SOURCE_COMMIT" 2>/dev/null || git -C "$SRC" rev-parse --short=9 HEAD)
RUNT=$R/relay_stages_netlist.json.gz
# port_bind_v2.json names the RTL by absolute paths under the prep's source tree (the root before /rtl/ or /physical/)
PFX=$(python3 -c '
import json, re, sys
d = json.load(open(sys.argv[1]))
ps = [v.get("rtl") or "" for v in d["masters"].values()] + list(d.get("rtl_files") or [])
m = next((x for x in (re.match(r"^(/.*?)/(rtl|physical|tools)/", p) for p in ps if p.startswith("/")) if x), None)
print(m.group(1) if m else "")' "$B/port_bind_v2.json" 2>/dev/null)
python3 "$SRC/tools/qwen_layerbench/netlist_relay_stages.py" --die-v "$B/die_bound.v" --port-bind "$B/port_bind_v2.json" \
  --design qwen_kv --commit "$COMMIT" --src-prefix "$SRC/" ${PFX:+--src-prefix "$PFX/"} --local-rtl "$B" --local-rtl "$C" \
  --plan-id "$(basename "$R")-netlist" --out "$RUNT" || { echo "RELAY_CHECK FAIL die-run table export failed"; exit 1; }
if [ -z "$SCHED" ]; then
  CST=${OT_COMPUTE_RELAY_STAGES:-$SRC/results/rtl/qwen_layer_tput_1018/compiled_L1/die_run/compute_dv2f14bn_relay_stages.json}
  (cd "$SRC" && python3 tools/qwen_layerbench/layer_compile.py --out "$R/layer_compile" --compute-stages "$CST" \
     --kv-stages "$RUNT" --kv-commit "$COMMIT") || { echo "RELAY_CHECK FAIL calendar compiler (layer_compile.py) failed on this die"; exit 1; }
  SCHED=$(ls "$R"/layer_compile/relay_schedule/kv_compiled.json* | head -1)
fi
bash "$SRC/tools/die_relay_chain_step.sh" "$RUNT" "$SCHED" "$R/relay_check.json"
