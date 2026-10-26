import pathlib,subprocess,hashlib,json,re
r=pathlib.Path(__file__).resolve().parent;o=r.parent/'qslot_replay';o.mkdir(exist_ok=True);vl=str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
with (o/'build.log').open('w') as f:p=subprocess.run([vl,'--binary','--timing','-j','4','-Wno-fatal','-Wno-lint','--top-module','tb_qbank','--Mdir',str(o/'obj'),str(r/'qbank.sv'),str(r/'sram.v'),str(r/'tb_qbank.sv')],stdout=f,stderr=subprocess.STDOUT)
assert p.returncode==0,'BUILD FAILURE'
cs=[]
for label,schedule in [('positive','qslot_pin_schedule.memh'),('early','qslot_pin_schedule_early.memh')]:
 p=subprocess.run([str(o/'obj/Vtb_qbank'),'+SCHEDULE='+str(r/schedule)],capture_output=True,text=True);t=p.stdout+p.stderr;(o/(label+'.log')).write_text(t)
 emits=[tuple(map(int,x)) for x in re.findall(r'QPIN_EMIT beat=(\d+) edge=(\d+) read_edge=(\d+) age=(\d+)',t)]
 expected=json.loads((r/'compiler_booking.json').read_text())['bookings'][0]['qbank_emit_edges'];matches=[e[1] for e in emits]==expected
 good=p.returncode==0 and 'QB_PASS' in t and len(emits)==32 and all(e[3]==4 for e in emits) and (matches if label=='positive' else not matches)
 cs.append(dict(name=label,rc=p.returncode,source_read_age=4,emit_matches_compiler=matches,ok=good));print(cs[-1],flush=True)
(o/'record.json').write_text(json.dumps(dict(scope='component source pin edges and synthetic compiler mechanism replay only; actual GEN dates remain absent',qbank_sha256=hashlib.sha256((r/'qbank.sv').read_bytes()).hexdigest(),macro_sha256=hashlib.sha256((r/'sram.v').read_bytes()).hexdigest(),binary_sha256=hashlib.sha256((o/'obj/Vtb_qbank').read_bytes()).hexdigest(),cases=cs),indent=2)+'\n')
raise SystemExit(0 if all(c['ok'] for c in cs) else 1)
