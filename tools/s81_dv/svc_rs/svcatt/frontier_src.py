import json,sys
d=json.load(open(sys.argv[1])); top=sys.argv[3]; m=d['modules'][top]
r=json.load(open(sys.argv[2]))
for x in r['rows']:
    c=x.get('cell')
    if not c: print(x['loads'],x['reason'][:20],x.get('names')); continue
    cell=m['cells'].get(c,{})
    a=cell.get('attributes',{})
    print(x['loads'],x['reason'][:20],cell.get('type'),c[:60],a.get('src','')[:200])
