#!/bin/bash
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
trap 'chown -R "$HUID:$HGID" /out' EXIT
openroad -no_init -exit /out/prepare_signal.tcl > /out/prepare_signal.log 2>&1
openroad -python -exit /out/infra_replay.py --source /infra/source.odb --target /out/target_signal.odb --nets /out/infra_nets.txt --out /out/combined_infra.odb --report /out/import_receipt.json > /out/import.log 2>&1
set +e
/usr/bin/time -v openroad -no_init -threads "${CPUS:-16}" -exit /out/grt.tcl > /out/grt.log 2>&1
rc=$?
if [ "$rc" = 0 ]; then
  openroad -python -exit /out/verify_import.py > /out/import_verify.log 2>&1
  rc=$?
fi
echo EXIT "$rc" >> /out/grt.log
exit "$rc"
