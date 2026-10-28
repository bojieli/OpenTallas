#!/bin/bash
# Export a (hierarchical) gate-level netlist to Yosys JSON for ohier.
# usage: export_json.sh NETLIST.v TOP OUT.json LIB [LIB...]   (run inside the ORFS image)
set -euo pipefail
net=$1; top=$2; out=$3; shift 3
tmp=$(mktemp -d)
cmd=""
for l in "$@"; do
  case $l in
    *.gz) b=$tmp/$(basename "${l%.gz}"); zcat "$l" > "$b"; cmd+="read_liberty -lib $b; ";;
    *) cmd+="read_liberty -lib $l; ";;
  esac
done
yosys -q -p "${cmd} read_verilog $net; hierarchy -check -top $top; write_json $out"
rm -rf "$tmp"
