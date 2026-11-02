#!/usr/bin/env python3
"""Prepare read-only capture from a TERMINAL passing native HEAD component.

No native Verilator regeneration or RTL recompilation is performed. The finite
SV bench, timing loop, actual model archive, genuine masks and checked gold stay
unchanged. A new C++ main only records the real raw-valid counter and output.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--passed-runtime',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();old=a.passed_runtime.resolve();obj=old/'obj'
    if 'PASS_NATIVE_HEAD_LEAF_RAW_COMPONENT' not in (old/'status').read_text():
        raise ValueError('terminal native baseline and wrong-weight PASS required before capture')
    if 'NATIVE_HEAD_LEAF_PASS' not in (old/'baseline.log').read_text():
        raise ValueError('native final-K canonical comparison PASS absent')
    if 'actual=c32f0600 expected=c3312600' not in (old/'wrong_weight.log').read_text():
        raise ValueError('causal wrong-weight result absent')
    files=[obj/n for n in ['Vtb_native_head_leaf__ALL.a','verilated.o','verilated_timing.o','verilated_threads.o']]
    files+=sorted(obj.glob('*.h'))
    if any(not f.is_file()for f in files):raise ValueError('passing native model library incomplete')
    a.out.mkdir(parents=True,exist_ok=False)
    for n in ['data','rom']:shutil.copytree(old/n,a.out/n)
    driver=Path(__file__).with_name('capture_native_head_prefixes.cpp')
    shutil.copy2(driver,a.out/driver.name)
    guards={str(f):sha(f)for f in files}
    (a.out/'model.sha256').write_text(''.join(h+'  '+n+'\n'for n,h in guards.items()))
    manifest=dict(status='PREP_ONLY_NO_DISPATCH',passed_runtime=str(old),passed_status_sha256=sha(old/'status'),
        checked_gold_scope='200finalK7vectors/3200values and wrongweight source-control',
        capture_scope='1600actualrawKprefixvectors/25600FP32words from unmodified native model; no full512split or post/STN claim',
        entry_policy='GNUld wraps only CRT main entry; original grouped model archive remains byte-identical',
        model_inputs=guards,driver_sha256=sha(driver),
        holds=['parent finite readset/resource review before normal compile/link/replay',
               'passed model library must remain immutable; no active cache mutation',
               'all timestamps are original component TEST_ONLY times, not global clock/calendar epochs'])
    (a.out/'preparation.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # This command compiles only the observer main and links existing native
    # model/runtime objects. Library inputs are read-only and hash-guarded.
    script='''#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")"
sha256sum -c packet.sha256 >input_guard.log 2>&1 || exit 3
sha256sum -c model.sha256 >model_guard.log 2>&1 || exit 4
obj_dir=MODEL_OBJECT_DIRECTORY
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
/usr/bin/time -v -o link.time /usr/bin/g++ -fcoroutines -O0 -w -fno-var-tracking -DVERILATOR=1 -DVM_TIMING=1 -DVM_SC=0 -DVM_COVERAGE=0 -DVM_TRACE=0 -DVM_TRACE_FST=0 -DVM_TRACE_VCD=0 -DVM_TRACE_SAIF=0 -DVM_VPI=0 -DVL_TIME_CONTEXT -I"$obj_dir" -I"$vroot/include" -I"$vroot/include/vltstd" capture_native_head_prefixes.cpp "$obj_dir/verilated.o" "$obj_dir/verilated_timing.o" "$obj_dir/verilated_threads.o" "$obj_dir/Vtb_native_head_leaf__ALL.a" -pthread -latomic -Wl,--wrap=main -o capture_native_head_prefixes >link.log 2>&1
link_rc=$?;printf 'LINK_RC=%s\\n' "$link_rc" >status
[ "$link_rc" = 0 ] || exit "$link_rc"
/usr/bin/time -v -o replay.time ./capture_native_head_prefixes +OT_ROM_DIR=rom >replay.log 2>&1
run_rc=$?;printf 'REPLAY_RC=%s\\n' "$run_rc" >>status
[ "$run_rc" = 0 ] && grep -q CAPTURE_ACTUAL_NATIVE_PREFIXES_PASS replay.log && grep -q NATIVE_HEAD_LEAF_PASS replay.log || exit 5
printf 'PASS_NATIVE_PREFIX_CAPTURE\\n' >>status
'''
    # Explicit shell quoting for an absolute path, never JSON-string-as-shell.
    quoted="'"+str(obj).replace("'","'\\''")+"'"
    (a.out/'run_capture.sh').write_text(script.replace('MODEL_OBJECT_DIRECTORY',quoted))
    (a.out/'packet.sha256').write_text(''.join(sha(f)+'  '+str(f.relative_to(a.out))+'\n'for f in sorted(a.out.rglob('*'))if f.is_file()))
    print(json.dumps(dict(status=manifest['status'],model_files=len(files),native_rebuild=False,actual_prefix_vectors=1600)))


if __name__=='__main__':main()
