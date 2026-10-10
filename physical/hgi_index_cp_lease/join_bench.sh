#!/usr/bin/env bash
set -eu
mode=${1:-exact}
task_tmp=$(mktemp -d /tmp/hgi-index-cp-join.XXXXXX)
trap 'rm -rf "$task_tmp"' EXIT
# Immutable dependencies, read from this agent's object store only.
source_pin=4ebccc7fa6cba44b5a61d22623447b7f9b2f3d8e
for f in rtl/hbm_accel/generic/idx/ot_hgi_idx_unit_lease.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_index_lease.sv physical/hbm_accel_die_views/hgi_idx_lease/rtl/hfd_hgi_idx_lease.sv; do
 git show "$source_pin:$f" > "$task_tmp/${f##*/}"
done
if [[ "$mode" == mutant ]]; then
 python3 - "$task_tmp/ot_hgi_idx_index_lease.sv" <<'MUTATE'
import sys
p=sys.argv[1];s=open(p).read();old='lease_frame[35:32], lease_frame[31:0]'
assert s.count(old)==1
open(p,'w').write(s.replace(old,"4'd0, 32'd0"))
MUTATE
fi
iverilog -g2012 -s tb -o "$task_tmp/sim" physical/hgi_index_cp_lease/tb_join.sv rtl/hbm_accel/control/ot_hgi_index_cp_lease.sv "$task_tmp/ot_hgi_idx_unit_lease.sv" "$task_tmp/ot_hgi_idx_index_lease.sv" "$task_tmp/hfd_hgi_idx_lease.sv" physical/hbm_accel_die_views/common/ot_hfd_oreg1.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_owned.sv rtl/hbm_accel/generic/idx/ot_hgi_idx_merge.sv rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk_registered.sv rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk.sv
if [[ "$mode" == mutant ]]; then vvp "$task_tmp/sim" +MODE=0;else for n in 0 1 2 3;do vvp "$task_tmp/sim" +MODE="$n";done;fi
