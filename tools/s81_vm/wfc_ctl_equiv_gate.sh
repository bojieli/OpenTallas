#!/bin/bash
# wfc_ctl_equiv_gate.sh OUTDIR [DEFINE]: differential bench of the wires-only dsfd_vm_static_wfc (+ dsfd_vm_static_wfc_ctl)
# against the r9 parent body (tools/s81_vm/wfc_ref_r9.sv = git 14c171167, renamed); RLAT 17/PAD 0 (READ_PIPE 4), RLAT 14/PAD 3.
set -euo pipefail
OUT=$1; DEF=${2:-}; mkdir -p "$OUT"
V=rtl/dsrom_sys/s81_ph/vm
ok=1
for cfg in "17 0" "14 3"; do set -- $cfg
  iverilog -g2012 ${DEF:+-D$DEF} -P tb_wfc_ctl_equiv.RLAT=$1 -P tb_wfc_ctl_equiv.PAD=$2 -s tb_wfc_ctl_equiv -o "$OUT/sim_$1" \
    $V/dsfd_vm_static_wfc.sv $V/ot_s81_vm_x34.sv $V/ot_s81_vm_x43.sv tools/s81_vm/wfc_ref_r9.sv tools/s81_vm/wfc_ctl_equiv_bench.sv
  for s in 1 2; do vvp -n "$OUT/sim_$1" +seed=$s | tee -a "$OUT/log" | tail -1 | grep -q "WFC_CTL_EQUIV PASS" || ok=0; done
done
[ $ok = 1 ] && echo "WFC_CTL_GATE PASS" || { echo "WFC_CTL_GATE FAIL ${DEF}"; exit 1; }
