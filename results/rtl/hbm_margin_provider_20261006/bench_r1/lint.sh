set -o pipefail
cd /srv/opentallas-scratch/claude/hbm-margin-provider/lint/src
F="-f rtl/hbm_accel/integrated_20261006/sfu_c12_selected_parent.files.f rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_su_cp_context.sv rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_admit_guard.sv rtl/hbm_accel/integrated_20261006/ot_hbm_integrated_su_provider_margin.sv rtl/hbm_accel/integrated_20261006/sfu_c12_selected/14_ot_hdc_fastfp.sv"
L="verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTITOP --top-module ot_ds_hbm_cluster20_integrated"
LOR="-GCOMBINED_ENABLE=1 -GSFU_C12_ENABLE=1 -GSFU_NATIVE_VM_ENABLE=1 -GNORM_C12_ENABLE=1 -GNORM_NATIVE_VM_ENABLE=1 -GNORM_NATIVE_INPUT_CP=1 -GSU_ENABLE=1 -GSU_REGISTERED_OUTPUTS=1 -GSU_REGISTERED_STATUS=1 -GSU_REGISTERED_BOUNDARY=1 -GSU_BALANCED_OWNER_BOUNDARY=1 -GSU_FOUR_COMBINATIONAL_CUTS=1 -GSU_FAST_OWNER_FRONTIER=1 -GSU_PROVIDER_ADAPTER=1 -GW2_RESULT_ENABLE=1 -GW2_SECTOR_ENABLE=1 -GFORMATTER_ENABLE=1 -GNORMAL_GATHER_ENABLE=1 -GLOCAL_CP_RESET_ENABLE=1 -GVM_AW=21"
MAR="-GSU_PARALLEL_PHASE_VALIDATION=1 -GSU_OWNER_VETO_POLARITY=1 -GSU_PIN_MARGIN=1 -GSU_RELEASE_REPLAY=1 -GSU_ADMIT_SHADOW=3"
$L $F > ../lint_default.log 2>&1; echo default rc=$?
$L $F $LOR > ../lint_lorentz.log 2>&1; echo lorentz rc=$?
$L $F $LOR $MAR > ../lint_margin_provider.log 2>&1; echo margin_provider rc=$?
$L $F $LOR $MAR -GSU_PROVIDER_ADAPTER=0 > ../lint_margin_legacy.log 2>&1; echo margin_legacy rc=$?
