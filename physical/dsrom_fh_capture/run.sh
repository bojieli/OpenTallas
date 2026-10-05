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
args=()
for f in rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/proto/ot_fp32_mul_rne_pipe.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv "$D/ot_hdc_v41_matvec.sv" "$D/ot_hdc_v41_fh_ctx.sv" "$D/ot_hdc_v41_fh_sram_return.sv" "$D/ot_hdc_v41_fh_macro_ctx.sv" rtl/dft/ot_rom_secded_dec.sv; do args+=(--source "$f"); done
mkdir -p "$R"
exec python3 "$S/tools/run_abi3_physical.py" --source-root "$S" --view asap7 --top ot_hdc_v41_fh_macro_ctx "${args[@]}" \
 --param ALAT=7 --param CAPTURE=1 --param RETURN_EXTRA=2 \
 --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner WC --hold-corners WC,BC --stages pnr \
 --macro-view "$M=physical/asap7_memory_macros/$M" --macro-place-halo 2 2 \
 --orfs-var ADDER_MAP_FILE= --die-area 0 0 2000 660 --core-area 2 2 1998 658 \
 --orfs-var POST_MACRO_PLACE_TCL=/src/physical/dsrom_fh_capture/macro_place.tcl \
 --core-utilization 35 --max-transition-ns 0.25 --max-fanout 16 --slew-margin-percent 20 --hold-margin-ns 0.02 \
 --sdc-append physical/dsrom_fh_capture/boundary.sdc --io-delay-fraction 0.2 \
 --keep-workdir "$R/work" --nickname-tag C10_capture --output "$R/physical.json"
