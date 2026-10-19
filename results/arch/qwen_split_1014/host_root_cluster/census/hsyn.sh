set -e
mkdir -p lib
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
zcat $L/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz > lib/AO.lib
zcat $L/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz > lib/INVBUF.lib
zcat $L/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz > lib/OA.lib
zcat $L/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz > lib/SIMPLE.lib
(zcat $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz 2>/dev/null || cat $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib) > lib/SEQ.lib
yosys -T -l out/hsyn.log -s hsyn.ys > /dev/null 2>&1; echo rc=$?
