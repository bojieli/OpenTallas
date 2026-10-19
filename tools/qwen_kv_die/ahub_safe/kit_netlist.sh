#!/bin/bash
# kit_netlist.sh OUT (KV-AHUB 10-19, fleet only): the ORFS-readable form of the face-copy native netlist for the SAFE ahub kits.
# The native source (57a9e0f3...) carries (* keep, dont_touch *) on every cell; ORFS yosys re-emits each liberty-cell
# instance with (* module_not_derived = 32'b... *), which OpenROAD's link_design rejects (synth_odb.tcl "stoi").  This
# script changes NO cell or connection: it ties literal constants to per-load TIEHI/TIELO cells (as ORFS synth hilomap),
# buffers port-to-port assigns (insbuf, as ORFS), drops all attributes and writes the netlist the kit feeds ORFS through
# SYNTH_NETLIST_FILES (no re-synthesis, so no opt_merge can fold the kept face copies).
set -euo pipefail
O=$(realpath -m "$1"); S=$PWD; mkdir -p "$O"
docker run --rm --cpus=4 --memory=16g -v "$O:/out" -v "$S:/src:ro" openroad/orfs:asap7lock bash -lc '
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
cd /tmp; for f in $L/asap7sc7p5t_{AO,INVBUF,OA,SIMPLE}_RVT_TT_nldm_2*.lib.gz; do zcat $f > $(basename $f .gz); done
cp $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib .
/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l /out/kit_netlist.log -p "
read_liberty -lib /tmp/asap7sc7p5t_*.lib;
read_verilog -sv /src/rtl/hdc/nearhbm/ot_nhb_tiles_bb.v /src/rtl/hdc/nearhbm/ot_qkh_recip_leaf_bb.v;
read_verilog /src/rtl/hdc/nearhbm/qkd_ahub_static_dw_safe_face_native.v;
hierarchy -check -top qkd_ahub_static_dw_safe_native;
hilomap -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L;
insbuf -buf BUFx2_ASAP7_75t_R A Y;
setattr -unset keep; setattr -unset dont_touch;
check -assert;
stat;
write_verilog -noattr -noexpr -nohex -nodec /out/qkd_ahub_static_dw_safe_face_native_kit.v" ' 
grep -c -E '_ASAP7_75t_R ' "$O/qkd_ahub_static_dw_safe_face_native_kit.v"
sha256sum "$O/qkd_ahub_static_dw_safe_face_native_kit.v"
