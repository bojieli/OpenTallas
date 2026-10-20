#!/usr/bin/env bash
set -euo pipefail
sha256sum gate_iop.odb fp_margin_lint.py fp_margin_lint.tcl fp_audit.tcl > fp_source_sha256.txt
docker run --rm -v "$PWD:/work" -w /work openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit fp_audit.tcl > fp_audit.log 2>&1
python3 fp_margin_lint.py check fp_dump.json --out fp_result.json
