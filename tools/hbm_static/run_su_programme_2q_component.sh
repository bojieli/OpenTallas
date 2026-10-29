#!/bin/bash
# Run through ot-run from an own staged runtime. No SU arithmetic array or physical qualification.
set -euo pipefail
if [ "$#" != 2 ]; then echo "usage: $0 native_prog.mem runtime_directory" >&2; exit 2; fi
root=$(git rev-parse --show-toplevel)
programme=$(realpath "$1")
runtime=$(realpath -m "$2")
mkdir -p "$runtime/src"
python3 "$root/tools/hbm_static/su_programme_compile.py" "$programme" "$runtime/lower" --root5 --parts 2 --line-bits 4940 --resident-edges 7111 --mut-q 0 > "$runtime/lowering.log"
cp "$root/rtl/test/hbm_su_prog/tb_hbm_su_programme_2q.sv" "$runtime/src/"
for module in ot_hbm_su_programme_root_h5 ot_hbm_su_programme_pgcol ot_hbm_su_programme; do
 cp "$root/rtl/hbm_accel/generic/adapters/static_su/programme/$module.sv" "$runtime/src/"
done
cp "$root/rtl/lib/ot_rst_relay.sv" "$runtime/src/"
cp "$root/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" "$runtime/src/"
cd "$runtime"
verilator --binary --timing -j "${JOBS:-1}" -Wno-fatal --top-module tb_hbm_su_programme_2q -I./lower --Mdir obj src/*.sv src/*.v >build.log 2>&1
obj/Vtb_hbm_su_programme_2q +DIR=lower >nominal.log 2>&1
set +e
obj/Vtb_hbm_su_programme_2q +DIR=lower +MUT_CFG >mut_cfg.log 2>&1
rc=$?
set -e
if [ "$rc" = 0 ] || ! grep -q '2Q_COMMAND_MISMATCH' mut_cfg.log; then cat mut_cfg.log; exit 1; fi
printf 'MUT_CFG_CAUGHT rc=%s\n' "$rc"
cat nominal.log
