#!/bin/bash
set -eu
cd "$(dirname "$0")/../../.."
mkdir -p native
libroot=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
# Separate real RVT TT Liberty groups as used by ASAP7 ORFS; no fake FF libraries are used here.
docker run --rm -v "$PWD:/work" -w /work openroad/orfs:latest bash -lc '
set -eu
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
for x in AO INVBUF OA SIMPLE;do zcat "$L"/asap7sc7p5t_${x}_RVT_TT*.lib.gz > native/$x.lib;done
cp "$L"/asap7sc7p5t_SEQ_RVT_TT*.lib native/SEQ.lib
cat > native/map.ys <<YS
read_verilog -sv rtl/qwen_split/qfd_sys_face_record_port_n32.sv
hierarchy -check -top qfd_sys_face_record_port_n32
synth -top qfd_sys_face_record_port_n32 -flatten
dfflibmap -liberty native/SEQ.lib
abc -liberty native/AO.lib -liberty native/INVBUF.lib -liberty native/OA.lib -liberty native/SIMPLE.lib -liberty native/SEQ.lib -D 770
setundef -zero
splitnets -ports
opt_clean -purge
write_verilog -noattr native/mapped.v
stat -liberty native/SEQ.lib
YS
yosys -Q -s native/map.ys > native/map.log 2>&1
python3 tools/ref_tile/native_census.py --netlist native/mapped.v --top qfd_sys_face_record_port_n32 --liberty native/AO.lib --liberty native/INVBUF.lib --liberty native/OA.lib --liberty native/SIMPLE.lib --liberty native/SEQ.lib --out native/census.json
'
