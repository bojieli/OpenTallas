"""Random legal fixed-issue calendar -> prog.hex / meta.hex / lat.hex (S-ELEM-PQ c9 n4 differential bench)."""
import random,sys
sys.path.insert(0,sys.argv[1]+'/tools/s81_static_control')
from program import encode_program
seed=int(sys.argv[2]);pert=int(sys.argv[3]);out=sys.argv[4]
r=random.Random(seed)
n=r.choice([2,3,8,40,127])
rows=[];used_i=set();used_d=set();lat={}
end_issue=r.randint(60,400)
ncmd=n-1-(1 if n>2 and r.random()<0.6 else 0)
k=0
while len(rows)<ncmd and k<10000:
    k+=1
    e=r.randrange(13);iss=r.randrange(0,end_issue-6);d=r.randint(1,min(30,end_issue-1-iss))
    if (e,iss) in used_i or (e,iss+d) in used_d:continue
    used_i.add((e,iss));used_d.add((e,iss+d))
    rows.append(dict(engine=e,arg=r.randrange(1<<24),issue=iss,done=iss+d))
if n-1-len(rows)==1:rows.append(dict(engine=14,arg=0,issue=r.randrange(0,end_issue),done=0))
rows.append(dict(engine=15,arg=0,issue=end_issue,done=0))
r.shuffle(rows)
p=encode_program(rows,5,r.randrange(4))
w=[x['word'] for x in p['writes']]
# command for row i appears one edge after age==issue; completion is checked when the registered dn equals done+1
for i,row in enumerate(rows):lat[i]=row['done']-row['issue'] if row['engine']<14 else 0
open(out+'/prog.hex','w').write(''.join(f'{x:09x}\n' for x in w))
open(out+'/meta.hex','w').write(''.join(f'{x:08x}\n' for x in [len(w),len(rows),20000,pert,p["start_phase"],0,0,0]))
open(out+'/lat.hex','w').write(''.join(f'{lat.get(i,0):04x}\n' for i in range(128)))
