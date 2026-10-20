#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
R=$PWD;A=results/rtl/coll_native32_1020;N=$R/native_q
mkdir -p "$N";cp "$A/native_config.mk" "$N/config.mk";cp "$A/constraint.sdc" "$N/constraint.sdc";cp "$A/native_dump.tcl" "$N/native_dump.tcl"
docker image inspect openroad/orfs:asap7lock --format '{{.Id}}' > "$N/image.id"
sha256sum rtl/rom/*native32.sv rtl/hdc/ot_hdc_fp32_add_lat{,_fan32}.sv rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native.v physical/asap7_memory_macros_v2/ot_sram_1r1w2c_{128,256}x64_m1/*lib > "$N/input_identity.sha256"
docker run --rm -v "$R:/src:ro" -v "$N:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work synth' > "$N/synth.log" 2>&1
docker run --rm -v "$R:/src:ro" -v "$N:/work" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /work/native_dump.tcl > "$N/census.log" 2>&1
# QW-ORPHANS 10-20: official pre-gate census (tools/ref_tile/native_census.py) on the mapped netlist, actual Liberty roles
docker run --rm -v "$R:/src:ro" -v "$N:/work" openroad/orfs:asap7lock bash -lc 'L=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM; A=""; for f in $L/*RVT_TT*; do A="$A --liberty $f"; done; for f in /src/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_{128,256}x64_m1/*_tt.lib; do A="$A --liberty $f"; done; python3 /src/tools/ref_tile/native_census.py --netlist $(ls /work/results/asap7/opentallas_ot_coll_split_q_native32_asap7_ref_gate/base/1_synth.v /work/results/asap7/opentallas_ot_coll_split_q_native32_asap7_ref_gate/base/1_2_yosys.v 2>/dev/null | head -1) --top ot_coll_split_q_native32 $A --out /work/native_census.json' > "$N/official_census.log" 2>&1 || true
python3 - "$N" <<'PY'
import json,sys,collections
r=json.load(open(sys.argv[1]+'/native_census.json'))
v=r.get('violations',[]);c=collections.Counter(x['driver_role'] for x in v)
print('QW_ORPHANS_COLL_Q_CENSUS',r['status'],'roots',r.get('roots_examined'),'max',r.get('max_dynamic_loads'),'viol',len(v),dict(c),'role_errors',len(r.get('role_errors',[])))
PY
