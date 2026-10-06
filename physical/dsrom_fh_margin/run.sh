#!/bin/bash
# Margin-first DS fused head context (owner rule 2026-10-06): MARGIN=1 HARD_LANE=1 (hardened protected lane RTL,
# ADDR_PIPE=2 request distribution, RETURN_EXTRA 5, zero-cycle broadcast trees, five-deep retirement, staged checked
# endpoint). Flat integration of the 64 lanes (SRAM macro OBS M1-M4 only, parent routes over it; the hardened lane's
# own abstract obstructs M1-M7 and carries M6 PG pins under M7 OBS). Routed at 770 ps, signed off at 833.333 ps.
# Usage: run.sh <source root> <out dir>
set -o pipefail
S=${1:?src}; O=${2:?out}; mkdir -p $O; cd $S
export OT_ORFS_NUM_CORES=16 NUM_CORES=16 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
export OPENTALLAS_ORFS_IMAGE=${OPENTALLAS_ORFS_IMAGE:-sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29}
D=rtl/hdc/v41/dspark_fused_head/capture_candidate
M=ot_sram_1r1w_512x128_m4_r2c2
H=physical/dsrom_fh_margin
args=(--source rtl/dsrom_sys/protected_vm/ot_dsrom_vm_pkg.sv --orfs-var SYNTH_HDL_FRONTEND=slang)
for f in rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/proto/ot_fp32_mul_rne_pipe.sv \
  rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv \
  $D/ot_hdc_v41_matvec.sv $D/ot_hdc_v41_fh_ctx.sv $D/ot_hdc_v41_fh_sram_return.sv \
  rtl/hdc/v41/dspark_fused_head/lane_hardened/ot_hdc_v41_fh_sram_return_hardened.sv $D/ot_hdc_v41_fh_macro_ctx.sv \
  rtl/dft/ot_rom_secded_dec.sv $D/ot_hdc_v41_fh_fault_retire.sv $D/ot_hdc_v41_fh_retire_parent.sv \
  $D/ot_hdc_v41_fh_vm_endpoint_ctx.sv $D/ot_hdc_v41_fh_checked_permission.sv; do args+=(--source $f); done
echo "$(date -Is) START $(hostname) $(cat SOURCE_COMMIT_OVERLAY 2>/dev/null)" >> $O/MANIFEST
python3 tools/run_abi3_physical.py --source-root "$S" --view asap7 --top ot_hdc_v41_fh_macro_ctx "${args[@]}" \
 --param ALAT=7 --param CAPTURE=1 --param RETURN_EXTRA=5 --param PROTECT_SPLIT=1 --param RETIRE=1 --param VM_ENDPOINT=1 \
 --param VM_GUARD=1 --param HARD_LANE=1 --param MARGIN=1 \
 --clock-period-ns 0.770 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --stages pnr \
 --macro-view "$M=physical/asap7_memory_macros/$M" --macro-place-halo 2 2 \
 --orfs-var ADDER_MAP_FILE= --die-area 0 0 1800 660 --core-area 2 2 1798 658 \
 --orfs-var MACRO_PLACEMENT_TCL=/src/$H/macro_place.tcl \
 --place-density 0.50 --orfs-var PLACE_DENSITY_LB_ADDON= --core-utilization 30 \
 --max-transition-ns 0.25 --max-fanout 16 --slew-margin-percent 20 --hold-margin-ns 0.035 \
 --step-tcl PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl --step-tcl PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl \
 --sdc-append physical/dsrom_fh_capture/boundary.sdc --io-delay-fraction 0.2 \
 --keep-workdir "$O/work" --nickname-tag fh_margin --keep-heavy-artifacts --output "$O/physical.json" > $O/route.log 2>&1
echo $? > $O/route.exit
python3 tools/w18/corner_sta.py --orfs-dir $O/work/orfs --macro physical/asap7_memory_macros/$M --post-sdc $H/signoff_833.sdc \
 --post-sdc physical/dsrom_fh_capture/boundary.sdc --output $O/corner_sta.json > $O/sta.log 2>&1
echo $? > $O/sta.exit
echo "$(date -Is) END route=$(cat $O/route.exit) sta=$(cat $O/sta.exit)" >> $O/MANIFEST
touch $O/DONE
