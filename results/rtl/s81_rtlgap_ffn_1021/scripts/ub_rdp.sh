#!/bin/bash
# RG-FFN: the existing transport cut bench (codex/s81-rdpair-cut-1019 tools/s81_dv/layer_prog/rdpair: tb_rd_pair.sv, run.sh,
# mutants 0..11) against ot_s81sl_xrt (transport built in) + ot_s81sl_rstopt; tb copy with module names substituted.
set -u; S=$(pwd); O=$S/ub_rdp_$1; mkdir -p $O; cd $S/src; [ -d physical ] || tar xf $S/rdp/extra.tar
mkdir -p RDP; cp $S/rdp/tb_rd_pair.sv RDP/
V=~/.local/opentallas-tools/verilator-5.050/bin/verilator; $V --version > $O/verilator.version
sha256sum $(cat $S/rdp/sources.f) > $O/sources.sha256
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_rd_pair -Mdir $O/obj -f $S/rdp/sources.f --build-jobs 8 \
  -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > $O/build.log 2>&1 || { echo BUILD_FAILED; grep -m8 "%Error" $O/build.log; exit 3; }
ok=1
for mut in 0 1 2 3 4 5 6 7 8 9 10 11; do
  $O/obj/Vtb_rd_pair +MUT=$mut > $O/mut_${mut}.log 2>&1
  echo "mut $mut: $(grep -E '^(PASS|FAIL)' $O/mut_${mut}.log) $(grep -E '^RDPAIR' $O/mut_${mut}.log | head -3 | tr '\n' ' ')"
  if [ $mut = 0 ]; then grep -q '^PASS$' $O/mut_0.log || ok=0; else grep -q '^FAIL$' $O/mut_${mut}.log || ok=0; fi
done
[ $ok = 1 ] && echo "RDP_BENCH_OK" || echo "RDP_BENCH_BAD"
