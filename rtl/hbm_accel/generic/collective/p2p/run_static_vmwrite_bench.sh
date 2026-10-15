#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
build=$(mktemp -d /tmp/hcoll-static-vmwrite.XXXXXX)
trap 'rm -rf "$build"' EXIT
for mutant in 0 1 2; do
  iverilog -g2012 -s tb_hgi_coll_static_vmwrite -Ptb_hgi_coll_static_vmwrite.MUT="$mutant" -o "$build/sim" \
    "$here/ot_hgi_coll_static_vmwrite.sv" "$here/tb_hgi_coll_static_vmwrite.sv"
  if vvp "$build/sim" > "$build/m$mutant.log" 2>&1; then
    cat "$build/m$mutant.log"
    if [[ "$mutant" != 0 ]]; then echo "mutant $mutant survived"; exit 1; fi
  else
    cat "$build/m$mutant.log"
    if [[ "$mutant" == 0 ]]; then exit 1; fi
    echo "mutant $mutant rejected as required"
  fi
done
