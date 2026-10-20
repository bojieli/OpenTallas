#!/bin/bash
set -uo pipefail
root=/srv/opentallas-scratch/claude/codex-qw-n59-service-r3-1020
run=$root/selector_mut
mkdir -p "$run/src"
tar -xzf "$root/source.tgz" -C "$run/src"
tar -xzf "$root/overlay.tgz" -C "$run/src"
cd "$run/src"
python3 - <<'PYM'
from pathlib import Path
p=Path('rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv')
s=p.read_text();a="else sel<=4'b0001<<word_index_pub[2*(wb/8)+:2];"
assert s.count(a)==1
p.write_text(s.replace(a,"else sel<=4'b0001<<(word_index_pub[2*(wb/8)+:2] ^ 2'(wb==0));"))
PYM
sha256sum rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv > "$run/mutant_source.sha256"
bash results/arch/qw_n59v6_service_1020/bench.sh local_rnd "$run/out" > "$run/bench.log" 2>&1
rc=$?
if test "$rc" != 0 && grep -Eq 'N59(DV|MU)_FAIL' "$run/out/wrapper.log"; then
 echo N59_SELECTOR_MUTANT_REJECTED > "$run/DONE"; cat "$run/DONE"; exit 0
fi
echo "N59_SELECTOR_MUTANT_UNEXPECTED rc=$rc" > "$run/DONE"; cat "$run/DONE"; exit 1
