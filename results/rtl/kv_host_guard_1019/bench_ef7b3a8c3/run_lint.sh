#!/bin/bash
B=$(cd "$(dirname "$0")" && pwd); cd "$B/src"; export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
rm -rf "$B/out/mu2"; bash rtl/test/mu_qwen_1018/run_mu_hroot.sh . "$B/out/mu2" lint_guard_mu; echo "rc=$?"; rm -rf "$B/out/mu2"/src_*
