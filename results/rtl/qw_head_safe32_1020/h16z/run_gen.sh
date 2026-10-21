#!/bin/bash
# QW-H16Z 10-21: h16z head netlist (H16X=3) = prepare_generic (h16v sources) -> synth -noabc bit_generic -> ABC (variant) ->
# bound_head_netlist (load-cap 16, as bound_r4) -> param header + single clock region (as h16u make_1r) -> depth report.
# usage (repo root): bash results/rtl/qw_head_safe32_1020/h16z/run_gen.sh OUT_DIR [ABC args...]
set -eu
O=$1; shift; ABCARGS="$*"; mkdir -p $O
H=results/rtl/qw_head_safe32_1020; IMG=openroad/orfs:asap7lock; Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
docker run --rm -v "$PWD:/src:ro" -v "$O:/out" $IMG $Y -s /src/$H/h16z/prepare_generic.ys > $O/prepare.log 2>&1 || { echo PREP_FAIL; grep -i error $O/prepare.log | tail; exit 1; }
printf 'read_json /out/generic.json\nhierarchy -check -top ot_qfd_tt_ctlm_static_hr_safe32\nsynth -top ot_qfd_tt_ctlm_static_hr_safe32 -flatten -noabc -nofsm -noshare\ndffunmap\nwrite_json /out/bit_generic.json\n' > $O/bit_generic.ys
docker run --rm -v "$O:/out" $IMG $Y -s /out/bit_generic.ys > $O/bit_generic.log 2>&1 || { echo BIT_FAIL; tail $O/bit_generic.log; exit 1; }
printf "read_json /out/bit_generic.json\nhierarchy -top ot_qfd_tt_ctlm_static_hr_safe32\nsetattr -set keep 1 w:u_head.fixed_issue w:u_head.fixed_end w:u_head.fixed_pc w:u_head.fixed_unit w:head_fault w:relocation_sticky\nstat\nabc -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX $ABCARGS\nopt_clean\nstat\nwrite_json /out/bit_generic_abc.json\n" > $O/abc.ys
docker run --rm -v "$O:/out" $IMG $Y -s /out/abc.ys > $O/abc.log 2>&1 || { echo ABC_FAIL; tail $O/abc.log; exit 1; }
sha256sum $O/generic.json $O/bit_generic.json $O/bit_generic_abc.json > $O/input.sha256
python3 $H/bound_head_netlist.py $O/bit_generic_abc.json --top ot_qfd_tt_ctlm_static_hr_safe32 --name ot_qfd_tt_ctlm_static_hr_safe32_native32 --out $O/native32.v --helpers $O/native32_helpers.sv --record $O/record.json --load-cap 16 --transparent-inverters --retain-all-comb --shared-helpers --fuse-ao > $O/generation.log 2>&1 || { echo GEN_FAIL; tail -20 $O/generation.log; exit 1; }
python3 $H/h16v/make_1r_param.py $O/native32.v $O/native32_1r_param.v
python3 $H/bound_r4/depth_max.py $O/native32.v > $O/depth_max.txt 2>&1 || true
python3 $H/h16v/jdepth2.py $O/bit_generic_abc.json ot_qfd_tt_ctlm_static_hr_safe32 16 40 > $O/jdepth.txt
echo "cells: $(grep -A30 'Printing statistics' $O/abc.log | grep -m1 -i 'cells')"; head -30 $O/jdepth.txt; tail -3 $O/depth_max.txt
