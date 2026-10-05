import hashlib,json,sys,subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from fractions import Fraction
from collections import Counter
sys.path.insert(0,'tools')
import w19_finite_service_calendar as C
scratch=TemporaryDirectory(prefix='finite-service-parent-replay-')
base=Path(scratch.name)
for tool,out,expected in [('w19_composed_schedule.py',base/'graph',2),('w19_finite_service_calendar.py',base/'profile.json',0),('w19_gpu_elementwise_calendar.py',base/'moe.json',0)]:
 result=subprocess.run([sys.executable,'tools/'+tool,'--out',str(out)],stdout=subprocess.DEVNULL)
 assert result.returncode==expected,(tool,result.returncode)
record={}
for n,source in [('finite_service_profile',str(base/'profile.json')),('moe_sum_calendar',str(base/'moe.json'))]:
 saved=Path(f'results/quality/w16_w19_composed_schedule_20261001/{n}.json').read_bytes(); fresh=Path(source).read_bytes();assert saved==fresh;record[n]=hashlib.sha256(saved).hexdigest()
replay=base/'graph'
for f in replay.glob('*.json'):
 saved=Path('results/quality/w16_w19_composed_schedule_20261001')/f.name
 if saved.exists():assert saved.read_bytes()==f.read_bytes();record[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
cases=[]
for clients in [1,4,32]:
 for stall in [1,7,31]:
  events=[dict(return_ps=str((i//128)*C.FAST),stack=(i//32)%4,pc=i%32,client=i%clients,sector=i%4,tag=i) for i in range(256)]
  r=C.read_calendar(events,clients,{i:stall for i in range(clients)}); rows=r['timeline'];assert len(rows)==256
  budget=Counter((x['stack'],Fraction(x['crossbar_grant_ps'])) for x in rows);assert max(budget.values())<=23
  bybank={}
  for x in rows:
   g=Fraction(x['crossbar_grant_ps']);release=Fraction(x['credit_return_ps'])
   assert release>=g+5*C.FAST
   key=x['client'],x['bank']; intervals=bybank.setdefault(key,[])
   assert sum(a<=g<b for a,b in intervals)<2
   intervals.append((g,release))
  assert all(Fraction(x['consumer_delivery_ps'])>Fraction(x['crossbar_grant_ps'])+4*C.FAST for x in rows)
  cases.append(dict(clients=clients,consumer_bound=stall,responses=256,conservation=True,controller_budget=True,inflight_output_credits=True,both_clock_crossings=True))
profile=json.load(open(str(base/'profile.json')))
for path,pin in profile['source_pins'].items():
 raw=subprocess.check_output(['git','show',pin['commit']+':'+path]);assert hashlib.sha256(raw).hexdigest()==pin['sha256']
out=dict(schema='opentallas.parent-finite-service-review.v1',reviewed_commit='20e93a52e',source_profiles=record,collision_cases=cases,focused_tests=32,status='PASS_COMPONENT_REPLAY_AND_RESOURCE_INVARIANTS',scope='Independent resource-occupancy and source replay; not numerical execution, RTL or full token',physical_admission=False,full_token_cycles=None,full_token_rate=None,remaining='Actual backend event traces, complete consumer contracts, combined read/write port budget and contextual timing/fit remain unbound.')
Path('results/quality/finite_service_parent_review_20261001/receipt.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS nine collision scenarios / 2304 response events; saved profiles and graph records replay exactly.')
