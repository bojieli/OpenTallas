from pathlib import Path
import concurrent.futures,json,subprocess,sys
s=Path(__file__).resolve().parent
p=Path(sys.argv[1]);p.mkdir(parents=True,exist_ok=False)
cmd=['iverilog','-g2012','-s','terminal_policy','-o',str(p/'terminal.vvp'),str(s/'terminal_policy.sv')]
b=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(p/'compile.log').write_text(b.stdout)
if b.returncode:sys.exit(b.returncode)
def one(i):
 r=subprocess.run(['vvp','-n',str(p/'terminal.vvp'),f'+BAD={i}'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (p/f'case_{i}.log').write_text(r.stdout)
 return dict(case=i,returncode=r.returncode,expected_nonzero=i!=0,correct=(r.returncode!=0)==(i!=0))
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:rows=list(pool.map(one,range(13)))
(p/'terminal.json').write_text(json.dumps(dict(scope='new source terminal predicates only; no engine, numerical requalification or historical replay',cases=rows),indent=2)+'\n')
sys.exit(0 if all(r['correct'] for r in rows) else 1)
