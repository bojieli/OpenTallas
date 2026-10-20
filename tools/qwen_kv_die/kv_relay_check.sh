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
FWDL=; [ -s "$R/fwd_lanes.json" ] && FWDL=$R/fwd_lanes.json
FWD_ARGS=(); [ -n "$FWDL" ] && FWD_ARGS=(--lanes "$FWDL")
# port_bind_v2.json names the RTL by absolute paths under the prep's source tree (the root before /rtl/ or /physical/)
PFX=$(python3 -c '
import json, re, sys
d = json.load(open(sys.argv[1]))
ps = [v.get("rtl") or "" for v in d["masters"].values()] + list(d.get("rtl_files") or [])
m = next((x for x in (re.match(r"^(/.*?)/(rtl|physical|tools)/", p) for p in ps if p.startswith("/")) if x), None)
print(m.group(1) if m else "")' "$B/port_bind_v2.json" 2>/dev/null)
python3 "$SRC/tools/qwen_layerbench/netlist_relay_stages.py" --die-v "$B/die_bound.v" --port-bind "$B/port_bind_v2.json" \
  --design qwen_kv --commit "$COMMIT" --src-prefix "$SRC/" ${PFX:+--src-prefix "$PFX/"} --local-rtl "$B" --local-rtl "$C" \
  --plan-id "$(basename "$R")-netlist" "${FWD_ARGS[@]}" --out "$RUNT" || { echo "RELAY_CHECK FAIL die-run table export failed"; exit 1; }
# HKV-DIE2 10-19: the static parameters priced from stage counts (hub AP_OFS / FR_OFS, ASTK e_after_header, attention
# fault latencies, the seq KVN bundle) recomputed on THIS netlist table (post lanes / pads / stations) and checked
KSM=; [ -s "$C/static_model.json" ] && KSM=$C/static_model.json
if [ -z "$SCHED" ]; then
  CST=${OT_COMPUTE_RELAY_STAGES:-$SRC/results/rtl/qwen_layer_tput_1018/compiled_L1/die_run/compute_dv2f14bn_relay_stages.json}
  (cd "$SRC" && python3 tools/qwen_layerbench/layer_compile.py --out "$R/layer_compile" --compute-stages "$CST" \
     --kv-stages "$RUNT" --kv-commit "$COMMIT" ${KSM:+--kv-static-model "$KSM" --kv-die-v "$B/die_bound.v" --kv-case-die-v "$C/die.v"} ${FWDL:+--kv-fwd-lanes "$FWDL"}) || { echo "RELAY_CHECK FAIL calendar compiler (layer_compile.py) failed on this die"; exit 1; }
  SCHED=$(ls "$R"/layer_compile/relay_schedule/kv_compiled.json* | head -1)
fi
# QLB-KV 10-18 (QXF-LINK F4): the TXDP the die BINDS on d2d_kv (qkd_d2d_static #(.TXDP), kv_die.d2d_txdp_k) must equal
# the vector the calendar compiler derives for THIS die's stages (RUN/layer_compile/d2d/txdp.svh QKD_D2D_TXDP); a missing
# or different TXDP is a FAIL (re-GEN with OT_KV_D2D_TXDP_K=<compiled>).  Only when the schedule was compiled here.
if [ -s "$R/layer_compile/d2d/txdp.svh" ]; then
  TXL=$(python3 - "$B/die_bound.v" "$R/layer_compile/d2d/txdp.svh" <<'PY'
import re, sys
v = open(sys.argv[1]).read(); t = open(sys.argv[2]).read()
m = re.search(r"QKD_D2D_TXDP\s*=\s*\{8'd(\d+),\s*8'd(\d+),\s*8'd(\d+),\s*8'd(\d+)\}", t)
comp = [int(x) for x in m.groups()][::-1] if m else None          # {p3,p2,p1,p0} -> [p0..p3]
b = re.findall(r"\bqkd_d2d_static\s*#\(([^;]*?)\)\s*[A-Za-z_]\w*\s*\(", v, re.S)
got = []
for prm in b:
    mm = re.search(r"\.TXDP\(\s*(?:32'h([0-9a-fA-F_]+)|(\d+))\s*\)", prm)
    got.append(None if not mm else (int(mm.group(1).replace('_', ''), 16) if mm.group(1) else int(mm.group(2))))
bv = [[(g >> (8 * k)) & 0xff for k in range(4)] if g is not None else None for g in got]
ok = bool(comp) and len(bv) == 1 and bv[0] == comp
print(("TXDP_K PASS" if ok else "TXDP_K FAIL") + f" bound {bv} (qkd_d2d_static instances {len(bv)}) compiled {comp}")
PY
)
  echo "$TXL"
  case "$TXL" in "TXDP_K PASS"*) ;; *) echo "RELAY_CHECK FAIL $TXL"; exit 1;; esac
fi
RCL=$(bash "$SRC/tools/die_relay_chain_step.sh" "$RUNT" "$SCHED" "$R/relay_check.json") && RCR=0 || RCR=$?
if [ -n "$KSM" ]; then
  python3 "$SRC/tools/qwen_kv_die/kv_static_params.py" --model "$KSM" --table "$RUNT" ${FWDL:+--fwd-lanes "$FWDL"} \
    --die-v "$B/die_bound.v" --case-die-v "$C/die.v" --out "$R/static_params.json" > "$R/static_params.log" 2>&1 && KSR=0 || KSR=$?
  tail -1 "$R/static_params.log" | cut -c1-1500
  if [ "$KSR" != 0 ]; then echo "${RCL/RELAY_CHECK PASS/RELAY_CHECK FAIL} | KV_STATIC_PARAMS FAIL ($R/static_params.json)"; exit 1; fi
fi
echo "$RCL"; exit $RCR
