import json,sys
r=json.load(open(sys.argv[1]))
print('STATUS',r.get('status'),'violations',len(r.get('violations',[])),'max',r.get('max_dynamic_loads'),'roots',r.get('roots_examined'),'errors',r.get('role_errors'))
for v in r.get('violations',[])[:10]: print(' ',v)
