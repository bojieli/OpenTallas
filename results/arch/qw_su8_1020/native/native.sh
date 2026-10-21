#!/bin/bash
# QW-SU8 pre-gate native census (mapped ASAP7 RVT, Codex recipe su8_reset0720/native_rst3.*), run in openroad/orfs:asap7lock
set -uo pipefail
cd /w; mkdir -p nat; cd nat
cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib seq.lib
cp ../cells.lib .; ln -sfn ../rtl rtl
yosys -Q -s ../results/arch/qw_su8_1020/native/native.ys > native_map.log 2>&1 || { tail -20 native_map.log; exit 1; }
python3 ../tools/ref_tile/native_census.py --netlist su8_mapped.v --top qfd_dv_s5_su8_rst3 --liberty cells.lib --out native.json > native.stdout 2>&1; NR=$?
python3 ../tools/textbook_lint.py check --netlist su8_mapped.v --top qfd_dv_s5_su8_rst3 --out textbook.json > textbook.stdout 2>&1; TR=$?
cat native.stdout textbook.stdout; grep -E 'Chip area|cells$' mapped_stat.txt | tail -3
echo "NATIVE_RC=$NR TEXTBOOK_RC=$TR"; exit $NR
