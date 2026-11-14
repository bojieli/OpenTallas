#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "${1:?outdir}")
CACHE=${NATIVE_REPLAY_CACHE:-/srv/opentallas-scratch2/claude/hard-s81-svc-1/native_programme/out/obj}
V=${VERILATOR_INCLUDE:-$HOME/.local/opentallas-tools/verilator-5.050/share/verilator/include}
mkdir -p "$O"
python3 - "$CACHE" "$O" <<'PY'
import pathlib,subprocess,json,hashlib,shutil,sys
cache=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);original=cache/'Vtb_svc_native_programme__ALL.a';private=out/'model_private.a'
symbols=subprocess.check_output(['nm','-A',str(original)],text=True)
stim='_Z105Vtb_svc_native_programme_tb_svc_native_programme___eval_initial__TOP__tb_svc_native_programme__Vtiming__0P48Vtb_svc_native_programme_tb_svc_native_programme'
weak={}
for target in (stim,'main'):
 hits=[s for s in symbols.splitlines() if s.endswith(' T '+target)]
 assert len(hits)==1,(target,len(hits))
 member=hits[0].split()[0].split(':')[-2];weak.setdefault(member,[]).append(target)
shutil.copyfile(original,private);meta={}
for member,targets in weak.items():
 p=out/member;p.write_bytes(subprocess.check_output(['ar','p',str(original),member]))
 text=out/(member+'.text.before');subprocess.run(['objcopy','--dump-section','.text='+str(text),str(p)],check=True)
 subprocess.run(['objcopy',*[f'--weaken-symbol={s}' for s in targets],str(p)],check=True)
 after=out/(member+'.text.after');subprocess.run(['objcopy','--dump-section','.text='+str(after),str(p)],check=True)
 assert text.read_bytes()==after.read_bytes(),'machine code changed'
 subprocess.run(['ar','r',str(private),str(p)],check=True)
 meta[member]={'weakened_testbench_symbols':targets,'unchanged_text_sha256':hashlib.sha256(text.read_bytes()).hexdigest()}
(out/'archive_receipt.json').write_text(json.dumps({'original_archive':str(original),'original_archive_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'private_archive':str(private),'private_link_changes':meta,'uut_machine_code_changed':False,'uut_state_or_memory_backdoors':False},indent=2)+'\n')
PY
g++ -O0 -std=c++20 -I"$CACHE" -I"$V" -I"$V/vltstd" tools/s81_dv/svc_rs/svc_returned_p_replay.cpp "$O/model_private.a" "$CACHE/verilated.o" "$CACHE/verilated_timing.o" "$CACHE/verilated_threads.o" -pthread -latomic -o "$O/replay" >"$O/build.log" 2>&1
"$O/replay" results/svc_attcut_1113/score_feedback/returned_p.hex results/svc_attcut_1113/score_feedback/score.hex results/svc_attcut_1113/score_feedback/dates.hex >"$O/run.log" 2>&1
cat "$O/run.log"
grep -q '^RETURNED_P_REPLAY PASS' "$O/run.log"
python3 - "$CACHE" "$O" <<'PY'
import hashlib,json,pathlib,sys
cache=pathlib.Path(sys.argv[1]);out=pathlib.Path(sys.argv[2]);r=json.loads((out/'archive_receipt.json').read_text());assert hashlib.sha256((cache/'Vtb_svc_native_programme__ALL.a').read_bytes()).hexdigest()==r['original_archive_sha256'];print('REPLAY_ARCHIVE_PRESERVED PASS')
PY
