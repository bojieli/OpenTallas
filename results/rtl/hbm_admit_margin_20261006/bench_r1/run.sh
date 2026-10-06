set -o pipefail
cd /srv/opentallas-scratch/claude/tk-hbm-admit/r1
F="rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_header_decode.sv rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_su_cp_bind.sv rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_su_cp_association.sv rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_su_cp_context.sv rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_admit_guard.sv rtl/test/hbm_accel/admit_margin_20261006/tb_admit_margin_exact.sv"
build(){ # name REPLAY
 (cd src && verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_admit_margin_exact -GREPLAY=$2 -Mdir ../obj_$1 $F) > build_$1.log 2>&1
}
build rp1 1 && build rp0 0 || { echo 1 > rc; exit 1; }
for s in 1 2 3; do ./obj_rp1/Vtb_admit_margin_exact +SEED=$s +verilator+seed+$s > run_rp1_s$s.log 2>&1 & done
for s in 1 2; do ./obj_rp0/Vtb_admit_margin_exact +SEED=$s +verilator+seed+$s > run_rp0_s$s.log 2>&1 & done
wait; echo 0 > rc
