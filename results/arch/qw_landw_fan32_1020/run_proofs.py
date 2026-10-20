import pathlib,subprocess,concurrent.futures,json
r=pathlib.Path.cwd();out=r.parent/'proof_final';out.mkdir(exist_ok=True)
jobs=[(m,w,mode) for m,w in [('qfd_landh0d8f_107_EW_52x52',107),('qfd_landh0d8f_116_EW_54x54',116),('qfd_landh0d8fn_107_EW_52x52',107),('qfd_landh0d8fn_116_EW_54x54',116)] for mode in ['pass','sel','naive','vld','encomb','k3','wsel','rsel']]
def run(j):
 m,w,mode=j;p=out/(m+'_'+mode);log=out/(p.name+'.log')
 with log.open('w') as f:r0=subprocess.run(['bash','tools/qwen_split/bench_land8f.sh',mode,str(p),m,str(w),'flop'],stdout=f,stderr=subprocess.STDOUT)
 text=log.read_text();expected='LAND8_BENCH_ALL '+('PASS'if mode=='pass'else'FAIL');x=dict(master=m,width=w,mode=mode,rc=r0.returncode,expected_regex=expected,expected_seen=expected in text,qualified=(r0.returncode==(0 if mode=='pass'else 1) and expected in text));print(x,flush=True);return x
with concurrent.futures.ThreadPoolExecutor(max_workers=6)as ex:rows=list(ex.map(run,jobs))
(out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n');raise SystemExit(0 if all(x['qualified']for x in rows)else 1)
