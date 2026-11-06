#!/usr/bin/env bash
# HBM-GAPS-3/Q3E 11-05: lock-step bench for the opt-in RXPRE form of ot_hfd_coll_q3_edge_core (define OT_COLL_LINK_RXPRE).
#   REF = an existing q3_edge kit rtl/ (native codec, RXPRE absent = 0), unchanged.
#   DUT = the same kit rtl/ with this checkout's ot_hgi_coll_edge_pr.sv + ot_hgi_coll_static_pinreg_ctl.sv +
#         ot_hgi_coll_static_seq_ctl.sv, every module renamed <name>__rx, compiled with +define+OT_COLL_LINK_RXPRE.
#   Stimulus = ../q3_edge/spec_base.json (epoch/seq directed periods + TX->RX loop-back, every 4th period random => CRC bad).
#   Every output bit compared every edge (0 added cycles).  MUT 0 must PASS; mutants (seq_ctl C3MUT_*) must FAIL:
#     1 = C3MUT_RX_BIT (CRC over a flipped bit), 2 = C3MUT_RX_STALE (compare against rf = wrong edge), 3 = C3MUT_RX_NOREG (no ne_q flop).
#   run.sh KITRTL SRAM_V OUT [MUTS]     (fleet host; verilator 5, memory-capped scope)
set -u
KR=$1; SV=$2; O=$3; MUTS=${4:-"0 1 2 3"}
H=$(cd "$(dirname "$0")" && pwd); R=$H/../..; REPO=$(cd "$H/../../../../../../.." && pwd)
P2P=$REPO/rtl/hbm_accel/generic/collective/p2p
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}; mkdir -p "$O/dut"
cp "$KR"/*.sv "$O/dut/"
cp "$P2P/ot_hgi_coll_edge_pr.sv" "$P2P/ot_hgi_coll_static_pinreg_ctl.sv" "$P2P/ot_hgi_coll_static_seq_ctl.sv" "$O/dut/"
python3 -I - "$O/dut" <<'PY'
import re, sys, pathlib
d = pathlib.Path(sys.argv[1]); fs = sorted(d.glob('*.sv'))
names = set()
for f in fs: names |= set(re.findall(r'^\s*module\s+(\w+)', f.read_text(), re.M))
pat = re.compile(r'\b(' + '|'.join(sorted(map(re.escape, names), key=len, reverse=True)) + r')\b')
for f in fs: f.write_text(pat.sub(lambda m: m.group(1) + '__rx', f.read_text()))
print('renamed', len(names), 'modules')
PY
python3 -I - "$KR/ot_hfd_coll_q3_edge_core__fshell.sv" "$H/../q3_edge/spec_base.json" "$O/spec.json" <<'PY'
import json, re, sys
s = open(sys.argv[1]).read(); s = s[s.index('module '):].split(');')[0]
P = {n: [d, int(h) + 1 if h else 1] for d, h, n in re.findall(r'^\s*(input|output) wire (?:\[(\d+):\d+\] )?(\w+),?$', s, re.M)}
b = json.load(open(sys.argv[2])); b['ports'] = P; b['ref'] = 'ot_hfd_coll_q3_edge_core'; b['dut'] = 'ot_hfd_coll_q3_edge_core__rx'
dens = b.pop('valid_dens', 8)
# period type 2: loop-back with a random single-bit corruption on 1 in 3 edges, so good and bad CRC frames alternate
# edge to edge (an RXPRE edge misalignment is only observable then; types 0/1 always good, type 3 always bad).
for k in range(3):
    b['stim'][f'link{k}_rx_pin_flit'] = (f"((cyc / 1000) % 4 == 3) ? {{20{{$urandom()}}}} : (((cyc / 1000) % 4 == 2) && "
        f"(($urandom() % 3) == 0)) ? (r_link{k}_tx_pin_flit ^ (612'(1) << ($urandom() % 612))) : r_link{k}_tx_pin_flit")
b['_note'] += '; RXPRE bench: type-2 periods corrupt one loop-back bit on 1 in 3 edges'
for n, (d, w) in P.items():
    if d == 'input' and w == 1 and n not in b['clocks'] + b['resets'] and n not in b.get('stim', {}):
        b.setdefault('stim', {})[n] = f'($urandom() % {dens}) == 0'
json.dump(b, open(sys.argv[3], 'w'), indent=1)
PY
python3 -I "$R/lockstep_gen.py" "$O/spec.json" "$O/tb.sv"
for M in $MUTS; do
  case $M in 0) MD="";; 1) MD="-DC3MUT_RX_BIT";; 2) MD="-DC3MUT_RX_STALE";; 3) MD="-DC3MUT_RX_NOREG";; esac
  rm -rf "$O/obj_m$M"
  systemd-run --user --scope -q -p MemoryMax=${MEMG:-16}G $V --binary -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
    -DSYNTHESIS -DOT_COLL_ISSUER256_NATIVE32 -DOT_COLL_LINK_RXPRE $MD --top-module tb -Mdir "$O/obj_m$M" -o sim "$O/tb.sv" \
    "$KR"/*.sv "$O"/dut/*.sv "$SV" > "$O/build_m$M.log" 2>&1 || { tail -20 "$O/build_m$M.log"; exit 2; }
  "$O/obj_m$M/sim" > "$O/sim_m$M.log" 2>&1; echo "MUT $M: $(grep LOCKSTEP "$O/sim_m$M.log")"
done
sha256sum "$KR"/*.sv "$O"/dut/*.sv "$SV" > "$O/sources.sha256"
