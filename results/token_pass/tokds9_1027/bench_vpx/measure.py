import json,sys,re
from pathlib import Path
for d in sys.argv[1:]:
    d=Path(d); e=json.loads((d/'expect.json').read_text())
    if not (d/'run.log').exists(): continue
    ev={'SEND':{},'LRI':{},'WR':{}}
    for ln in (d/'run.log').read_text(errors='replace').splitlines():
        t=ln.split()
        if t and t[0] in ev: ev[t[0]].setdefault(t[1],[]).append(int(t[2]))
    t0,t1=e['t0'],e['t1']
    stim=[int(l.split()[0]) for l in (d/'stim.txt').read_text().splitlines()[1:]]
    first_ctl=min(c for c in stim if c>=t0)
    r={}
    for die in 'AB':
        s=[c for c in ev['SEND'].get(die,[]) if t0<=c<t1]
        w=[c for c in ev['WR'].get(die,[]) if t0<=c<t1]
        l=[c for c in ev['LRI'].get(die,[]) if t0<=c<t1]
        r[die]=dict(sends=len(s),first_send=min(s) if s else None,last_send=max(s) if s else None,
                    last_peer_wr=None)
        r[die]['lri']=(min(l),max(l)) if l else None
        r[die]['wr']=(min(w),max(w)) if w else None
    last_wr=max([r[x]['wr'][1] for x in 'AB' if r[x]['wr']] or [0])
    link=[]
    for die,peer in (('A','B'),('B','A')):
        s=[c for c in ev['SEND'].get(die,[]) if t0<=c<t1]; l=[c for c in ev['LRI'].get(peer,[]) if t0<=c<t1]
        if s and l and len(s)==len(l): link.append(sorted({b-a for a,b in zip(s,l)}))
    chk=json.loads((d/'check.json').read_text()) if (d/'check.json').exists() else {}
    print(json.dumps(dict(case=d.name,pass_=chk.get('pass'),first_ctl=first_ctl,last_peer_wr=last_wr,span=last_wr-first_ctl+1 if last_wr else None,send_to_lri=link,dies=r)))
