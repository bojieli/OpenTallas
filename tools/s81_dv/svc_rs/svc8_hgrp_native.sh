#!/usr/bin/env bash
# S81-SVC8 (10-20): mapped native census of ot_s81svc8_hgrp_s81 BEFORE any layout gate.
#   1 map    : RTL -> ASAP7 RVT TT (ot_keep_regs, synth -flatten -noshare, dfflibmap, abc) -> map/{mapped,flat}.json
#   2 bound  : svc7_bound_graph.py (SCC-aware driver replication, same input functions/clock/reset per copy,
#              --limit 32) -> bound/bounded.v + ledger
#   3 retain : re-synthesise bounded.v through the same mandatory flow -> retained/mapped.v, native_census.py
# usage (repo root): svc8_hgrp_native.sh OUT [STAGES]   STAGES default "map bound retain"
set -euo pipefail
ROOT=$PWD; OUT=$(mkdir -p "${1:?out}" && cd "$1" && pwd); STAGES=${2:-"map bound retain"}
TOP=ot_s81svc8_hgrp_s81
V=rtl/hdc/v41x; H=rtl/hdc
RTL="/src/$V/ot_s81svc8_hgrp_s81.sv /src/$V/ot_s81svc8_ring.sv /src/$V/ot_hdc_v41x_attn_tile_s.sv /src/$V/ot_hdc_v41x_attn_tile_lat.sv /src/$V/ot_hdc_v41x_attn_tile.sv /src/$V/ot_hdc_v41x_kreg.sv /src/$H/ot_hdc_fastfp.sv /src/$H/ot_hdc_fp32_add_lat.sv /src/$H/ot_hdc_prefix.sv /src/$H/ot_hdc_fp32_f12.sv /src/$V/ot_dsrom_su_add6.sv"
BB="/src/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_bb.v /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1_bb.v"
synth() {  # $1 out dir, $2 read line, $3 top
  local O=$1; mkdir -p "$O"
  { for b in $BB; do echo "read_verilog -lib $b"; done
    echo "$2"
    for k in SIMPLE AO OA INVBUF SEQ; do echo "read_liberty -lib /tmp/lib/$k.lib"; done
    cat <<YS
hierarchy -check -top $3
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top $3 -flatten -noshare
dfflibmap -liberty /tmp/lib/SEQ.lib
abc -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
opt_clean
tee -o /out/stat.txt stat
write_verilog -noattr /out/mapped.v
write_json /out/mapped.json
setattr -mod -unset keep_hierarchy
flatten
write_verilog -noattr /out/flat.v
write_json /out/flat.json
YS
  } > "$O/map.ys"
  docker run --rm -v "$ROOT:/src:ro" -v "$OUT:/graph:ro" -v "$O:/out" openroad/orfs:latest bash -lc '
   source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
   N=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
   mkdir -p /tmp/lib /out/lib
   for k in SIMPLE AO OA; do zcat "$N/asap7sc7p5t_${k}_RVT_TT_nldm_211120.lib.gz" > /tmp/lib/$k.lib; done
   zcat "$N/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz" > /tmp/lib/INVBUF.lib
   cp "$N/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /tmp/lib/SEQ.lib
   cp /tmp/lib/*.lib /out/lib/
   cp /src/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_tt.lib /out/lib/MACRO128.lib
   cp /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1_tt.lib /out/lib/MACRO64.lib
   yosys -V > /out/tool_identity.txt
   yosys -l /out/synth.log -s /out/map.ys > /dev/null
  ' > "$O/synth.stdout" 2>&1
  local args=(); for f in "$O"/lib/*.lib; do args+=(--liberty "$f"); done
  python3 tools/ref_tile/native_census.py --netlist "$O/mapped.v" --top "$3" --out "$O/census.json" "${args[@]}" > "$O/census.log" 2>&1 || true
  echo "SVC8_NATIVE stage=$(basename $O) $(tail -2 $O/census.log | tr '\n' ' ')"; grep -A40 'Number of cells' "$O/stat.txt" | grep -E 'cells|DFF|sram|Chip area' | head -12
}
sha256sum $(for f in $RTL $BB; do echo ${f#/src/}; done) tools/s81_dv/svc_rs/svc7_bound_graph.py physical/common_flow/ot_keep_regs.tcl > "$OUT/source_identity.sha256"
for s in $STAGES; do case $s in
  map) synth "$OUT/map" "read_verilog -sv -DSYNTHESIS $RTL" $TOP ;;
  bound) mkdir -p "$OUT/bound"
     /usr/bin/time -v python3 tools/s81_dv/svc_rs/svc7_bound_graph.py "$OUT/map/flat.json" --top $TOP --name ${TOP}_bounded \
       --out "$OUT/bound/bounded.v" --limit 32 --incremental > "$OUT/bound/replicate.log" 2>&1 || { tail -20 "$OUT/bound/replicate.log"; echo "SVC8_NATIVE bound FAIL"; exit 1; }
     tail -3 "$OUT/bound/replicate.log" ;;
  retain) synth "$OUT/retained" "read_verilog /graph/bound/bounded.v" ${TOP}_bounded ;;
esac; done
