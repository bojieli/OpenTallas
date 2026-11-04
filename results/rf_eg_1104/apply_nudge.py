#!/usr/bin/env python3
"""RF-EG follow-up: apply ft_nudge.py station moves as a text edit (only changed slot keys); JSON equality asserted. argv: PLAN NUDGED_OUT"""
import json,re,sys
F,O=sys.argv[1:3]; s=open(F).read(); a=json.loads(s); b=json.load(open(O)); n=0
def span(s,i):
    op=s[i]; cl={'[':']','{':'}'}[op]; d=0; q=False; j=i
    while True:
        c=s[j]
        if q:
            if c=='\\': j+=1
            elif c=='"': q=False
        elif c=='"': q=True
        elif c==op: d+=1
        elif c==cl:
            d-=1
            if d==0: return j+1
        j+=1
base=s.index('"partition_types"')
for tn,t in a["partition_types"].items():
    tb=b["partition_types"][tn]
    if t==tb: continue
    ti=s.index('"%s":'%tn,base)
    for sa,sb in zip(t["ft_slots"],tb["ft_slots"]):
        if sa==sb: continue
        fi=s.index('"ft_slots"',ti); ni=re.compile(r'"name":\s*"%s"'%sa["name"]).search(s,fi).start()
        for k in sb:
            if sa.get(k)==sb[k]: continue
            assert k in sa,(tn,k)
            ki=s.index('"%s"'%k,ni); vi=s.index(':',ki)+1
            while s[vi] in ' \n': vi+=1
            e=span(s,vi) if s[vi] in '[{' else None; assert e
            new=json.dumps(sb[k]); s=s[:vi]+new+s[e:]; n+=1; print(tn,sa["name"],k,"->",new[:160])
    assert json.loads(s)["partition_types"][tn]==tb,tn
assert json.loads(s)==b
open(F,"w").write(s); print("edits",n)
