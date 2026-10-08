#!/bin/bash
# OWNER OPTION B (2026-10-07): setup at TT closes a block; SS is a sensitivity.  Re-time an existing routed result
# at TT without touching it: the job's own w18_sta_ss.tcl (same odb / spef / sdc / extra SDCs / OT_* reductions)
# with the SS standard-cell and macro libraries swapped for TT.  Writes OUT_JSON (setup_tt record).
# usage: tt_resta.sh ORFS_DIR SRC_DIR OUT_JSON
set -u
ORFS=$1; SRC=$2; OUT=$3; D=$(dirname "$OUT"); mkdir -p "$D"
T=$ORFS/w18_sta_ss.tcl
if [ ! -f "$T" ]; then echo "{\"error\": \"no $T (setup_tt unmeasurable)\"}" > "$OUT"; exit 3; fi
TCL=$D/tt_resta_$(basename "$OUT" .json).tcl
sed -e 's/_\(S\?L\?\|R\)VT_SS_nldm/_\1VT_TT_nldm/g' -e 's/_ss\.lib/_tt.lib/g' -e 's/^puts "OT_CORNER ss"/puts "OT_CORNER tt"/' "$T" > "$TCL"
LOG=${TCL%.tcl}.log
timeout 5400 docker run --rm -v "$ORFS:/work:ro" -v "$SRC:/src:ro" -v "$D:/tt" openroad/orfs:asap7lock bash -lc \
  "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /tt/$(basename "$TCL")" > "$LOG" 2>&1
python3 - "$LOG" "$OUT" "$TCL" <<'PY'
import json, re, sys, hashlib
log, out, tcl = sys.argv[1:4]
s = open(log, errors="replace").read()
g = lambda k: (re.search(rf"^{k} (\S+)", s, re.M) or [None, None])[1]
f = lambda v: None if v in (None, "INF", "1e9", "1e+09") else round(float(v) * (1e12 if abs(float(v)) < 1e-3 else 1), 2)
rec = dict(corner="tt", check="setup", source="tt_resta.sh (job's w18_sta_ss.tcl with TT libraries)",
           worst_slack_ps=round(float(g("OT_WS")) * 1e12, 2) if g("OT_WS") else None,
           tns_ps=round(float(g("OT_TNS")) * 1e12, 1) if g("OT_TNS") else None,
           worst_reg_to_reg_slack_ps=g("OT_WS_R2R"), worst_input_to_reg_slack_ps=g("OT_WS_I2R"),
           worst_output_port_slack_ps=g("OT_WS_OUT"), violating_d_pins=g("OT_VIOL_D_PINS"),
           errors=re.findall(r"\[ERROR[^\n]*|^Error[^\n]*", s, re.M)[:5],
           tcl_sha256=hashlib.sha256(open(tcl, "rb").read()).hexdigest())
json.dump(dict(setup_tt=rec), open(out, "w"), indent=1)
print(json.dumps(rec))
PY
