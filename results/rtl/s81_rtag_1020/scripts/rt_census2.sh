#!/usr/bin/env bash
# S81-RTAG pre-gate native census of dsfd_bf_front_roots (kit s81bf_front_five_roots_nlock_h03 sources, branch
# claude/s81-rtag-1020): RTL -> ASAP7 RVT TT (ot_keep_regs hook, synth -flatten, dfflibmap, abc) -> mapped.v ->
# tools/ref_tile/native_census.py (origin/main).  usage (cwd = csrc): rt_census.sh OUT "DEFINES"
set -euo pipefail
ROOT=$PWD; OUT=$(mkdir -p "$1" && cd "$1" && pwd); DEFS=${2:-}
TOP=${TOP:-dsfd_bf_front_roots}
SRCS=${SRCS_OVR:-$(python3 -c "import json;print(' '.join(s for s in json.load(open('spec.json'))['sources'] if not s.endswith('_bb.v')))")}
BB=$(python3 -c "import json;print(' '.join(s for s in json.load(open('spec.json'))['sources'] if s.endswith('_bb.v')))")
SRCS="$SRCS rtl/v41rom/ot_s81_so_label_q.sv rtl/lib/ot_rst_relay.sv"
{ for b in $BB; do echo "read_verilog -lib /src/$b"; done
  echo "read_verilog -sv -DSYNTHESIS $DEFS $(for s in $SRCS; do printf '/src/%s ' $s; done)"
  for k in SIMPLE AO OA INVBUF SEQ; do echo "read_liberty -lib /tmp/lib/$k.lib"; done
  cat <<YS
hierarchy -check -top $TOP
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top $TOP -flatten
dfflibmap -liberty /tmp/lib/SEQ.lib
abc -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
opt_clean
tee -o /out/stat.txt stat
write_verilog -noattr /out/mapped.v
YS
} > "$OUT/map.ys"
sha256sum $SRCS $BB > "$OUT/source_identity.sha256"
docker run --rm -v "$ROOT:/src:ro" -v "$OUT:/out" openroad/orfs:latest bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 N=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
 mkdir -p /tmp/lib /out/lib
 for k in SIMPLE AO OA; do zcat "$N/asap7sc7p5t_${k}_RVT_TT_nldm_211120.lib.gz" > /tmp/lib/$k.lib; done
 zcat "$N/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz" > /tmp/lib/INVBUF.lib
 cp "$N/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /tmp/lib/SEQ.lib
 cp /tmp/lib/*.lib /out/lib/
 cp /src/physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8_tt.lib /out/lib/ROM4096.lib
 cp /src/physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8_tt.lib /out/lib/ROM8192.lib
 yosys -V > /out/tool_identity.txt
 yosys -l /out/synth.log -s /out/map.ys > /dev/null
' > "$OUT/synth.stdout" 2>&1 || { tail -20 "$OUT/synth.stdout"; tail -20 "$OUT/synth.log"; echo RT_CENSUS SYNTH_FAIL; exit 1; }
args=(); for f in "$OUT"/lib/*.lib; do args+=(--liberty "$f"); done
python3 tools/ref_tile/native_census.py --netlist "$OUT/mapped.v" --top $TOP --out "$OUT/census.json" "${args[@]}" > "$OUT/census.log" 2>&1 || true
echo "RT_CENSUS $(basename $OUT) $(tail -3 $OUT/census.log | tr '\n' ' ')"
grep -E 'Number of cells|DFF|Chip area' "$OUT/stat.txt" | tail -6
