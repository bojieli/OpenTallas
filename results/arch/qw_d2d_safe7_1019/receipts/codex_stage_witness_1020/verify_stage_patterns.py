import ast,argparse,hashlib,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--closure-script',type=Path,required=True);a=ap.parse_args()
ROOT=Path(__file__).resolve().parents[5];HERE=Path(__file__).resolve().parent
source=a.closure_script.read_text();tree=ast.parse(source);nodes=[]
for n in tree.body:
 if isinstance(n,ast.FunctionDef) and n.name in ('expected_fail_seen','bench_crashed'):nodes.append(n)
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('RESOURCE_RE','BENCH_CRASH_RC','WORK_RE') for t in n.targets):nodes.append(n)
ns={'re':re};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(a.closure_script),'exec'),ns)
def accepted(st,rc,txt):return not ns['bench_crashed'](st,rc,txt) and ns['expected_fail_seen'](st,rc,txt)
j=json.loads((ROOT/'physical/ref_tile/qfd_d2d_static_sf7w/job.json').read_text());old='^XQ_FAIL errors=[1-9][0-9]*$';records=[]
for st in j['stages']['bench']:
 if st['name'] not in ('xsf7_mut_c0_late','xsf7_mut_bypass_age','xsf7_mut_ohtwin'):continue
 raw=(ROOT/st['fail_witness']).read_text();lines=raw.splitlines()
 # Exact presentation in run_xdie_exchange_sf7.sh lines116/117: selected records, then first3errors, indented4spaces.
 selected=[x for x in lines if re.match(r'^XQ_(E|CFG|PASS|FAIL|CAUSE|FIN)',x)]
 selected += [x for x in lines if x.startswith('XQ_ERR')][:3]
 staged=''.join('    '+x+'\n' for x in selected)
 (HERE/(st['name']+'.staged_from_witness.log')).write_text(staged)
 assert re.search(old,raw,re.M) and not re.search(old,staged,re.M)
 assert accepted(st,1,raw) and accepted(st,1,staged)
 errs=re.findall(r'^XQ_ERR.*$',raw,re.M);assert errs and re.search(r'^XQ_FAIL errors=[1-9][0-9]*$',raw,re.M)
 records.append({'name':st['name'],'raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'staged_sha256':hashlib.sha256(staged.encode()).hexdigest(),'raw_and_staged_match':True,'causal_first_errors':errs[:3]})
assert len(records)==3
st=next(x for x in j['stages']['bench'] if x['name']=='xsf7_mut_c0_late');actual=(HERE/'bench_xsf7_mut_c0_late.a2b1.log').read_text();rc=int((HERE/'bench_xsf7_mut_c0_late.a2b1.rc').read_text().strip());assert rc==1 and accepted(st,rc,actual) and not re.search(old,actual,re.M)
assert accepted(st,1,'\tXQ_FAIL errors=1\n')
negatives=[(1,'XQ_FAIL errors=0\n'),(1,'    XQ_FAIL errors=0\n'),(1,'XQ_PASS layers=35\n'),(1,'OTHER_FAIL errors=699\n'),(1,'prefixXQ_FAIL errors=699\n'),(1,'error: compile failed\n'),(137,'    XQ_FAIL errors=699\nKilled\n'),(1,'    XQ_FAIL errors=699\nCannot allocate memory\n')]
for rc,txt in negatives:assert not accepted(st,rc,txt),(rc,txt)
report={'status':'PASS_NARROW_HORIZONTAL_WHITESPACE_ONLY','actual_c0_stage_rc':1,'actual_c0_stage_sha256':hashlib.sha256(actual.encode()).hexdigest(),'closure_script_sha256':hashlib.sha256(source.encode()).hexdigest(),'pattern':st['fail_regex'],'records':records,'negative_fixtures_rejected':len(negatives),'other_two_stage_forms':'Exact recorded wrapper presentation replayed from committed raw witnesses; their daemon stages were not reached after c0stop. No new simulation claimed.'}
(HERE/'pattern_receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
