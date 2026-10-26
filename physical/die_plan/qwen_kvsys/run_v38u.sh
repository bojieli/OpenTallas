#!/usr/bin/env bash
# KVG3-WI 10-24: plan v3.8s -> v3.8u = top-down pins for the 22 planned host-root cores of kv3_hub_Wi (G0C 'no pins
# listed').  core_pins_hr.py (host leaf u_host elaborated with yosys from the kit filelist, cluster-plan members mapped
# onto the obsx hierarchy, glue:* members stay partition glue) writes cores/qkd_hr_*_pins.json, cores/core_patch_v38u.json
# and the kv3_hub_Wi entries of core_conns.json into this plan dir; post_v38u.py applies pins_file/orient/note.  Touches
# only partition_types.kv3_hub_Wi.hard_cores and core_conns.json[kv3_hub_Wi]; no lane / latency change (no gen.py step).
#   usage: run_v38u.sh V38S_DIE_PLAN.json OUTDIR RTL_DIR(kv41/rtl) KIT_RTL_F(kit_rtl/g3/kv3_hub_Wi/kit_rtl.f) [WORK]
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd); R=$(cd "$D/../../.." && pwd)
IN=${1:?v3.8s die_plan.json}; O=${2:?output directory}; RTL=${3:?bound RTL dir}; KF=${4:?hub_Wi kit_rtl.f}
W=${5:-$O/elab}; mkdir -p "$O"
python3 "$D/core_pins_hr.py" "$IN" "$RTL" "$KF" "$D" --work "$W" 2> "$O/core_pins_hr.log"
python3 "$D/post_v38u.py" "$IN" "$D" > "$O/die_plan.json"
cp -r "$D/cores" "$D/census" "$D/core_conns.json" "$D/cells_evidence.json" "$D/die_io.json" "$D"/l1_cores_v3*.json "$O/"
python3 "$R/tools/die_plan/check.py" "$O/die_plan.json" --out "$O/g0u"
python3 "$R/tools/die_plan/check.py" "$O/die_plan.json" --completeness --out "$O/g0cu" || true
