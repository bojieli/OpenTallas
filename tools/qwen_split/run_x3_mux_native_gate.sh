#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?output directory required}
mkdir -p "$out"
for mut in 0 1 2 3; do
    iverilog -g2012 -s tb_qfd_x3_mux_native -Ptb_qfd_x3_mux_native.MUT="$mut" -o "$out/m$mut" \
        "$root/rtl/qwen_split/ot_qfd_x3_mux_native.sv" "$root/rtl/test/qwen_split/tb_qfd_x3_mux_native.sv"
    if vvp "$out/m$mut" > "$out/m$mut.log" 2>&1; then rc=0; else rc=$?; fi
    if (( mut == 0 )); then
        cat "$out/m$mut.log"
        if (( rc != 0 )) || ! grep -q '^PASS native static Q/KVN' "$out/m$mut.log"; then
            echo 'positive scheduled transport failed' >&2
            exit 1
        fi
    else
        if (( rc == 0 )) || ! grep -q '^FATAL:' "$out/m$mut.log"; then
            echo "mutant $mut did not demonstrate a functional failure" >&2
            exit 1
        fi
        echo "MUTANT $mut observed FAIL rc$rc"
    fi
done
