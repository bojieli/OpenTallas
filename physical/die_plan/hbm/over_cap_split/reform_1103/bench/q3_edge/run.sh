#!/usr/bin/env bash
# DIE-HBM-61/SPLIT q3_edge lock-step: uncut kit core ot_hfd_coll_q3_edge_core (kit face shell) vs the split composition
# ot_hfd_coll_q3_edge_core__split (3 x LINK__fs + ARG__fs).  Fleet host only (verilator 5, memory-capped scope).
#   run.sh KITRTL SRAMDIR OUT [MUTS]     MUT 0 must PASS; MUT 1/2/3 must FAIL.  SRAMDIR = SRAM model + _bb view.
#   XDEFS (env, default empty): extra defines for both sides, e.g. XDEFS=OT_COLL_LINK_RXPRE with an RXPRE kit rtl/ (HBM-GAPS-4 11-05).
#   RXSTIM=1 (env): the q3_edge_rxpre type-2 periods (one loop-back bit corrupted on 1 in 3 edges, good/bad CRC alternate).
set -u
XD=""; for d in ${XDEFS:-}; do XD="$XD -D$d"; done
XF=""; for d in ${XDEFS:-}; do XF="$XF -D $d"; done
KR=$1; SR=$2; O=$3; MUTS=${4:-"0 1 2 3"}
H=$(cd "$(dirname "$0")" && pwd); R=$H/../..; RT=$H/../../../../../../../rtl/hbm_accel/cores_split/reform_1103/ot_hfd_coll_q3_edge_core
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}; mkdir -p "$O/gen"
MEM=$(ls "$KR"/*.sv | grep -v -e __fshell -e __wrap -e q3_edge_core.sv -e face_reg)   # member RTL (link_e_pr, argmax, SRAM leaf)
for S in link arg; do
  python3 "$R/facewrap.py" --top ot_hfd_coll_q3_edge_$S --out "$O/gen/ot_hfd_coll_q3_edge_${S}__fs.sv" --clk-re '^clk$' --rst-re '^rst_n$' \
    -D SYNTHESIS -D OT_COLL_ISSUER256_NATIVE32 $XF "$RT/ot_hfd_coll_q3_edge_$S.sv" $MEM "$SR"/*_bb.v > "$O/${S}_ports.json" || exit 1
done
RXSTIM=${RXSTIM:-0} python3 - "$KR/ot_hfd_coll_q3_edge_core__fshell.sv" "$H/spec_base.json" "$O/spec.json" <<'PY'
import json, re, sys
s = open(sys.argv[1]).read(); s = s[s.index('module '):].split(');')[0]
P = {n: [d, int(h) + 1 if h else 1] for d, h, n in re.findall(r'^\s*(input|output) wire (?:\[(\d+):\d+\] )?(\w+),?$', s, re.M)}
b = json.load(open(sys.argv[2])); b['ports'] = P
dens = b.pop('valid_dens', 8)
import os
if os.environ.get('RXSTIM') == '1':
    for k in range(3):
        b['stim'][f'link{k}_rx_pin_flit'] = (f"((cyc / 1000) % 4 == 3) ? {{20{{$urandom()}}}} : (((cyc / 1000) % 4 == 2) && "
            f"(($urandom() % 3) == 0)) ? (r_link{k}_tx_pin_flit ^ (612'(1) << ($urandom() % 612))) : r_link{k}_tx_pin_flit")
    b['_note'] += '; RXSTIM: type-2 periods corrupt one loop-back bit on 1 in 3 edges'
for n, (d, w) in P.items():   # 1-bit control inputs: sparse pulses (density 1/dens)
    if d == 'input' and w == 1 and n not in b['clocks'] + b['resets'] and n not in b.get('stim', {}):
        b.setdefault('stim', {})[n] = f'($urandom() % {dens}) == 0'
json.dump(b, open(sys.argv[3], 'w'), indent=1)
PY
python3 "$R/lockstep_gen.py" "$O/spec.json" "$O/tb.sv"
for M in $MUTS; do
  sed "s/ot_hfd_coll_q3_edge_core__split u_dut/ot_hfd_coll_q3_edge_core__split #(.MUT($M)) u_dut/" "$O/tb.sv" > "$O/tb_m$M.sv"
  rm -rf "$O/obj_m$M"
  systemd-run --user --scope -q -p MemoryMax=${MEMG:-16}G $V --binary -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
    -DSYNTHESIS -DOT_COLL_ISSUER256_NATIVE32 $XD --top-module tb -Mdir "$O/obj_m$M" -o sim "$O/tb_m$M.sv" \
    "$KR"/*.sv $(ls "$SR"/*.v | grep -v _bb.v) "$RT"/*.sv "$O"/gen/*__fs.sv > "$O/build_m$M.log" 2>&1 || { tail -20 "$O/build_m$M.log"; exit 2; }
  "$O/obj_m$M/sim" > "$O/sim_m$M.log" 2>&1; echo "MUT $M: $(grep LOCKSTEP "$O/sim_m$M.log")"
done
sha256sum "$KR"/*.sv "$RT"/*.sv "$O"/gen/*.sv > "$O/sources.sha256"
