# QW-LANDW3 behavioural witnesses of the RSL=1 masters on Verilator 5.050: pass + 8 mutants (incl. new rsl) x 4 masters.
import pathlib,subprocess,concurrent.futures,json
r=pathlib.Path.cwd();out=r/'results/arch/qw_landw3_rst_1020/bench';work=r/'bench_work';out.mkdir(parents=True,exist_ok=True)
M=[('qfd_landh0d8g_107_EW_52x52',107),('qfd_landh0d8gn_107_EW_52x52',107),('qfd_landh0d8g_116_EW_52x52',116),('qfd_landh0d8gn_116_EW_52x52',116)]
jobs=[(m,w,x) for m,w in M for x in ['pass','sel','naive','vld','encomb','k3','wsel','rsel','rsl']]
def run(j):
 m,w,mode=j;log=out/f'{m}_{mode}.log'
 with log.open('w') as f:r0=subprocess.run(['bash','tools/qwen_split/bench_land8f.sh',mode,str(work/f'{m}_{mode}'),m,str(w),'flop'],stdout=f,stderr=subprocess.STDOUT)
 t=log.read_text();e='LAND8_BENCH_ALL '+('PASS' if mode=='pass' else 'FAIL')
 x=dict(master=m,width=w,mode=mode,rc=r0.returncode,expected=e,seen=e in t,qualified=(r0.returncode==(0 if mode=='pass' else 1) and e in t));print(x,flush=True);return x
with concurrent.futures.ThreadPoolExecutor(12) as ex:rows=list(ex.map(run,jobs))
(out/'summary.json').write_text(json.dumps(rows,indent=1)+'\n');ok=all(x['qualified'] for x in rows);print('LANDW3_BENCH',('PASS' if ok else 'FAIL'),sum(x['qualified'] for x in rows),'/',len(rows));raise SystemExit(0 if ok else 1)
