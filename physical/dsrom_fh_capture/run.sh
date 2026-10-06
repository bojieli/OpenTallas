#!/bin/bash
# Execute through unchanged admit.sh with a fresh EPYC2 load <128 check.
set -euo pipefail
if [ "$#" -ne 1 ]; then echo 'Usage: run.sh RUN_ROOT' >&2; exit 2; fi
R=$(realpath -m "$1")
mkdir -p "$R"
S=$(realpath "$(dirname "$0")/../..")
cd "$S"
python3 - <<'PY'
import hashlib,json
from pathlib import Path
p=json.loads(Path('SOURCE_PIN.json').read_text())
for f,h in p['sha256'].items():
    assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,f
print('SOURCE_PIN verified',p['commit'],flush=True)
PY
python3 -c 'from pathlib import Path; assert float(Path("/proc/loadavg").read_text().split()[0]) < 128'
uptime
free -g
df -h "$R"
export OT_ORFS_NUM_CORES=16
export OT_SYNTH_TIMEOUT_SECONDS=unlimited
export OT_FLOW_TIMEOUT_SECONDS=unlimited
D=rtl/hdc/v41/dspark_fused_head/capture_candidate
M=ot_sram_1r1w_512x128_m4_r2c2
SPLIT=${OT_FH_PROTECT_SPLIT:-0}
case "$SPLIT" in 0|1) ;; *) echo 'OT_FH_PROTECT_SPLIT must be0 or1' >&2; exit 2;; esac
RETURN_EXTRA=$((2+SPLIT))
RETIRE=${OT_FH_RETIRE:-0}
VM_GUARD=${OT_FH_VM_GUARD:-0}
case "$VM_GUARD" in 0|1) ;; *) exit 2;; esac
VM_ENDPOINT=${OT_FH_VM_ENDPOINT:-0}
if [ "$VM_GUARD" = 1 ] && [ "$VM_ENDPOINT" != 1 ]; then exit 2; fi
case "$VM_ENDPOINT" in 0|1) ;; *) echo "OT_FH_VM_ENDPOINT must be0 or1" >&2; exit 2;; esac
if [ "$VM_ENDPOINT" = 1 ] && [ "$RETIRE" != 1 ]; then echo "Native VM endpoint requires RETIRE=1" >&2; exit 2; fi
case "$RETIRE" in 0|1) ;; *) echo "OT_FH_RETIRE must be0 or1" >&2; exit 2;; esac
TAG=${OT_FH_ROUTE_TAG:-C10_capture}
STOP_AFTER=${OT_FH_STOP_AFTER:-finish}
case "$STOP_AFTER" in floorplan|cts|finish) ;; *) echo "Unsupported ORFS stop stage" >&2; exit 2;; esac
args=()
if [ "$VM_ENDPOINT" = 1 ]; then
 args+=(--source rtl/dsrom_sys/protected_vm/ot_dsrom_vm_pkg.sv --source "$D/ot_hdc_v41_fh_vm_endpoint_ctx.sv" --source "$D/ot_hdc_v41_fh_checked_permission.sv" --orfs-var SYNTH_HDL_FRONTEND=slang)
fi
for f in rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/proto/ot_fp32_mul_rne_pipe.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv "$D/ot_hdc_v41_matvec.sv" "$D/ot_hdc_v41_fh_ctx.sv" "$D/ot_hdc_v41_fh_sram_return.sv" "$D/ot_hdc_v41_fh_macro_ctx.sv" rtl/dft/ot_rom_secded_dec.sv; do args+=(--source "$f"); done
if [ "$RETIRE" = 1 ]; then
 for f in "$D/ot_hdc_v41_fh_fault_retire.sv" "$D/ot_hdc_v41_fh_retire_parent.sv"; do args+=(--source "$f"); done
fi
mkdir -p "$R"
exec python3 "$S/tools/run_abi3_physical.py" --source-root "$S" --view asap7 --top ot_hdc_v41_fh_macro_ctx "${args[@]}" \
 --param ALAT=7 --param CAPTURE=1 --param RETURN_EXTRA="$RETURN_EXTRA" --param PROTECT_SPLIT="$SPLIT" --param RETIRE="$RETIRE" --param VM_ENDPOINT="$VM_ENDPOINT" --param VM_GUARD="$VM_GUARD" \
 --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --stages pnr --pnr-stop-after "$STOP_AFTER" \
 --macro-view "$M=physical/asap7_memory_macros/$M" --macro-place-halo 2 2 \
 --orfs-var ADDER_MAP_FILE= --die-area 0 0 2000 660 --core-area 2 2 1998 658 \
 --orfs-var MACRO_PLACEMENT_TCL=/src/physical/dsrom_fh_capture/macro_place.tcl \
 --place-density 0.60 --orfs-var PLACE_DENSITY_LB_ADDON= --core-utilization 35 --max-transition-ns 0.25 --max-fanout 16 --slew-margin-percent 20 --hold-margin-ns 0.02 \
 --sdc-append physical/dsrom_fh_capture/boundary.sdc --io-delay-fraction 0.2 \
 --keep-workdir "$R/work" --nickname-tag "$TAG" --output "$R/physical.json"
