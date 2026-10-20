import hashlib,json,re,subprocess,tempfile
from pathlib import Path
R=Path.cwd();fix=R/'cand/tools/ref_tile/tests/fixtures/hc_tree16_wrapper';spec=json.loads(Path('hc_spec.json').read_text());benches={b['name']:b for b in spec['job']['benches']};result={}
for side in ('old','new'):
 body=(fix/(side+'.sh')).read_text();commands='\n'.join(line for line in body.splitlines() if line.startswith('grep '))
 for name,raw in [('qtree16_exact','original_positive.log'),('qtree16_mut4','original_mutant.log')]:
  with tempfile.TemporaryDirectory() as td:
   Path(td,'run.log').write_bytes(Path(raw).read_bytes());p=subprocess.run(['bash','-euo','pipefail','-c','out=$1\n'+commands,'terminal-replay',td],capture_output=True,text=True)
  bench=benches[name];pattern=bench['pass_regex'] if bench['expect']=='pass' else bench['fail_regex'];matched=bool(re.search(pattern,p.stdout,re.M))
  assert p.returncode==(0 if bench['expect']=='pass' else 1),(side,name,p.returncode)
  assert matched==(side=='new' or bench['expect']=='pass'),(side,name,p.stdout)
  result[side+'/'+name]={'returncode':p.returncode,'regex':pattern,'matched':matched,'stdout':p.stdout,'raw_sha256':hashlib.sha256(Path(raw).read_bytes()).hexdigest(),'extracted_literal_grep_commands':commands}
Path('terminal_replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
