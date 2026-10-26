import json,sys,re
pp=json.load(open(sys.argv[1]))['nk']
STN={'tt':(104,94,114),'ff':(79,69,89)}
out={}
for tag,path in [('diagt',sys.argv[2]),('diag',sys.argv[3])]:
    d=json.load(open(path))
    for r,m in d['clock_measurements'].items():
        for c in ('tt','ff'):
            mc=m[c]; lo=[];hi=[];plo=[];phi=[]
            for p in mc['macros']['pins']:
                inst,pin=p['pin'].rsplit('/',1); a=p['arr']
                leaf=inst.split('.')[-1]
                if leaf.startswith('u_t_'):
                    if pin not in pp[c]: print('MISSING',pin); continue
                    _,mn,mx=pp[c][pin]
                else: _,mn,mx=STN[c]
                lo.append(a+mn); hi.append(a+mx); plo.append(a); phi.append(a)
            al=mc['all']
            if al and al.get('n'): lo.append(al['min']); hi.append(al['max']); plo.append(al['min']); phi.append(al['max'])
            out.setdefault(tag,{}).setdefault(r,{})[c]={'pin_ins':[round(min(plo),1),round(max(phi),1)],'pin_spread':round(max(phi)-min(plo),1),
               'flop_ins':[round(min(lo),1),round(max(hi),1)],'flop_spread':round(max(hi)-min(lo),1)}
for t,R in out.items():
    for r,v in R.items():
        print(t,r,' '.join(f"{c}: pin {v[c]['pin_ins'][0]}-{v[c]['pin_ins'][1]} sp {v[c]['pin_spread']} | flop {v[c]['flop_ins'][0]}-{v[c]['flop_ins'][1]} sp {v[c]['flop_spread']}" for c in ('tt','ff')))
json.dump(out,open('/tmp/qdie10_flop.json','w'),indent=1)
