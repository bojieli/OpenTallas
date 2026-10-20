#!/bin/bash
set -uo pipefail
root=/srv/opentallas-scratch/claude/codex-qw-n59-service-r3b-1020
run=$root/resultpub_zero_dv
mkdir -p "$run/src"
tar -xzf "$root/source.tgz" -C "$run/src"
tar -xzf "$root/overlay.tgz" -C "$run/src"
cd "$run/src"
python3 - <<'PYM'
from pathlib import Path
p=Path('rtl/qwen_split/qfd_native59_record_endpoint.sv')
s=p.read_text();a="else q<=rx_result_pub[rc/8]&&slot_back_pub[rc/8];"
assert s.count(a)==1
p.write_text(s.replace(a,"else q<=1'b0;"))
PYM
sha256sum rtl/qwen_split/qfd_native59_record_endpoint.sv > "$run/mutant_source.sha256"
bash results/arch/qw_n59v6_service_1020/bench.sh local_dv "$run/out" > "$run/bench.log" 2>&1
rc=$?
if test "$rc" != 0 && grep -Eq 'N59(DV|MU)_FAIL' "$run/out/wrapper.log"; then
 echo N59_RESULTPUB_MUTANT_REJECTED > "$run/DONE"; cat "$run/DONE"; exit 0
fi
echo "N59_RESULTPUB_MUTANT_UNEXPECTED rc=$rc" > "$run/DONE"; cat "$run/DONE"; exit 1
