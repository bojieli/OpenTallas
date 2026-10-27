import json,sys
r=json.load(open(sys.argv[1]))
for k in ('max','min'):
  f=r['fits'][k];print(k,f['params'],f['kleaf'],{b:{c:(v['mean'],v['sd'],v['maxabs']) for c,v in x.items()} for b,x in f['per_build'].items()})
  for h,x in r['loo'][k].items(): print('  LOO',h,x['params'],{c:(v['mean'],v['sd'],v['maxabs']) for c,v in x['test'].items()})
