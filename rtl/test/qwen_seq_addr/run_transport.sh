#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory}; mkdir -p "$out"
sources=(rtl/test/qwen_seq_addr/tb_qwen_seq_row_transport.sv rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su_bi.sv rtl/hdc/ot_hdc_delay.sv)
run() {
    local tag=$1 expect=$2; shift 2
    iverilog -g2012 -s tb_qwen_seq_row_transport -o "$out/$tag.vvp" "$@" "${sources[@]}" > "$out/$tag.compile.log" 2>&1
    local code=0
    vvp "$out/$tag.vvp" > "$out/$tag.log" 2>&1 || code=$?
    if [[ $expect == pass ]]; then [[ $code == 0 ]] && grep -q '^PASS ' "$out/$tag.log";
    else [[ $code != 0 ]] && grep -q 'FAIL tp_seq_vrl' "$out/$tag.log"; fi
    cat "$out/$tag.log"; rm "$out/$tag.vvp"
}
run static_native256 pass -P tb_qwen_seq_row_transport.CRDY=0
run static_backpressure pass
run elastic_recovery pass -P tb_qwen_seq_row_transport.VARIABLE=1
run early_response fail -P tb_qwen_seq_row_transport.MUT=1
run missing_response fail -P tb_qwen_seq_row_transport.MUT=2
run wrong_response_cycle fail -P tb_qwen_seq_row_transport.VRL=18
run response_order fail -P tb_qwen_seq_row_transport.MUT=3
python3 - "$out" <<'PYCODE'
import sys,re,json
from pathlib import Path
root=Path(sys.argv[1])
a=(root/'static_native256.log').read_text(); b=(root/'static_backpressure.log').read_text()
assert a == b, 'runtime c_ready altered native schedule'
issues=[int(x) for x in re.findall(r'TIMELINE issue=\d+ row=\d+ cycle=(\d+)',a)]
responses=[int(x) for x in re.findall(r'TIMELINE response=\d+ cycle=(\d+)',a)]
assert len(issues)==len(responses)==256
assert all(y-x==19 for x,y in zip(issues,responses))
(root/'schedule.json').write_text(json.dumps(dict(rows=256,round_trip=19,collective_cycles=544,ready_independent=True,issues=issues,responses=responses),indent=2)+'\n')
PYCODE
sha256sum "${sources[@]}" > "$out/sources.sha256"
echo 'PASS scheduled native row transport and exceptional recovery; four observed failing mutants'
