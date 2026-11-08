"""CLAND census v2: every landing raw reset relay/collector reset in the bound RTL, hop from its driver to its placed
site. Sites: u_cland_collect_<n>/u_cland_reset_<n> = collector tree xy[n] (landing_place); u_cland_rst_<b> = the plan's
landing_contract.group_rects_um centre when set, else the collector-tree xy of the source node of local source b
(landing_place line 440). Driver site: body relay comment '@ (x, y)', or
a cland_reset_<p> copy at tree xy[p]. usage: census2.py PLAN SIDECAR BIND_RTL_DIR OUT.json"""
import json,re,sys,glob,os,collections
P=json.load(open(sys.argv[1]));S=json.load(open(sys.argv[2]));R=sys.argv[3]
rel=re.compile(r"ot_dp_r(?:relay|gate)\w*\s+(\w+)\s*\([^;]*?\.d\(([^)]+)\)[^;]*?\.q\(([^)]+)\)\);\s*//[^@\n]*?(?:depth (\d+) )?@\s*\(([-\d.]+),\s*([-\d.]+)\)")
cp=re.compile(r"ot_dp_rrelay\s+(u_cland_(?:reset|rst)_\w+)\s*\(\.clk\(clk\),\s*\.d\(([^)]+)\),\s*\.q\((\w+)\)\);")
co=re.compile(r"ot_dp_landing_collect\s*#\(\.N\(\d+\)\)\s*(u_cland_collect_(\w+))\s*\(\s*\.clk\(clk\),\s*\.rst_n\(([^)]+)\)")
def safe(n):return re.sub(r"\W","_",n)
rows=[];tot=collections.Counter()
for T,pt in sorted(P['partition_types'].items()):
    f=f"{R}/{pt.get('module',T)}.sv"
    if not os.path.exists(f):continue
    txt=open(f,errors='replace').read()
    if 'u_cland_' not in txt:continue
    lc=(pt.get('clock') or {}).get('landing_contract') or {}
    info=(S['collector']['types'].get(T) or {})
    import importlib
    tree=lc.get('collector_tree') if isinstance(lc.get('collector_tree'),dict) and lc['collector_tree'].get('relays') and not lc['collector_tree'].get('hard') else info.get('tree')
    if not tree or tree.get('hard'):continue
    xy={'rst_root_n':tuple(tree['root']),**{r['q']:tuple(r['xy']) for r in tree['relays']}}
    sxy={safe(k):v for k,v in xy.items()}
    body={m.group(3):(float(m.group(5)),float(m.group(6))) for m in rel.finditer(txt)}
    copies={m.group(3):m for m in cp.finditer(txt)}
    def site_of_net(net):
        if net in body:return body[net],'body'
        if net.startswith('cland_reset_') and net[12:] in sxy and ('u_'+net) in [m.group(1) for m in copies.values()]:return sxy[net[12:]],'copy'
        if net=='rst_root_n':return xy['rst_root_n'],'root'
        return None,'?'
    srcnode={s['name']:(f"rst_n_t{s['tap']}" if s.get('tap') is not None else s.get('node')) for s in info.get('local_sources',[])}
    def add(kind,inst,site,net):
        d,how=site_of_net(net)
        h=None if (d is None or site is None) else abs(d[0]-site[0])+abs(d[1]-site[1])
        tot[(kind,'n')]+=1
        if h is None:tot[(kind,'unknown')]+=1
        elif h>405+1e-6:tot[(kind,'>405')]+=1;rows.append((T,kind,inst,net,how,round(h,1)))
    for net,m in copies.items():
        inst=m.group(1)
        if inst.startswith('u_cland_reset_'):add('copy',inst,sxy.get(inst[14:]),m.group(2))
        else:
            b=inst[12:];n=srcnode.get(b);r=(lc.get('group_rects_um') or {}).get(inst)
            add('ring',inst,((r[0]+r[2])/2,(r[1]+r[3])/2) if r else (xy.get(n) if n else None),m.group(2))
    for m in co.finditer(txt):add('collect',m.group(1),sxy.get(m.group(2)),m.group(3))
print({f"{k[0]}:{k[1]}":v for k,v in sorted(tot.items())})
ty=collections.Counter(r[0] for r in rows)
print('types with >405',len(ty),'by kind',collections.Counter(r[1] for r in rows),'max',max([r[5] for r in rows],default=0))
for k in ('copy','collect','ring'):print(k,'types',len({r[0] for r in rows if r[1]==k}))
json.dump(dict(totals={f"{k[0]}:{k[1]}":v for k,v in tot.items()},rows=rows),open(sys.argv[4],'w'),indent=0)
