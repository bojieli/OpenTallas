#!/usr/bin/env bash
# Continue the single admitted CTS snapshot, keeping all completed ORFS objects.
# Usage: bash continue_route.sh REMOTE_GATE_ROOT EXACT_IMAGE_ID
set -euo pipefail
r=$(realpath "$1")
image=$2
src=$r/src
c=$r/routes/gate/work/orfs
kit=physical/ref_tile/hcoll_ring_state_capture_1417
cd "$src"
printf '%s\n' \
 'c827fb8dc971baca5e155b88a3381eab218999b127e3a4b9f419f3f28e77d514  rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_pring_static.sv' \
 '9ffba061514f1f2fc150a38da9706c8a53c22dd38d077cbc3c7e24a7fb096857  rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_pring_static_state_capture.sv' | sha256sum -c -
bases=("$c"/results/asap7/*/base)
test "${#bases[@]}" -eq 1
test -s "${bases[0]}/4_1_cts.odb"
sha256sum "$c/config.mk" "$src/$kit/signoff.sdc" "$r/source_snapshot.json" 2>/dev/null > "$r/continue_inputs.sha256" || sha256sum "$c/config.mk" "$src/$kit/signoff.sdc" > "$r/continue_inputs.sha256"
docker image inspect --format '{{.Id}}' "$image" > "$r/continue_image_id.txt"
docker run --rm -e LEC_CHECK=0 -v "$src:/src:ro" -v "$c:/work" -w /OpenROAD-flow-scripts/flow "$image" bash -lc \
 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts && python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 finish metadata-generate' > "$r/route_continue.log" 2>&1
printf 'finish_rc=0\n' > "$r/route_continue.status"
python3 tools/w18/corner_sta_ref.py --orfs-dir "$c" --extra-sdc "$src/$kit/signoff.sdc" --output "$r/corner_sta.json" > "$r/corner_sta.log" 2>&1
printf 'corner_rc=0\n' >> "$r/route_continue.status"
python3 tools/ref_tile/ref_tile.py export --orfs-dir "$c" --kit "$kit" --out "$r/views/ot_hgi_coll_pring_static_state_capture_lane" > "$r/export.log" 2>&1
printf 'export_rc=0\n' >> "$r/route_continue.status"
python3 - "$r" "$src" <<'PY'
import json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(sys.argv[2])/'tools/hier_contract'))
import native_pin_audit as N
r=pathlib.Path(sys.argv[1]); cell='ot_hgi_coll_pring_static_state_capture_lane'
a=N.audit_one((sys.argv[2],cell,str(r/'views'/cell)))
a['scope']='single routed diagnostic candidate; current parent not adopted; +1edge read/write visibility'
(r/'native_pin_audit.json').write_text(json.dumps(a,indent=1)+'\n')
assert a.get('pass') and a.get('outputs')==128 and a.get('inputs')==164 and a.get('insertion'),a
print(json.dumps(a))
PY
printf 'native_pin_rc=0\n' >> "$r/route_continue.status"
