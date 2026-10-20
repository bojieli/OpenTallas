#!/bin/bash
set -uo pipefail
root=/srv/opentallas-scratch/claude/qw-cb16a0-n59r3c-1020
run=$root/kreqpub_zero
mkdir -p "$run/src"
tar -xzf "$root/source.tgz" -C "$run/src"
tar -xzf "$root/overlay.tgz" -C "$run/src"
cd "$run/src"
python3 - <<'PYM'
from pathlib import Path
p=Path('rtl/qwen_split/qfd_native59_static_service.sv')
s=p.read_text();a="""else q<=kreq_d;"""
assert s.count(a)==1,s.count(a)
p.write_text(s.replace(a,"""else q<=(c==0)?1'b0:kreq_d;"""))
PYM
sha256sum rtl/qwen_split/qfd_native59_static_service.sv > "$run/mutant_source.sha256"
bash results/arch/qw_n59v6_service_1020/bench.sh local_dv "$run/out" > "$run/bench.log" 2>&1
rc=$?
if test "$rc" != 0 && grep -Eq 'N59(DV|MU)_FAIL' "$run/out/wrapper.log"; then
 echo N59_R3C_KREQPUB_ZERO_MUTANT_REJECTED > "$run/DONE"; cat "$run/DONE"; exit 0
fi
echo "N59_R3C_KREQPUB_ZERO_MUTANT_UNEXPECTED rc=$rc" > "$run/DONE"; cat "$run/DONE"; exit 1
