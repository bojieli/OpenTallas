#!/bin/bash
set -eu
K=$(cd "$1" && pwd)
docker run --rm --name codex-slang-macro-2144 --memory=2g --memory-swap=2g --cpus=1 -v "$K":/work -w /work openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
for mode in functional blackbox; do
 suffix=""; [ "$mode" = blackbox ] && suffix=_bb
 printf "%s\n" "read_liberty -lib -ignore_miss_func /work/ot_sram_1r1w2c_32x64_m1_tt.lib" "read_slang -D SYNTHESIS --keep-hierarchy --compat=vcs --ignore-assertions --top top --blackboxed-module ot_sram_1r1w2c_32x64_m1 /work/top.sv /work/ot_sram_1r1w2c_32x64_m1${suffix}.v" "hierarchy -check -top top" > "$mode.ys"
 yosys -Q -T -s "$mode.ys" > "$mode.log" 2>&1
 echo "$?" > "$mode.rc"
done
chown -R 1000:1000 /work
'
python3 - "$K" <<'PY'
import pathlib,sys,json
p=pathlib.Path(sys.argv[1]);a=int((p/'functional.rc').read_text());b=int((p/'blackbox.rc').read_text());assert a!=0 and b==0,(a,b)
assert "parameter named 'CB'" in (p/'functional.log').read_text()
(p/'result.json').write_text(json.dumps({'verdict':'MECHANISM_CONFIRMED','functional_source_rc':a,'actual_bb_source_rc':b,'cause':'Slang --blackboxed-module on functional macro attaches localparam CB to the instance; Liberty module has no parameters. Using the actual compiler-generated blackbox declaration preserves ports and avoids the spurious parameter.','scope':'Tiny diagnostic only. Old whole-leaf RQ0 kit obsolete; current bank/pool canonicalization already passed and live jobs are untouched.'},indent=2)+'\n')
print('SLANG_MACRO_REPRO PASS')
PY
