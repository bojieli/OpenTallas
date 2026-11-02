#!/usr/bin/env bash
# Parent review/admission required; source_dir is the TERMINAL packet3 run.
set -uo pipefail
cd "$(dirname "$0")"
source_dir=${1:?terminal packet3 directory required}
sha256sum -c packet.sha256 >input_guard.log 2>&1 || exit 3
python3 prepare_mutant.py >prepare.log 2>&1 || exit 4
python3 - "$source_dir" <<'PY'
from pathlib import Path
import hashlib,json,sys
old=Path(sys.argv[1]).resolve();new=Path.cwd()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(old/'packet.sha256')=='0173eabd386340f4e9ce21c8d87479261eb7346d94667221c646c97751604da1'
assert (old/'obj/Vtb_native_head_leaf').is_file()
s=(old/'baseline.log').read_text();assert 'actual=c3174c00 expected=c3312600' in s
for parent in ['src','rom','data']:
 for p in (new/parent).iterdir():assert p.is_file()and sha(p)==sha(old/parent/p.name),(parent,p.name)
out=new/'gate1_preserved';out.mkdir()
for src,dst in [(old/'obj/Vtb_native_head_leaf',out/'Vtb_native_head_leaf.gate1'),(old/'baseline.log',out/'baseline.log'),(old/'build.log',out/'build.log'),(old/'packet.sha256',out/'packet.sha256')]:dst.write_bytes(src.read_bytes())
(out/'receipt.json').write_text(json.dumps(dict(source=str(old),source_packet_sha256=sha(old/'packet.sha256'),elf_sha256=sha(old/'obj/Vtb_native_head_leaf'),baseline_sha256=sha(old/'baseline.log'),native_input_identity='allsrc/rom/datafilesbyteidentical',old_run_mutated=False),indent=2)+'\n')
PY
[ "$?" = 0 ] || exit 5
# Reflink where supported, otherwise copy. Never hardlink or edit old obj/ELF.
cp -a --reflink=auto "$source_dir/obj" obj || exit 6
python3 - <<'PY'
from pathlib import Path
import hashlib,json
p=Path('obj');d={x.name:hashlib.sha256(x.read_bytes()).hexdigest()for x in p.iterdir()if x.suffix in ('.cpp','.h','.o')};Path('cache_before.json').write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')
PY
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
export CXX=/usr/bin/g++
"$VL" --version >toolchain.log
/usr/bin/g++ --version >>toolchain.log
printf 'START host=%s\n' "$(hostname -s)" >status
# Regenerate source first, then incremental make. Same native RTL/shape/gold.
/usr/bin/time -v -o generate.time "$VL" --cc --exe --main --timing -O0 -finline --output-groups 16 -j 1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -CFLAGS '-O0 -w -fno-var-tracking' --top-module tb_native_head_leaf -f source.f native_tile0_cut.sv tb_native_head_leaf.sv --Mdir obj >generate.log 2>&1
rc=$?;echo "GENERATE_RC=$rc" >>status
[ "$rc" = 0 ] || exit "$rc"
python3 - <<'PY'
from pathlib import Path
import hashlib,json
old=json.loads(Path('cache_before.json').read_text());d={x.name:hashlib.sha256(x.read_bytes()).hexdigest()for x in Path('obj').iterdir()if x.suffix in('.cpp','.h')};r=dict(same=[n for n,h in d.items()if old.get(n)==h],changed=[n for n,h in d.items()if old.get(n)!=h]);Path('regeneration_delta.json').write_text(json.dumps(r,indent=2)+'\n')
PY
/usr/bin/time -v -o make.time make -C obj -f Vtb_native_head_leaf.mk -j 1 >make.log 2>&1
rc=$?;echo "MAKE_RC=$rc" >>status
[ "$rc" = 0 ] || exit "$rc"
/usr/bin/time -v -o baseline.time ./obj/Vtb_native_head_leaf +OT_ROM_DIR=rom >baseline.log 2>&1
rc=$?;echo "BASELINE_RC=$rc" >>status
[ "$rc" = 0 ] && grep -q NATIVE_HEAD_LEAF_PASS baseline.log || exit 1
/usr/bin/time -v -o wrong_weight.time ./obj/Vtb_native_head_leaf +OT_ROM_DIR=rom_wrong_weight >wrong_weight.log 2>&1
rc=$?;echo "WRONG_WEIGHT_RC=$rc" >>status
[ "$rc" != 0 ] && grep -q 'actual=c32f0600 expected=c3312600' wrong_weight.log || exit 2
echo PASS_NATIVE_HEAD_LEAF_RAW_COMPONENT >>status
