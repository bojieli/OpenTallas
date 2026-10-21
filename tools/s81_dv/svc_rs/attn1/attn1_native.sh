#!/usr/bin/env bash
# DRIVE-S81-ATTN1 (10-20): PRE-GATE mapped native census of the narrowed attw landed parent dsdv_svc_attw_n1_f_lp
# (u_c + landing rings + reset runs; the 4 hard head groups and the SRAMs are blackboxes, as in the kit).
#   RTL -> ASAP7 RVT TT (ot_keep_regs, synth -flatten -noshare, dfflibmap, abc) -> map/{stat.txt,flat.v}; then
#   tools/ref_tile/native_census.py on the flat netlist (SRAM tt libs + the hgrp8 role-only stub lib).
# usage (repo root, fleet): attn1_native.sh OUT [KITSPEC]   (KITSPEC default the main kit spec: sources/params/defines)
set -euo pipefail
ROOT=$PWD; export PYTHONPATH="$ROOT/tools${PYTHONPATH:+:$PYTHONPATH}"
OUT=$(mkdir -p "${1:?out}" && cd "$1" && pwd); SPEC=${2:-tools/ref_tile/specs_s81dv_svc_lp/dsdv_svc_attw_n1_main_lp.json}
TOP=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['top'])" "$SPEC")
python3 - "$SPEC" > "$OUT/read.ys" <<'PY'
import json, sys
k = json.load(open(sys.argv[1]))
defs = " ".join(f"-D{d}" for d in k["defines"])
inc = k["orfs_vars"]["VERILOG_INCLUDE_DIRS"]
for b in ["physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_bb.v",
          "physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_bb.v",
          "tools/s81_dv/svc_rs/attn1/ot_s81svc8_hgrp_s81_bounded_bb.v"]:
    print(f"read_verilog -lib /src/{b}")
srcs = [s for s in k["sources"] if not s.startswith("physical/asap7_memory_macros/")]
print(f"read_verilog -defer -sv -DSYNTHESIS {defs} -I{inc} " + " ".join(f"/src/{s}" for s in srcs))
print(f"hierarchy -check -top {k['top']} " + " ".join(f"-chparam {n} {v}" for n, v in k["params"].items()))
PY
{ cat "$OUT/read.ys"
  for l in SIMPLE AO OA INVBUF SEQ; do echo "read_liberty -lib /tmp/lib/$l.lib"; done
  cat <<YS
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top $TOP -flatten -noshare
dfflibmap -liberty /tmp/lib/SEQ.lib
abc -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
opt_clean
tee -o /out/stat.txt stat -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
setattr -mod -unset keep_hierarchy
flatten
opt_clean
tee -o /out/stat_flat.txt stat -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
write_verilog -noattr /out/flat.v
YS
} > "$OUT/map.ys"
mkdir -p "$OUT/map"
sha256sum "$SPEC" $(python3 -c "import json,sys;print(' '.join(json.load(open(sys.argv[1]))['sources']))" "$SPEC") \
  tools/s81_dv/svc_rs/attn1/* physical/common_flow/ot_keep_regs.tcl > "$OUT/source_identity.sha256"
cp "$OUT/map.ys" "$OUT/map/map.ys"
docker run --rm -v "$ROOT:/src:ro" -v "$OUT/map:/out" openroad/orfs:latest bash -lc '
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
  N=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
  mkdir -p /tmp/lib /out/lib
  for k in SIMPLE AO OA; do zcat "$N/asap7sc7p5t_${k}_RVT_TT_nldm_211120.lib.gz" > /tmp/lib/$k.lib; done
  zcat "$N/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz" > /tmp/lib/INVBUF.lib
  cp "$N/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /tmp/lib/SEQ.lib
  cp /tmp/lib/*.lib /out/lib/
  cp /src/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_tt.lib /out/lib/M128.lib
  cp /src/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_tt.lib /out/lib/M256.lib
  cp /src/tools/s81_dv/svc_rs/attn1/hgrp8_role_stub.lib /out/lib/HGRP8_STUB.lib
  yosys -V > /out/tool_identity.txt
  /usr/bin/time -v yosys -l /out/synth.log -s /out/map.ys > /dev/null 2> /out/time.txt
' > "$OUT/map/docker.stdout" 2>&1 || { tail -30 "$OUT/map/synth.log" 2>/dev/null; tail -5 "$OUT/map/docker.stdout"; echo "ATTN1_NATIVE synth FAIL"; exit 1; }
args=(); for f in "$OUT"/map/lib/*.lib; do args+=(--liberty "$f"); done
python3 tools/ref_tile/native_census.py --netlist "$OUT/map/flat.v" --top "$TOP" --out "$OUT/census.json" "${args[@]}" \
  > "$OUT/census.log" 2>&1 || true
grep -E 'Chip area|Number of cells' "$OUT/map/stat_flat.txt" | head -4 || true
python3 - "$OUT/census.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
v = r.get("violations") or []
print("ATTN1_NATIVE status=%s max_dynamic_loads=%s violations=%d role_errors=%d" %
      (r.get("status"), r.get("max_dynamic_loads"), len(v), len(r.get("role_errors") or [])))
for x in v[:25]: print("  VIOL", json.dumps(x)[:300])
for x in (r.get("role_errors") or [])[:10]: print("  ROLE", x[:300])
PY
