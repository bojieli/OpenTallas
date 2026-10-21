# QW-G5STA diagnostic: rewrite the g5 die STA landing MCPs with the land plan re-derived on g5's OWN STA (chain/land_plan.json)
import json,re,sys,os
from pathlib import Path
chain=Path(sys.argv[1]); out=Path(sys.argv[2])
plan={l['bid']:l for l in json.load(open(chain/'land_plan.json'))['links']}
lanes=json.load(open(chain/'case_r22k/fwd_lanes.json'))['lanes']
def pins(r): return f"{r['landing']}/a[*]" + ('' if r['n']==1 else f" {r['landing']}/ea[*]")
pmap={}; rep=[]
for r in lanes:
    if r.get('lane')=='reset': continue
    p=plan.get(r['bid'])
    if not p or p.get('E') is None: continue
    D=int(p.get('D') or 4)
    pmap[pins(r)]=(int(p['E']),D-1,r['bid'],r.get('E_sta'),r.get('E'),r['n'])
    rep.append(dict(bid=r['bid'],n=r['n'],E_sta_old=r.get('E_sta'),E_sta_new=int(p['E']),D=D,E_sched_old=r.get('E'),
                    E_sched_new=(r.get('E') or 0)-(r.get('E_sta') or 2)+int(p['E']),window_ok=p.get('window_ok')))
rx=re.compile(r'^set_multicycle_path -(setup|hold) (\d+) -to \[get_pins \{([^}]*)\}\]')
for c in ('tt','ff','ss'):
    src=chain/f'sta_r22k_{c}/grt_{c}.tcl'; d=out/f'sta_{c}'; d.mkdir(parents=True,exist_ok=True)
    n=0; L=[]
    for line in open(src):
        m=rx.match(line)
        if m and m.group(3) in pmap:
            e,h,_,_,_,_=pmap[m.group(3)]
            line=f"set_multicycle_path -{m.group(1)} {e if m.group(1)=='setup' else h} -to [get_pins {{{m.group(3)}}}]\n"; n+=1
        line=line.replace('/work/die_clock_check.tcl','/work/__skip_dcc.tcl')
        if 'die_repeaters.tcl' in line: continue
        L.append(line)
    (d/f'grt_{c}.tcl').write_text(''.join(L))
    for f in ('ckpt_grt.odb','die_grt.spef'):
        t=d/f
        if not t.exists(): os.link(chain/f'sta_r22k_{c}'/f,t)
    lt=chain/f'sta_r22k_{c}/land_{c}.tcl'
    (d/f'land_{c}.tcl').write_text(Path(lt).read_text())
    ld=d/'libs'; ld.mkdir(exist_ok=True)
    for f in (chain/f'sta_r22k_{c}/libs').iterdir():
        if not (ld/f.name).exists(): os.link(f,ld/f.name)
    print(c,'mcp lines rewritten',n)
json.dump(rep,open(out/'e_rederive.json','w'),indent=1)
over=[x for x in rep if x['E_sta_new']>x['E_sta_old']]
print('lanes',len(rep),'E_sta raised',len(over),'D8',sum(1 for x in rep if x['D']==8))
