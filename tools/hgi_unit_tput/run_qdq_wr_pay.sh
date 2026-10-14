#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory};mkdir -p "$out"
pay=rtl/hbm_accel/generic/qw/ot_hgi_qdq_wr_pay.sv
if [[ ${MUT:-0} != 0 ]]; then
 python3 - "$pay" "$out/mutated_pay.sv" "${MUT}" <<'PY'
from pathlib import Path
import sys,hashlib,json
src=Path(sys.argv[1]);s=src.read_text()
a,b=("d[k*32 +: 32] = {c[k*16 +: 16], 16'd0};","d[k*32 +: 32] = {c[k*16 +: 16], 16'd0} ^ 32'd1;") if sys.argv[3]=='1' else ("wcnt[q]+8'(w_hit[q])","wcnt[q]-8'(w_hit[q])") if sys.argv[3]=='2' else ("outstanding_n<=~next_outstanding;","outstanding_n<=~next_outstanding ^ (OW+1)'(1);")
assert s.count(a)==1
p=Path(sys.argv[2]);p.write_text(s.replace(a,b));p.with_suffix('.mutation.json').write_text(json.dumps({'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'mutant_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'from':a,'to':b},indent=2))
PY
 pay="$out/mutated_pay.sv"
fi
iverilog -g2012 -s tb_hgi_qdq_wr_pay -Ptb_hgi_qdq_wr_pay.EMPTY_BYPASS="${BYPASS:-0}" -o "$out/sim" rtl/lib/ot_rst_relay.sv rtl/link/ot_fifo_sram_fwft.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v "$pay" rtl/test/hbm_accel/generic/tb_hgi_qdq_wr_pay.sv >"$out/build.log" 2>&1
set +e
vvp "$out/sim" >"$out/run.log" 2>&1
run_rc=$?
set -e
cat "$out/run.log"
exit "$run_rc"
