import json,sys,os
def load(p):
    if os.path.isdir(p): p=os.path.join(p,'g0_report.json')
    r=json.load(open(p)); it=r.get('items',r.get('findings',[]))
    return {(i.get('check'),i.get('msg')) for i in it if i.get('level','').upper() in ('ERROR','ERR')}
a,b=load(sys.argv[1]),load(sys.argv[2])
print('base',len(a),'new',len(b)); 
for k in sorted(b-a): print('NEW',k[0],k[1][:300])
for k in sorted(a-b): print('GONE',k[0],k[1][:200])
