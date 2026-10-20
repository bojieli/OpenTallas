#!/usr/bin/env bash
set -euo pipefail
G=$(cd "${1:?graph directory}" && pwd)
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
MODELS=$G/verify_canonical/formal_prep/library_model_formal.v
O=$G/${2:-valid_formal}
mkdir -p "$O"
# Check the exact model being imported, not merely a neighboring coupon file.
python3 - "$MODELS" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);j=json.loads((p.parent/'canonical_model_identity.json').read_text())
assert hashlib.sha256(p.read_bytes()).hexdigest()==j['imported_model_sha256']
assert j['checks']==544 and j['plain_dff_checks']==128
assert all(v['pass_canonical_coupon'] for v in j['imported_results'].values())
PY
cat > "$O/miter.sv" <<'SV'
module svc7_valid_miter(input clk,rst_n,v,input[31:0]a,b,output bad,early);
 wire vg,vn;wire[31:0]yg,yn;wire[1:0]eg,en;
 ot_s81svc7_add_graph_input gold(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(yg),.err(eg),.valid_out(vg));
 ot_s81svc7_add_native dut(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(yn),.err(en),.valid_out(vn));
 assign bad=vg!=vn;
 assign early=vg||vn;
endmodule
SV
cat > "$O/proof.ys" <<'YS'
read_verilog -formal -sv /graph/native.v /models/cells.v /out/miter.sv /src/rtl/hdc/v41x/ot_s81svc7_add_graph_input.sv /src/rtl/hdc/ot_hdc_fp32_f12.sv /src/rtl/hdc/ot_hdc_fastfp.sv /src/rtl/hdc/ot_hdc_prefix.sv
hierarchy -check -top svc7_valid_miter
proc
flatten
opt_clean
async2sync
dffunmap
opt_clean
# Hardware FFs have arbitrary independent initial state. Initial reset held
# for the specified 2-stage landing. No later reset constraints or masks.
# Data/err converge by capture5; only capture4 needs no-valid proof.
sat -seq 4 -set-def-inputs -set clk 1 -set-at 1 rst_n 0 -set-at 2 rst_n 0 -set-at 3 rst_n 0 -prove early 0 -prove-skip 3 -verify -show-inputs -show-outputs
# Valid convergence max6; cover all earlier contract edges and arbitrary
# in-flight reset. Later equality follows the capture-DAG induction.
sat -seq 20 -set-def-inputs -set clk 1 -set-at 1 rst_n 0 -set-at 2 rst_n 0 -set-at 3 rst_n 0 -prove bad 0 -prove-skip 3 -verify -show-inputs -show-outputs
# Nonvacuity: continuously offered legal input becomes visible; no output mask.
sat -seq 10 -set-def-inputs -set clk 1 -set v 1 -set rst_n 1 -set-at 1 rst_n 0 -set-at 2 rst_n 0 -set-at 3 rst_n 0 -prove early 1 -prove-skip 9 -verify -show-inputs -show-outputs
YS
docker run --rm -v "$ROOT:/src:ro" -v "$G:/graph:ro" -v "$MODELS:/models/cells.v:ro" -v "$O:/out" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -l /out/proof.log -s /out/proof.ys' > "$O/stdout.log" 2>&1
tail -n 15 "$O/proof.log"
