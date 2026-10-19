import subprocess,json,hashlib,resource,time,os
from pathlib import Path
p=Path('.')
def run(name,station,adapter,expect):
 d=p/name;d.mkdir(exist_ok=True)
 (d/'station.v').write_text(station);(d/'adapter.v').write_text(adapter)
 b=subprocess.run(['iverilog','-g2012','-s','bench','-o',str(d/'sim'),str(d/'station.v'),str(d/'adapter.v'),'bench.v'],capture_output=True,text=True)
 assert b.returncode==0,b.stderr
 q=subprocess.run(['vvp',str(d/'sim')],capture_output=True,text=True)
 (d/'witness.log').write_text(b.stdout+b.stderr+q.stdout+q.stderr)
 assert (q.returncode==0)==expect,(name,q.returncode,q.stdout)
 if not expect:assert 'FUNCTIONAL_FAIL' in q.stdout
 return {'name':name,'rc':q.returncode,'witness_sha256':hashlib.sha256((d/'witness.log').read_bytes()).hexdigest()}
s=p.joinpath('station.v').read_text();a=p.joinpath('native_equation_adapter.v').read_text();t=time.time()
r=[run('baseline',s,a,True),run('mut_inverted_QN',s,a.replace('assign QN=IQN','assign QN=~IQN'),False),run('mut_missing_stage',s.replace('.D(d2)','.D(hi)'),a,False),run('mut_clock_only_assertion',s,a.replace(' or negedge RESETN or negedge SETN',''),False),run('mut_ownership',s.replace('.RESETN(reset_in_n)',".RESETN(1'b1)"),a,False)]
Path('simulation_receipt.json').write_text(json.dumps({'status':'FUNCTIONAL_PASS_PHYSICAL_PHASE_HOLD','runs':r,'wall_s':time.time()-t,'child_maxrss_kb':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'tool':subprocess.run(['iverilog','-V'],capture_output=True,text=True).stdout.splitlines()[0]},indent=2))
print(json.dumps(r));print('rss_kb',resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
