#!/usr/bin/env bash
# Exercise the sequencer embedded in the actual native body, not a generated substitute.
set -euo pipefail
out=${1:?output directory required}
mkdir -p "$out"
sources=(rtl/test/qwen_seq_addr/tb_qwen_seq_addr.sv rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su_bi.sv rtl/hdc/ot_hdc_delay.sv)
run() {
    local name=$1 expectation=$2; shift 2
    iverilog -g2012 -s tb_qwen_seq_addr -o "$out/$name.vvp" "$@" "${sources[@]}" > "$out/$name.compile.log" 2>&1
    local result=0
    vvp "$out/$name.vvp" > "$out/$name.log" 2>&1 || result=$?
    if [[ $expectation == pass ]]; then
        [[ $result == 0 ]] && grep -q '^PASS ' "$out/$name.log"
    else
        [[ $result != 0 ]] && grep -q 'row truncation\|FAIL tp_seq_vrl' "$out/$name.log"
    fi
    printf '%s expected=%s result=%s\n' "$name" "$expectation" "$result"
    rm "$out/$name.vvp"
}
run row256 pass
run cross_low8 pass -P tb_qwen_seq_addr.VW0=745728
run ar256 pass -P tb_qwen_seq_addr.VW0=4096 -P tb_qwen_seq_addr.NWORDS=256
run upper_boundary pass -P tb_qwen_seq_addr.VW0=1048536
run overflow_fence pass -P tb_qwen_seq_addr.VW0=1048540 -P tb_qwen_seq_addr.FENCE=1
run legacy_address pass -P tb_qwen_seq_addr.VW0=16
run truncate_mutant fail -P tb_qwen_seq_addr.TRUNC=1
run read_latency_mutant fail -P tb_qwen_seq_addr.VRL=6
# The range fence mutant must cause a real read/address mismatch, never a nominal rejection.
python3 - "$out/fence_mutant.sv" <<'PY'
import sys
from pathlib import Path
s=Path('rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su_bi.sv').read_text()
s=s.replace('descriptor_end > (21\'d1 << VWA)', '1\'b0')
Path(sys.argv[1]).write_text(s)
PY
iverilog -g2012 -s tb_qwen_seq_addr -P tb_qwen_seq_addr.VW0=1048540 -P tb_qwen_seq_addr.FENCE=1 -o "$out/fence_mutant.vvp" rtl/test/qwen_seq_addr/tb_qwen_seq_addr.sv "$out/fence_mutant.sv" rtl/hdc/ot_hdc_delay.sv > "$out/fence_mutant.compile.log" 2>&1
if vvp "$out/fence_mutant.vvp" > "$out/fence_mutant.log" 2>&1; then
    echo 'ERROR range fence mutant passed'; exit 1
fi
grep -q 'row truncation\|FAIL tp_seq_vrl' "$out/fence_mutant.log"
rm "$out/fence_mutant.vvp" "$out/fence_mutant.sv"
sha256sum "${sources[@]}" rtl/qwen_split/qfd_seq_su.sv tools/hdc_qwen_fullshape_isa_w12.py > "$out/sources.sha256"
echo 'PASS native20 row descriptors, production 7-edge path, writeback and rejecting fences; 3 mutants failed'
