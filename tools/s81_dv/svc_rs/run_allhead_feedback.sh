#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "${1:?outdir}")
ROWS=${ROWS:-32}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/dsrom_sys/s81_dv/svc_rs
SX_CACHE=${SX_PROTECTED_CACHE:-/srv/opentallas-scratch2/claude/hard-s81-svc-1/score_feedback/out/pl}
SM_CACHE=${SM_PROTECTED_CACHE:-$O/sm_pl}
mkdir -p "$O"
python3 - "$O" "$ROWS" <<'PY'
import pathlib,re,json,sys,hashlib
out=pathlib.Path(sys.argv[1]);rows=int(sys.argv[2]);assert rows in (32,128)
src=pathlib.Path('results/svc_attcut_1113/native_programme');assert json.loads((src/'oracle.json').read_text())['status']=='PASS'
m=re.search(r'^SCORE case0 relative77 row0 payload([0-9a-f]+) flags00000000$',(src/'run.log').read_text(),re.M);assert m
raw=int(m.group(1),16);base=[(raw>>(32*k))&0xffffffff for k in range(32)]
for hb in (0,1):
 lines=[]
 for b in range(rows//4):
  data=sum((x if hb==0 else x-(2<<23))<<(32*k) for k,x in enumerate(base))
  word=((4*b)<<1060)|(15<<1056)|(data<<32);lines.append(f'{word:0269x}')
 (out/f'score_hb{hb}.hex').write_text('\n'.join(lines)+'\n')
(out/'dates.hex').write_text('\n'.join(f'{77+b:08x}' for b in range(rows//4))+'\n')
(out/'source_candidates.json').write_text(json.dumps({'source_commit':'4b3430fb52','rows':rows,'hb0':'original actualnative scorevector, repeated only overidentical all-one rows','hb1':'independent exact quarter-scale expectedsource, freshnative comparison REQUIRED beforeclosedchain claim','candidate_dates':'phase1 fixedproducer77..77+rows/4-1; freshnative comparison REQUIRED','closure_pending':True,'oracle':'uniformperrow; gain2^-8,sink−32 < eachscaledscore, so SEe=exp0=1','pio':800,'source_original_sha256':hashlib.sha256((src/'run.log').read_bytes()).hexdigest()},indent=2)+'\n')
PY
COMMON=(-DOT_SVC_H8 -DOT_SVC_NATIVE_RT2_CALENDAR -DSU_SMU_T -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -I"$D" --output-split 20000 --output-split-cfuncs 2000 -fno-inline --unroll-count 16 --unroll-limit 131072 -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O0)
source tools/s81_dv/svc_rs/rs_files.sh
if [[ ! -f $SM_CACHE/libot_s81_su_sms_fold2_pl.a ]];then
 "$VL" --cc --build -j 4 --protect-lib ot_s81_su_sms_fold2_pl --top-module ot_s81_su_sms_fold2 -Mdir "$SM_CACHE" "${COMMON[@]}" "${RS_SRC[@]}" "${RS_LIB[@]}" >"$O/build_sm_lib.log" 2>&1
fi
"$VL" --binary --timing --top-module tb_svc_allhead_feedback -Mdir "$O/obj" -j 4 "${COMMON[@]}" "${RS_SRC[@]}" "${RS_LIB[@]}" "$SX_CACHE/dsdv_svc_sx_pl.sv" "$SX_CACHE/libdsdv_svc_sx_pl.a" "$SM_CACHE/ot_s81_su_sms_fold2_pl.sv" "$SM_CACHE/libot_s81_su_sms_fold2_pl.a" "$D/dsdv_svc_mem_ar.sv" physical/asap7_memory_macros_v2/ot_sram_1r1w_160x256_m1_r0c0/ot_sram_1r1w_160x256_m1_r0c0.v physical/asap7_memory_macros_v2/ot_sram_1r1w_32x128_m1_r0c0/ot_sram_1r1w_32x128_m1_r0c0.v "$D/test/tb_svc_allhead_feedback.sv" >"$O/build_top.log" 2>&1
for hb in 0 1;do
 "$O/obj/Vtb_svc_allhead_feedback" +scores="$O/score_hb$hb.hex" +dates="$O/dates.hex" +hb=$hb +rows=$ROWS >"$O/run_hb$hb.log" 2>&1
 grep -E '^ALLHEAD_(HEAD|COUNTS|DATES|FEEDBACK)' "$O/run_hb$hb.log"
 grep -q '^ALLHEAD_FEEDBACK PASS' "$O/run_hb$hb.log"
done
python3 - "$O" "$ROWS" <<'PY'
import pathlib,sys,re
out=pathlib.Path(sys.argv[1]);rows=int(sys.argv[2]);expected=int('3f80'*32,16)
for hb in (0,1):
 text=(out/f'run_hb{hb}.log').read_text();words=re.findall(r'^ALLHEAD_P_WORD hb\d+ rows\d+ cycle(\d+) index(\d+) data([0-9a-f]+)',text,re.M);assert len(words)==rows//4
 assert all(int(i)==j and int(d,16)==expected for j,(c,i,d) in enumerate(words))
 (out/f'returned_hb{hb}.hex').write_text('\n'.join(d for c,i,d in words)+'\n')
print('ALLHEAD_RETURN_PACKET_ORACLE PASS')
PY
