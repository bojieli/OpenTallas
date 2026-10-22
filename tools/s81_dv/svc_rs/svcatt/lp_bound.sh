#!/bin/bash
# lp_bound.sh OUTNAME "DEFINES" "CHPARAMS"  : LP whole synth -> census -> bound graph (clone-cyclic all) -> retention census
set -e
R=/srv/opentallas-scratch/claude/svcatt-1021; O=$R/$1; T=dsdv_svc_attw_n1_f_lp
LIB=/srv/opentallas-scratch/claude/elemsvc-g4-1021/out_norst/map/lib
HG=/srv/opentallas-scratch/claude/elemsvc-g4-1021/src_norst/tools/s81_dv/svc_rs/attn1
bash $R/wc_native_v2.sh $1 $T "$2" "$3"
python3 $R/svcatt_bound_graph.py $O/flat.json --top $T --name ${T}_bounded --out $O/bounded.v --limit 32 --collect-frontier --clone-cyclic all --keep-names --clock-port ck_c --clock-port ck_t0 > $O/graph_all.log 2>&1 || true
cat $O/graph_all.log
python3 $R/frontier_src.py $O/flat.json $O/bounded.v.frontier.json $T 2>/dev/null | head -40 || true
test -s $O/bounded.v || { echo NO_BOUNDED_NETLIST; exit 3; }
cat > $O/ret.ys <<YS
read_liberty -lib /tmp/lib/SIMPLE.lib
read_liberty -lib /tmp/lib/AO.lib
read_liberty -lib /tmp/lib/OA.lib
read_liberty -lib /tmp/lib/INVBUF.lib
read_liberty -lib /tmp/lib/SEQ.lib
read_verilog -lib /src/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_bb.v
read_verilog -lib /src/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_bb.v
read_verilog -lib /hg/ot_s81svc8_hgrp_s81_bounded_bb.v
read_verilog /out/bounded.v
hierarchy -check -top ${T}_bounded
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top ${T}_bounded -flatten -noshare
opt_clean
tee -o /out/ret_stat.txt stat -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
write_verilog -noattr /out/retained.v
YS
docker run --rm -v "$R/src:/src:ro" -v "$HG:/hg:ro" -v "$O:/out" -v "$LIB:/tmp/lib:ro" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -l /out/ret.log -s /out/ret.ys' > $O/ret.build.log 2>&1 || { echo RET_SYNTH_FAIL; tail -5 $O/ret.log; exit 4; }
args=(); for f in $LIB/*.lib; do args+=(--liberty $f); done
python3 $R/tools/ref_tile/native_census.py --netlist $O/retained.v --top ${T}_bounded --out $O/ret_census.json "${args[@]}" > $O/ret_census.log 2>&1 || true
cat $O/ret_census.log
python3 -c "import json;r=json.load(open('$O/ret_census.json'));print('RETAINED',r['status'],'max',r['max_dynamic_loads'],'viol',r['violations'] if isinstance(r['violations'],int) else len(r['violations']),'roles',len(r['role_errors']))"
python3 $R/attrib.py $O/retained.v $O/ret_census.json $O/ret_attrib.json 2>/dev/null | head -30 || true
