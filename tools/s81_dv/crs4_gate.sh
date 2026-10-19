#!/bin/bash
# crs4_gate.sh <mode> <outdir> (cwd = repo root): one variant of the dsfd_cfifo_crs4 bench (tools/s81_dv/crs4_bench.py,
# tb rtl/dsrom_sys/s81_dv/land/test/tb_cfifo_crs4.sv, iverilog) for the hardened-view kit (S81-DIE7/CRS4 10-18).
#   pass       the RTL: every lane on its own forwarded clock, 4 geometries x 5 skew points cycle-exact vs dsfd_cfifo_crs
#              at the compile-time latency E + const, slip on lane 0 / 3 raises fault  -> 'CRS4_BENCH PASS base ...'
#   mut_nbr    lanes 0 / 3 captured on the neighbour lane's clock (the dsfd_cfifo_crs gap)  -> 'CRS4_BENCH FAIL ...'
#   mut_sel    landing read slot one late                                                 -> 'CRS4_BENCH FAIL ...'
#   mut_naive  bounded-skew retime register instead of the ring                           -> 'CRS4_BENCH FAIL ...'
# Exit status = the variant's own verdict (0 PASS, 1 FAIL); the closure-loop bench expect decides what is wanted.
set -u
M=$1; O=$2; mkdir -p "$O"
case $M in pass) V=base;; mut_nbr|mut_sel|mut_naive) V=$M;; *) echo "crs4_gate.sh: unknown mode $M"; exit 2;; esac
python3 tools/s81_dv/crs4_bench.py --variant $V --out "$O/crs4_$V.json"
