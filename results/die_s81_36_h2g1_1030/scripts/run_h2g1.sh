#!/bin/bash
# DIE-S81-36/H2G1 (ROOT-authorized ONE more protected G1 clock install after the free-site re-convert): free-site H2 1811-cell tree built on the EXISTING
# native 3_place by the canonical install_stage pre_cts hook (DIE-QC-36 A0; only tree cells DPL'd, all else FIRM),
# official dependency-free ORFS do-cts (leaf-complete plan tree: TritonCTS not run), then a read-only audit.
# NO synthesis, GPL, GRT-repair, DRT, finish or G2.  usage: run_h2g1.sh RUNDIR [MEM_GB] [THREADS]
set -euo pipefail
R=$1; MEM=${2:-24}; THREADS=${3:-8}
K=$R/kit
B=$K/run/results/asap7/kl_dsfd_coll_lane_w_safe8_ntf_h2fixw/base
python3 -I - "$R" <<'PY'
import hashlib, json, sys
from pathlib import Path
r = Path(sys.argv[1]); k = r / "kit"
h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
p = json.loads((r / "prep/prep.json").read_text()); f = json.loads((r / "prep/preflight.json").read_text())
assert p["verdict"] == "PASS" and f.get("verdict") == "PASS", "prep/preflight not PASS"
base = next((k / "run/results/asap7").glob("*/base"))
assert h(base / "3_place.odb") == p["place_odb_sha256"] == "56af214f7b538dbe07f42249f6d158491338cd68b7eb302750f0ef617ccb323e"
assert h(k / "master_core_infra_late.tcl") == p["late_tcl_sha256"], "late hook changed after prep"
assert not [x for x in base.iterdir() if x.name[:2] in ("4_", "5_", "6_")], "not a fresh G1 successor"
print("H2G1_BIND PASS: native 3_place", p["place_odb_sha256"][:12], "late hook", p["late_tcl_sha256"][:12])
PY
echo "image openroad/orfs:asap7lock $(docker image inspect --format '{{.Id}}' openroad/orfs:asap7lock) host $(hostname) start $(date -Is)" > "$K/image.txt"
docker run --rm --name "claude-h2g1b-$$" --cpus "$THREADS" --memory "${MEM}g" --memory-swap "${MEM}g" \
  -v "$K":/work -v "$R":/rd -e HUID=$(id -u) -e HGID=$(id -g) -w /work openroad/orfs:asap7lock bash -lc '
set -uo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/kit_modes.py check /work --step cts || exit 9
M="make --no-print-directory -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run NUM_CORES='"$THREADS"'"
$M do-cts; rc=$?
B=$(ls -d /work/run/results/asap7/*/base)
if [ $rc = 0 ]; then
  PLACE=$B/3_place.odb CTS=$B/4_cts.odb SLICE=/rd/admitted/slice_model.json TCL=/rd/admitted/master_core_infra.tcl \
    OUT=/rd/audit.json openroad -python -exit /rd/scripts/h2g1_audit.py > /rd/audit.log 2>&1; rc=$?; tail -2 /rd/audit.log
fi
chown -R $HUID:$HGID /work /rd/audit.json /rd/audit.log 2>/dev/null
exit $rc' > "$R/run_cts.log" 2>&1 && rc=0 || rc=$?
echo "end $(date -Is) rc $rc" >> "$K/image.txt"
grep -E "OT_CORE_INFRA|H2G1_|Error|ERROR" "$R/run_cts.log" | tail -20
exit $rc
