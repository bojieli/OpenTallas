#!/bin/bash
set -e
result/tiled_mutant/Vtb_qfd_su_vm_bv_acc > result/tiled_mutant/checked_run.log 2>&1
cat result/tiled_mutant/checked_run.log
if grep -q '^FAIL qfd_su_vm_bv ' result/tiled_mutant/checked_run.log; then exit 1; fi
if ! grep -q '^PASS qfd_su_vm_bv ' result/tiled_mutant/checked_run.log; then exit 2; fi
