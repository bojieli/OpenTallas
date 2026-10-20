#!/bin/bash
set -euo pipefail
out=${1:?output};mkdir -p "$out"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
P=rtl/hbm_accel/generic/collective/p2p
"$V" --version | tee "$out/verilator_version.txt"
sha256sum "$P/ot_hgi_coll_gq.sv" "$P/tb_gq_req_chunk_eq.sv" > "$out/sources.sha256"
for seed in 1 2 3 4;do
 tag=seed$seed
 "$V" --binary --timing -j 2 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_gq_req_chunk_eq -GSEED=$seed --Mdir "$out/obj_$tag" -o tb "$P/tb_gq_req_chunk_eq.sv" "$P/ot_hgi_coll_gq.sv" > "$out/build_$tag.log" 2>&1
 "$out/obj_$tag/tb" > "$out/$tag.log" 2>&1
 grep REQ_CHUNK_EQ_PASS "$out/$tag.log"
done
"$V" --binary --timing -j 2 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_gq_req_chunk_eq -GMUT=1 --Mdir "$out/obj_mut" -o tb "$P/tb_gq_req_chunk_eq.sv" "$P/ot_hgi_coll_gq.sv" > "$out/build_mut.log" 2>&1
if "$out/obj_mut/tb" > "$out/mut.log" 2>&1;then echo REQ_CHUNK_MUTANT_ESCAPED;exit 1;fi
grep REQ_CHUNK_EQ_FAIL "$out/mut.log"
echo REQ_CHUNK_PROOFS_PASS seeds4_checks40000_mutants1
