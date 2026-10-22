#!/bin/bash
# KV-PEER12 10-20: native32 primitive copy of the MU 1 PEER synthesis (synth_mu.sh) with the PEER/ORDER source-copy
# generator (primitive32/host_order_native32.py, unchanged), Yosys re-synthesis (-noabc, pinned orfs:asap7lock), mapped
# census (SS libs + macro, max 32 loads) and the primitive/pin correspondence certificate.  usage (repo root):
#   SYN=synth_mu2 bash rtl/test/host_peer_main_fixture_1020/mu_sram/native_mu.sh
set -eu
R=$PWD;P=rtl/test/host_peer_main_fixture_1020/primitive32;SYN=${SYN:-synth_mu};O=${O:-native_mu};mkdir -p $O
N=$SYN/results/asap7/peer_mu_census/base/1_2_yosys.v;SHA=$(sha256sum $N|cut -d' ' -f1);T=qkd_hr_core_peer_mu_n32
cp $N $O/original.v
python3 $P/host_order_native32.py --netlist $O/original.v --parser $P/textbook_lint.py --sha256 $SHA --top $T --out $O/$T.sv > $O/generate.log 2>&1
cp physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1_p192_mir/ot_sram_1r1w_32x546_m1_p192_mir_bb.v $O/macro_bb.v
cat > $O/resynth.sh <<'SH'
set -euo pipefail
cd /work; mkdir -p libs
for f in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_*.lib.gz; do gzip -dc "$f" > "libs/$(basename "${f%.gz}")"; done
cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib libs/
{ for p in libs/*.lib; do echo "read_liberty -lib $p"; done
  echo "read_verilog -lib macro_bb.v"; echo "read_verilog $T.sv"; echo "hierarchy -check -top $T"
  echo "synth -top $T -noabc"; echo "write_verilog -noattr resynth.v"; } > resynth.ys
yosys -s resynth.ys > resynth.log 2>&1
SH
docker run --rm -e T=$T -v "$R/$O:/work" openroad/orfs:asap7lock bash /work/resynth.sh
mkdir -p real5
docker run --rm -v "$R/real5:/libs" openroad/orfs:latest bash -lc 'cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_SS_nldm* /libs/'
libs=();for f in "$R"/real5/* "$R"/physical/asap7_memory_macros/*p192_mir/*_ss.lib;do libs+=(--liberty "$f");done
python3 $P/native_census.py --netlist $O/resynth.v --top $T "${libs[@]}" --out $O/native_resynth.json > $O/census.log 2>&1 || true
python3 $P/host_order_native32_certificate.py --original $O/original.v --mapped $O/resynth.v --parser $P/textbook_lint.py --record $O/$T.json --out $O/correspondence_resynth.json > $O/certificate.log 2>&1 || true
python3 - $O <<'PY'
import json,sys
o=sys.argv[1]
g=json.load(open(o+'/qkd_hr_core_peer_mu_n32.json'))
print('GEN original_cells',g.get('original_cells'),'generated_cells',g.get('generated_cells'),'max_terminal_loads',g.get('max_terminal_loads'))
try:
    c=json.load(open(o+'/native_resynth.json')); print('CENSUS', {k:c[k] for k in c if not isinstance(c[k],(list,dict))})
except Exception as e: print('CENSUS ERR',e)
try:
    c=json.load(open(o+'/correspondence_resynth.json')); print('CERT', {k:c[k] for k in c if not isinstance(c[k],(list,dict))})
except Exception as e: print('CERT ERR',e)
PY
sha256sum $O/$T.sv
