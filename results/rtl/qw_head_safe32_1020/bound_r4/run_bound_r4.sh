#!/bin/bash
# QW-ORPHANS2 SEGCAL bound_r4: depth-optimised generic (ABC gate mapping) before the fanout-bounding pass.
set -eu
D=/srv/opentallas-scratch/claude/qw-orphans2-segcal; O=$D/r4
printf 'read_json /o/bit_generic.json\nhierarchy -top ot_qfd_tt_ctlm_static_hr_safe32\nsetattr -set keep 1 w:u_head.fixed_issue w:u_head.fixed_end w:u_head.fixed_pc w:u_head.fixed_unit w:head_fault w:relocation_sticky\nstat\nabc -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX\nopt_clean\nstat\nwrite_json /o/bit_generic_abc.json\n' > $O/abc.ys
docker run --rm -v $O:/o openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -s /o/abc.ys > $O/abc.log 2>&1
sha256sum $O/bit_generic.json $O/bit_generic_abc.json > $O/input.sha256
python3 $D/bound_head_netlist.py $O/bit_generic_abc.json --top ot_qfd_tt_ctlm_static_hr_safe32 --name ot_qfd_tt_ctlm_static_hr_safe32_native32 --out $O/native32.v --helpers $O/native32_helpers.sv --record $O/record.json --load-cap 16 --transparent-inverters --retain-all-comb --shared-helpers --fuse-ao > $O/generation.log 2>&1 || { echo GEN_FAIL; tail -20 $O/generation.log; exit 1; }
python3 $D/depth_max.py $O/native32.v
