#!/bin/bash
set -eu
# One small component build. No SU/SM/array arithmetic elaboration.
job=$1
src=$job/src
export TMPDIR=$job/tmp
mkdir -p "$TMPDIR" "$job/obj"
cd "$src"
python3 - <<'PY'
import ast
from pathlib import Path
from types import SimpleNamespace
# Execute the existing allocator method, without importing checkpoint/model code.
p=Path('tools/gpu_sys/v41_hbm.py')
t=ast.parse(p.read_text())
c=next(n for n in t.body if isinstance(n,ast.ClassDef) and n.name=='Program')
f=next(n for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='put')
a=ast.Module(body=[f],type_ignores=[]);ast.fix_missing_locations(a)
ns={};exec(compile(a,str(p),'exec'),ns)
fixture=SimpleNamespace(cur=0x1000,a={})
base_a=ns['put'](fixture,'W2_A_rows',64,64)
ns['put'](fixture,'private_guard',64,64)
base_b=ns['put'](fixture,'W2_B_rows',64,64)
assert base_a==4096 and base_b==4224 and fixture.cur<=8192
Path('private_alloc.svh').write_text(f'localparam integer RAM_BYTES=8192;\nlocalparam [31:0] BASE_A=32\'d{base_a}, LIMIT_A=32\'d{base_a+64}, BASE_B=32\'d{base_b}, LIMIT_B=32\'d{base_b+64};\n')
print('ACTUAL_PROGRAM_PUT private RAM8192B A',base_a,'B',base_b,'each64B, guard64B')
PY
verilator --version > "$job/toolchain.log"
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_hbm_integrated_w2_publication_nash --Mdir "$job/obj" -I. \
 rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv \
 rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_prior_debt.sv \
 rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_sm0_borrow.sv \
 rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_w2_result_sink.sv \
 rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv \
 rtl/test/hbm_accel/integrated_20261005/tb_hbm_integrated_w2_publication_nash.sv > "$job/compile.log" 2>&1
set +e
"$job/obj/Vtb_hbm_integrated_w2_publication_nash" > "$job/normal.log" 2>&1
normal=$?
printf 'normal_rc=%s\n' "$normal" > "$job/runtime.rc"
if test "$normal" != 0; then exit "$normal"; fi
"$job/obj/Vtb_hbm_integrated_w2_publication_nash" +CORRUPT_READBACK > "$job/corrupt.log" 2>&1
negative=$?
printf 'corrupt_rc=%s\n' "$negative" >> "$job/runtime.rc"
if test "$negative" = 0; then echo 'corrupt readback unexpectedly succeeded'; exit 1; fi
if ! rg -q 'CORRUPT_READBACK_DETECTED' "$job/corrupt.log" || ! rg -q 'EXPECTED_CORRUPT_READBACK_FAIL_CLOSED' "$job/corrupt.log"; then echo 'wrong negative failure'; exit 1; fi
if ! rg -q 'PASS W2_PUBLICATION_SHARED_CPEND_CPL' "$job/normal.log"; then echo 'normal missing verdict'; exit 1; fi
echo 'PASS normal + expected nonzero corrupted actual RAM readback'
