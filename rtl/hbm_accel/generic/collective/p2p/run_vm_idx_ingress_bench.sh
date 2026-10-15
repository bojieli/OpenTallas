#!/usr/bin/env bash
set -euo pipefail
p=$(cd -- "$(dirname -- "$0")" && pwd)
out=$(mktemp -d /tmp/hcoll-vm-idx-ingress.XXXXXX)
trap 'rm -rf "$out"' EXIT
for m in 0 1 2;do
 iverilog -g2012 -s tb_hgi_coll_vm_idx_ingress -Ptb_hgi_coll_vm_idx_ingress.MUT="$m" -o "$out/sim" \
  "$p/tb_hgi_coll_vm_idx_ingress.sv" "$p/ot_hgi_coll_vm_idx_ingress.sv"
 if vvp "$out/sim" > "$out/m$m.log" 2>&1;then
  cat "$out/m$m.log";[[ "$m" == 0 ]] || { echo mutant survived;exit 1; }
 else
  cat "$out/m$m.log";[[ "$m" != 0 ]] || exit 1
  grep -q 'FATAL:' "$out/m$m.log";echo "shared ingress mutant$m rejected"
 fi
done
