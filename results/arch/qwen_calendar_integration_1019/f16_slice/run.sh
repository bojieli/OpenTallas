#!/bin/bash
# QW-F16PROG4: qfd_dv_slice2 PRIVATE_CALR face variants (qfd_dv_slice2_wc / _ec: tload + VM join + treq row hop) and
# the unchanged default faces elaborate on Verilator 5.050 (lint); default faces must not reference the CALR logic.
set -uo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version > verilator.version
sha256sum $(cat files.txt) > sources.sha256
mkdir -p logs; ok=1
for top in qfd_dv_slice2_wc qfd_dv_slice2_ec qfd_dv_slice2_w qfd_dv_slice2_e; do
  "$V" --lint-only -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINCONNECTEMPTY --top-module $top $(cat files.txt) > logs/lint_$top.log 2>&1 \
    && echo "ELAB_PASS $top" || { echo "ELAB_FAIL $top"; ok=0; }
done
grep -q "u_core.g_tld.u_tld" logs/lint_qfd_dv_slice2_wc.log && echo "NOTE g_tld named in wc lint"
grep -E "g_tld|tload" logs/lint_qfd_dv_slice2_w.log && { echo "DEFAULT_FACE_REFERENCES_CALR"; ok=0; }
[ $ok = 1 ] && echo F16_SLICE_CALR_ELAB_PASS || { echo F16_SLICE_CALR_ELAB_FAIL; exit 1; }
