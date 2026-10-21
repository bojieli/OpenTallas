import concurrent.futures as cf,json,pathlib,re,subprocess
root=pathlib.Path('/srv/opentallas-scratch/claude/closure-loop/dsdv_sh_lk_s10gq-dsdv_sh_lk_s10gq-e316c4132')
out=pathlib.Path('/srv/opentallas-scratch/claude/codex-s81-shlk-benchfix-1021/all_negatives');out.mkdir(exist_ok=True)
src=root/'bench_src_a1'
src=pathlib.Path('/srv/opentallas-scratch/claude/codex-s81-shlk-benchfix-1021/source_1bf')
import os
extra='-DOT_S81_SH_APIPE9 -DOT_S81_SH_APIPE10 -DOT_S81_SH_SRAM -DOT_S81_SH_RSZ -DOT_S81_SH_S10B -DOT_S81_SH_S10C -DOT_S81_SH_S10D -DOT_S81_SH_S10E -DTB_HSH=8'
def unit(m):
 p=out/f'unit_mut{m}.log'; dest=out/f'unit_mut{m}'
 with p.open('w') as f:r=subprocess.run(['bash',str(src/'rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_bench.sh'),str(dest),'1',str(m)],cwd=src,env=dict(os.environ,VL_EXTRA=extra),stdout=f,stderr=subprocess.STDOUT)
 log=dest/f'run_mut{m}.log';text=log.read_text() if log.exists() else p.read_text()
 pat=r'^SEQHOST FAIL( |$)' if m!=7 else r'^SEQHOST FAIL( |$)|Assertion failed.*hx_pop replica diverged'
 return dict(name=f'unit_mut{m}',rc=r.returncode,caught=bool(re.search(pat,text,re.M)),log=str(log))
with cf.ThreadPoolExecutor(max_workers=4) as pool: records=list(pool.map(unit,[1,2,3,4,5,6,7,9,10,14,16,19,23]))
def n32(m):
 p=out/f'n32_{m or "base"}.log';cmd=['bash',str(src/'rtl/hdc/ingest/test/run_n32_lockstep.sh'),str(out/f'n32_{m or "base"}'),'1 2 3' if not m else '1']+([m] if m else [])
 with p.open('w') as f:r=subprocess.run(cmd,cwd=src,stdout=f,stderr=subprocess.STDOUT)
 text=p.read_text();pat=r'^LOCKSTEP_GATE PASS$' if not m else r'^FAIL LOCKSTEP seed=\d+ mismatches=[1-9]|%Fatal: ot_s81_ing_stream_n32\.sv:\d+: Assertion failed'
 return dict(name=f'n32_{m or "base"}',rc=r.returncode,caught=bool(re.search(pat,text,re.M)),log=str(p))
with cf.ThreadPoolExecutor(max_workers=7) as pool:records+=list(pool.map(n32,['','BYP','GOD','WIN','KIND','FQS','CQR']))
(out/'receipt.json').write_text(json.dumps(dict(source='1bf1d11bc',unchanged_rtl=True,records=records,pass_all=all(r['caught'] for r in records)),indent=2)+'\n')
print(json.dumps(records,indent=2),flush=True)
raise SystemExit(0 if all(r['caught'] for r in records) else 1)
