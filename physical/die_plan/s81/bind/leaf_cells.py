import sys,json,re,collections
sys.path.insert(0,'/home/ubuntu/wt/binder4-s81-1023/tools/die_plan')
import bind_elab as E
yjs=json.load(open(sys.argv[1]+'/asbuilt.json'))
ab=json.load(open(sys.argv[2]))
F=E.flatten(yjs, ab['top'], ab.get('substitute_parent', []))
tr=[re.compile(t['module']) for t in ab['transport']]+[re.compile(s['module']) for s in ab['sources']]
c=collections.Counter(); ex={}
out=[]
for cell in F.cells:
    if any(r.fullmatch(cell.module) for r in tr): continue
    out.append((cell.path, cell.module, getattr(cell,'ytype',None)))
    k=(re.sub(r'\d+','#',cell.path), cell.module if not cell.module.startswith('$') else cell.module)
    c[k]+=1; ex.setdefault(k,cell.path)
json.dump(out, open(sys.argv[1]+'/leaf_cells.json','w'))
for k,v in sorted(c.items()): print(v,k[0][:110],k[1][:50],ex[k][:60])
