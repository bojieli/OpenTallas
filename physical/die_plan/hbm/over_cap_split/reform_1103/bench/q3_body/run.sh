#!/usr/bin/env bash
# DIE-HBM-61/SPLIT q3_body lock-step: uncut kit core ot_hfd_coll_q3_body_core (kit face shell, as-built netlist) vs the split
# composition ot_hfd_coll_q3_body_core__split (CTL__fs + 4 x QCOL4__fs).  Fleet host only (verilator 5, memory-capped scope).
#   run.sh KITRTL SRAMDIR OUT [MUTS]     MUT 0 must PASS; MUT 1/2/3 must FAIL.  SRAMDIR = behavioural SRAM models (*.v).
set -u
KR=$1; SR=$2; O=$3; MUTS=${4:-"0 1 2 3"}
H=$(cd "$(dirname "$0")" && pwd); R=$H/../..; RT=$H/../../../../../../../rtl/hbm_accel/cores_split/reform_1103/ot_hfd_coll_q3_body_core
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}; mkdir -p "$O/gen"
python3 "$H/gen_q3_body_split.py" "$KR" "$O/gen" || exit 1
python3 "$R/facewrap.py" --top ot_hfd_coll_q3_body_ctl --out "$O/gen/ctl__fs.sv" --clk-re '^clk$' --rst-re '^rst_n$' \
  "$O/gen/ot_hfd_coll_q3_body_ctl.sv" "$SR"/*_bb.v > "$O/ctl_ports.json" || exit 1
python3 "$R/facewrap.py" --top ot_hfd_coll_q3_qcol4 --out "$O/gen/qcol4__fs.sv" --clk-re '^clk$' --pass-param MUT \
  "$H/qcol4_portstub.v" > "$O/qcol_ports.json" || exit 1
python3 - "$KR/ot_hfd_coll_q3_body_core__fshell.sv" "$H/spec_base.json" "$O/spec.json" <<'PY'
import json, re, sys
s = open(sys.argv[1]).read(); s = s[s.index('module '):].split(');')[0]
P = {n: [d, int(h) + 1 if h else 1] for d, h, l, n in re.findall(r'^\s*(input|output) wire (?:\[(\d+):(\d+)\] )?(\w+),?$', s, re.M)}
b = json.load(open(sys.argv[2])); b['ports'] = P
dens = b.pop('valid_dens', 8)
for n, (d, w) in P.items():   # 1-bit control inputs: sparse pulses (density 1/dens), as the 10-25 q3 lock-step
    if d == 'input' and w == 1 and n not in b['clocks'] + b['resets'] and n not in b.get('stim', {}):
        b.setdefault('stim', {})[n] = f'($urandom() % {dens}) == 0'
json.dump(b, open(sys.argv[3], 'w'), indent=1)
PY
python3 "$R/lockstep_gen.py" "$O/spec.json" "$O/tb.sv"
for M in $MUTS; do
  sed "s/ot_hfd_coll_q3_body_core__split u_dut/ot_hfd_coll_q3_body_core__split #(.MUT($M)) u_dut/" "$O/tb.sv" > "$O/tb_m$M.sv"
  rm -rf "$O/obj_m$M"
  systemd-run --user --scope -q -p MemoryMax=${MEMG:-64}G $V --binary -j 16 --output-split 30000 --output-split-cfuncs 3000 \
    -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb -Mdir "$O/obj_m$M" -o sim "$O/tb_m$M.sv" \
    "$KR"/ot_hbm_face_reg.sv "$KR"/ot_hfd_coll_q3_body_core__fshell.sv "$KR"/ot_hfd_coll_q3_body_core__wrap.sv \
    "$KR"/ot_hfd_coll_q3_body_core.sv $(ls "$SR"/*.v | grep -v _bb.v) \
    "$O/gen/ot_hfd_coll_q3_body_ctl.sv" "$O/gen/ot_hfd_coll_q3_body_core__split.sv" "$RT/ot_hfd_coll_q3_qcol4.sv" \
    "$O/gen/ctl__fs.sv" "$O/gen/qcol4__fs.sv" > "$O/build_m$M.log" 2>&1 || { tail -20 "$O/build_m$M.log"; exit 2; }
  "$O/obj_m$M/sim" > "$O/sim_m$M.log" 2>&1; echo "MUT $M: $(grep LOCKSTEP "$O/sim_m$M.log")"
done
sha256sum "$KR"/*.sv "$RT"/*.sv "$O"/gen/*.sv > "$O/sources.sha256"
