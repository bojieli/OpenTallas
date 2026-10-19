#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
sha256sum -c INPUT_SHA256SUMS
mkdir output
gzip -dc input/netlist.v.gz >input/netlist.v
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
runner=(docker run --rm --network none --user "$(id -u):$(id -g)" -v "$PWD:/work" -w /work "$image")
"${runner[@]}" bash -lc 'sha256sum -c kit/platform_SHA256SUMS && sha256sum -c kit/lib_SHA256SUMS' >output/platform.log 2>&1
# Exactly one physical invocation. Every failure remains immutable.
"${runner[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /work/kit/place.py >output/place.log 2>&1
sha256sum output/*checkpoint.odb output/pg_checkpoint.v >output/checkpoint.sha256
failed=0
attempt() { local label="$1";shift;local rc=0;"$@" >"output/$label.log" 2>&1 || rc=$?;echo "$label $rc" >>output/stage_exit_status;if ((rc));then failed=1;fi; }
attempt raw "${runner[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /work/kit/export_raw.py /work/output/pg_checkpoint.odb /work/output/native
attempt metal "${runner[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /work/kit/export_metal.py /work/output/pg_checkpoint.odb /work/output
attempt conductor "${runner[@]}" bash -lc 'cd output;python3 ../kit/prove_metal_readonly.py'
attempt strict "${runner[@]}" bash -lc 'cp input/canonical/all.lib output/native/;cd output/native;sha256sum raw.json all.lib >SHA256SUMS;python3 /work/kit/vendor/strict_replay.py . /work/output/strict'
attempt checkpoint_immutable sha256sum -c output/checkpoint.sha256
if ((failed));then exit 1;fi
echo 'PLACEMENT_PG_NATIVE_DIAGNOSTIC_COMPLETE_NO_CTS_NO_ROUTE' >output/status
