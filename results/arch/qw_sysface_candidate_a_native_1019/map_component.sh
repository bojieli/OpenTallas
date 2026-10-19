#!/bin/bash
set -euo pipefail
P=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
mkdir -p libs mapped_original mapped_candidate receipts
sha256sum "$P"/*RVT_TT* "$P"/*RVT_FF* > receipts/libraries.sha256
sha256sum /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad > receipts/tools.sha256
yosys -V > receipts/yosys.version
/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -version > receipts/openroad.version
python3 canonical/merge_libs.py libs/comb.lib "$P"/asap7sc7p5t_AO_RVT_TT_*.lib.gz "$P"/asap7sc7p5t_INVBUF_RVT_TT_*.lib.gz "$P"/asap7sc7p5t_OA_RVT_TT_*.lib.gz "$P"/asap7sc7p5t_SIMPLE_RVT_TT_*.lib.gz
cp "$P/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" libs/seq.lib
python3 canonical/merge_libs.py libs/all.lib libs/comb.lib libs/seq.lib
sha256sum libs/* > receipts/merged_libraries.sha256
for WHICH in original candidate; do
  TOP=qfd_host_native_context_rx
  SRC=original.sv
  if [ "$WHICH" = candidate ]; then TOP=qfd_host_native_context_rx_candidate_a; SRC=candidate_a.sv; fi
  export OT_KEEP_PIN_REGS=1 DESIGN_NAME="$TOP"
  OUT="mapped_$WHICH"
  /usr/bin/time -v -o "$OUT/time.txt" yosys -Q -T -p "read_liberty -lib libs/all.lib; read_verilog -sv -DSYNTHESIS $SRC; hierarchy -check -top $TOP; tcl canonical/ot_keep_regs.tcl; synth -top $TOP -flatten -noabc; dfflibmap -liberty libs/seq.lib; abc -liberty libs/comb.lib; clean; stat -liberty libs/all.lib; write_verilog -noattr $OUT/netlist.v; write_json $OUT/netlist.json" > "$OUT/yosys.log" 2>&1
  du -sb . > "$OUT/disk.txt"
done
echo MAPPING_COMPLETE
