import json,sys
raw=json.load(open(sys.argv[1])); parts={p['name']:p for p in raw['partitions']}
for q in ('NW',):
  for n in ('b110','b111','b112','b113','hub'):
    pn=f'{q}_{n}'; p=parts[pn]; t=raw['partition_types'][p['type']]; w,h=t['outline_um']
    hc=t.get('hard_cores',[])
    a=sum(c['outline_um'][0]*c['outline_um'][1] for c in hc)
    print(pn,p['type'],p['origin_um'],'outline',w,h,'area',round(w*h),'cores',len(hc),'core_area',round(a),'frac',round(a/(w*h),3), [k for k in t if 'fill' in k or 'util' in k])
    if n=='hub': continue
    for c in hc:
      if any(s in (c.get('module','')+c['inst']).lower() for s in ('sfu','lane','opst','ctl')):
        print('   ',c['inst'],c.get('module'),c['outline_um'],c['origin_um'])
