"""Require actual RTL output, numerical verdict and matching NU1/4 raw traces."""
import pathlib,json,hashlib,re
W=pathlib.Path('/srv/opentallas-scratch/claude/refill-1225/QWLAYER/staging_replay_1019')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for c in json.loads((W/'cases.json').read_text()):
 d=W/f'nu{c["nu"]}'/c['name'];out=(d/'bench.out').read_text();logs=list(d.glob('run_*.log'));events=list(d.glob('run_*.ev'))
 verdicts=re.findall(r'^DV_LOWER_VEC .+$',out,re.M)
 row=dict(nu=c['nu'],name=c['name'],mutant=c['mutant'],verdict=verdicts,errors=[x.strip() for x in out.splitlines() if x.startswith('    ')],rtl_logs={p.name:dict(sha256=sha(p),bytes=p.stat().st_size,lines=sum(1 for _ in p.open())) for p in logs},events={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in events})
 row['actual_rtl']=bool(logs and events and all(p.stat().st_size for p in logs+events) and 'RTL_EXEC_BEGIN' in out and 'Traceback' not in out)
 row['expected_verdict']=row['actual_rtl'] and len(verdicts)==1 and (' FAIL ' if c['mutant'] else ' PASS ') in verdicts[0] and ('BENCH_RC 1' if c['mutant'] else 'BENCH_RC 0') in out
 if c['mutant']:
  required={'arwin':r'slice 0: RB .* want ', 'nor':r'act stream: 24/24 words wrong / off edge', 'ropesign':r'q: 512/512 mismatches'}[c['mutant']]
  row['causal_fail_regex']=required;row['causal_reason_match']=bool(re.search(required,out));row['expected_verdict'] &= row['causal_reason_match']
 if not c['mutant']:row['isa_gold']=re.search(r'isa_gold_words=(\d+)/(\d+)',out).groups();row['isa_gold_complete']=row['isa_gold'][0]==row['isa_gold'][1] and int(row['isa_gold'][0])>0
 rows.append(row)
pairs=[]
for a in [r for r in rows if r['nu']==1]:
 b=next(r for r in rows if r['nu']==4 and r['name']==a['name']);pairs.append(dict(name=a['name'],raw_rtl_equal=a['rtl_logs']==b['rtl_logs'],events_equal=a['events']==b['events'],verdict_equal=a['verdict']==b['verdict']))
report=dict(cases=rows,pairs=pairs,scope='Seven recorded vector cuts and three causal command/program mutants on N12, each NU1/NU4; no independent four-user request lifetimes, matrix cuts or full token qualification.')
report['pass']=all(r['expected_verdict'] and r.get('isa_gold_complete',True) for r in rows) and all(all(r[k] for k in ['raw_rtl_equal','events_equal','verdict_equal']) for r in pairs)
(W/'classification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));raise SystemExit(0 if report['pass'] else 1)
