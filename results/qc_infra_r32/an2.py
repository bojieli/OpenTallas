import json,collections,re,sys
d=json.load(open(sys.argv[1])); s=json.load(open(sys.argv[2]))
e=d['rows']
by={n["edge"]:n for n in s["nets"]}
cs=s['cell_sites']
gk={}
for nm,v in cs.items(): gk[v['group']]=v['kind']
c=collections.Counter(); nets=collections.defaultdict(set)
for x in e:
    n=by[x['edge']]; m=re.match(r"(.*?) (M\d) ideal",x['detail'])
    fam=(x['edge'].split(':')[0], 'elbow' if 'elbow' in x['edge'] else ('L' if '_L' in x['edge'] else ''), gk[int(n['drv'][1:])], gk[int(n['load'][1:])], n['layer'],n['ndr'], m.group(1).replace(n['drv'].replace('g','ckt_'),'X'))
    c[fam]+=1; nets[fam].add(x['edge'])
for k,v in c.most_common(60): print(v,len(nets[k]),k)
