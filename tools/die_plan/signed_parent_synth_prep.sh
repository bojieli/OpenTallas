#!/bin/bash
# Explicit mapped-parent producer only. Run through ot-run; no LEC/physical stage.
set -uo pipefail
K=$(cd "$1" && pwd)
MEM=${2:-16}; CPUS=${3:-8}
if [ "${OT_SIGNED_PARENT_PREP_SYNTH:-0}" != 1 ]; then echo 'HELD: explicit SYNTH PREP opt-in required'; exit 78; fi
python3 -I "$K/signed_parent_adapter.py" --check-synth-prep "$K" || exit 78
OUT=$K/signed_parent/synth_prep
if [ -e "$OUT" ]; then echo 'HELD: retain prior SYNTH PREP; use a fresh owned KIT'; exit 78; fi
mkdir -p "$OUT"
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
docker run --rm --name signed-parent-synth-prep-$$ --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" \
  -v "$K":/work:ro -v "$OUT":/prep -e HUID=$(id -u) -e HGID=$(id -g) -e NUM_CORES="$CPUS" \
  -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1;
  python3 -I /work/native_bb.py /OpenROAD-flow-scripts/flow/scripts/synth_preamble.tcl --physical-synth /OpenROAD-flow-scripts/flow/scripts/synth.tcl || exit 9;
  MAP_ARGS=();
  if [ -f /work/adder_map_dontuse.py ]; then
    python3 -I /work/adder_map_dontuse.py gen --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --out /prep/adder_map_dontuse.v --report /prep/adder_map_dontuse.json || exit 9;
    MAP_ARGS+=(ADDER_MAP_FILE=/prep/adder_map_dontuse.v);
  fi;
  make DESIGN_CONFIG=/work/signed_parent/physical_config.mk WORK_HOME=/prep/run FLOW_VARIANT=base NUM_CORES="$NUM_CORES" "${MAP_ARGS[@]}" synth;
  rc=$?;
  if [ "$rc" = 0 ] && [ -f /work/adder_map_dontuse.py ]; then
    N=$(find /prep/run/results -name 1_2_yosys.v -print -quit);
    python3 -I /work/adder_map_dontuse.py check --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --netlist "$N" --report /prep/dont_use_check.json; rc=$?;
  fi;
  chown -R "$HUID:$HGID" /prep; exit "$rc"' > "$OUT/native.log" 2>&1
RC=$?
printf '%s\n' "$RC" > "$OUT/exit.txt"
# This is a producer artifact, not a proof receipt. Existing native files/leases
# were mounted read-only; no physical or abstract-parent EQ is dispatched.
python3 - "$OUT" "$RC" <<'PY'
import hashlib,json,sys
from pathlib import Path
out=Path(sys.argv[1]);files=sorted(out.glob('run/results/asap7/*/base/1_2_yosys.v'))
record=dict(status='SYNTH PREP ONLY; native-parent EQ NOT RUN',synth_exit=int(sys.argv[2]),
            mapped_parent_netlists={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(out/'mapped_parent_producer.json').write_text(json.dumps(record,indent=2)+'\n')
PY
exit "$RC"
