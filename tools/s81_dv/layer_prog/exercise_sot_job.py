"""Exercise SOT on the real source compiler Job and a real fixture."""
import argparse, copy, json, sys
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--source',required=True); p.add_argument('--fixtures',required=True); p.add_argument('--booking',required=True)
a=p.parse_args()
base=Path(a.source)
for sub in ('tools','tools/s81_dv/layer_prog'):
    sys.path.append(str(base/sub))
import lower_svc as L
sys.path.insert(0,str(Path(__file__).resolve().parent))
from sot_program import booking, attach_to_job
r=json.loads(Path(a.booking).read_text())
heads={int(g):{k:v+r['install_edge'] for k,v in x.items()} for g,x in r['heads'].items()}
rec=booking(L.USER<<8,0x21,0x22,0x200,1,r['install_edge'],heads,r['gather_first']+r['install_edge'],r['gather_last']+r['install_edge'])
j=L.Job(a.fixtures,owner_epoch=0)
before=j.schedule(0,0,0,32,25)
attach_to_job(j,rec)
after=j.schedule(0,0,0,32,25)
assert after['nframes']==before['nframes']+1
assert after['at']['SOT']==after['at']['WIN_LOAD']+1
assert after['at']['ATTN_Q0']==before['at']['ATTN_Q0']+3
arg,word=L.job_word(after['nframes'],j.tag)
assert (arg>>7)&255==after['nframes']
caught=[]
try: attach_to_job(j,rec)
except ValueError: caught.append('duplicate')
j2=L.Job(a.fixtures,owner_epoch=0)
bad=copy.deepcopy(rec);bad['owner']^=1
try: attach_to_job(j2,bad)
except ValueError: caught.append('owner')
for label,change in [('overflow',{'retire':r['install_edge']+65536}),('read_before_write',{'read':heads[0]['last']+1})]:
    bh=copy.deepcopy(heads); bh[0].update(change)
    try: booking(L.USER<<8,0x21,0x22,0x200,1,r['install_edge'],bh,r['gather_first']+r['install_edge'],r['gather_last']+r['install_edge'])
    except ValueError: caught.append(label)
assert len(caught)==4
print(json.dumps(dict(verdict='PASS',real_job_frames_before=before['nframes'],real_job_frames_after=after['nframes'],q_words_added=3,causal_invalid_bookings=caught,scope='real compiler frame/count path; component dates are not production die dates')))
