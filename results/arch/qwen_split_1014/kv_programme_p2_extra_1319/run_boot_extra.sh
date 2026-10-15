#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
iverilog -g2012 -s tb_qkd_kv_native_programme -Ptb_qkd_kv_native_programme.MUT=0 -Ptb_qkd_kv_native_programme.BAD=0 -o out/m0.sim ot_rst_relay.sv qkd_kv_native_programme.sv qkd_kv_static_writer.sv ot_qkd_kv_static_writer_native.sv tb_qkd_kv_native_programme.sv >out/m0.compile.log 2>&1
vvp out/m0.sim >out/m0.log 2>&1
grep -q '^PASS programme+native_writer all36 two_tokens' out/m0.log
cat out/m0.log
python3 - <<'BOOT'
import pathlib,subprocess
r=pathlib.Path('.').resolve();words=[int(s,16) for s in (r/'boot.hex').read_text().split()]
cases={'early_t0':(0,3),'nonascending_t1':(1,words[0]),'nonascending_t2':(2,words[1]),'nonascending_t3':(3,words[2]),'short_stop':(4,words[3]+2),'high_payload':(0,words[0]|(1<<32)),'seal':(180,words[180]^1)}
for n,(i,v) in cases.items():
 p=r/'out'/n;p.mkdir();ws=words.copy();ws[i]=v;(p/'boot.hex').write_text(''.join(f'{w:016x}\n' for w in ws))
 q=subprocess.run(['vvp',str(r/'out/m0.sim')],cwd=p,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (p/'run.log').write_text(q.stdout)
 assert q.returncode!=0 and 'configuration failed' in q.stdout,(n,q.returncode,q.stdout[-500:])
 print('PASS refused boot value',n,'rc',q.returncode)
BOOT
