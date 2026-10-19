#!/bin/bash
set -euo pipefail
T=tools/hbm_hidx_wrapper
mkdir -p out_repr_namecheck
python3 "$T/geometry.py"
python3 "$T/capacity_sensitivity.py"
python3 "$T/constraints.py"
python3 "$T/pg_model.py"
python3 "$T/binding.py"
python3 "$T/arc_domains.py"
if test -f out/roundtrip_mismatch.json;then mv out/roundtrip_mismatch.json out_repr_namecheck/identifier_escape_mismatch.json;fi
sha256sum tools/hbm_hidx_wrapper/* canonical/* out/*.json out/*.log out/*.v out/*.lib out/*.sdc out/*.tcl out/*.gz >out/SHA256SUMS_FINAL
sha256sum out_repr_bad/* out_repr_namecheck/* 2>/dev/null | grep -v '  .*initial_draft$' >out/FAILED_EVIDENCE_SHA256SUMS || true
