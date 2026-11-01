from pathlib import Path
import json
r=Path('/srv/opentallas-scratch2/claude/codex-qc-red-balance-1101');p=r/'tools/die_plan/core_family_slice.py';s=p.read_text()
fn='''def lattice_local_balance(P, limit=35.0):
    # Reassign actual sinks only among existing sibling tips; topology/masters/stages unchanged.
    # No dummy loads, added sinks, removed sinks, padding or per-driver sizing.
    pos={n[0]:n[2] for n in P["nodes"]}
    groups={}
    for u in P["leafsinks"]:groups.setdefault(u[:-1],[]).append(u)
    moved=0;blocked=0
    for prefix,us in sorted(groups.items()):
        us=sorted(us);N=sum(len(P["leafsinks"][u]) for u in us);q,rem=divmod(N,len(us))
        ranked=sorted(us,key=lambda u:(-len(P["leafsinks"][u]),u))
        target={u:q+(i<rem) for i,u in enumerate(ranked)}
        while True:
            hot=[u for u in us if len(P["leafsinks"][u])>target[u]]
            cold=[u for u in us if len(P["leafsinks"][u])<target[u]]
            if not hot or not cold:break
            best=None
            for a in hot:
                for i,sk in enumerate(P["leafsinks"][a]):
                    old=abs(sk[0]-pos[a][0])+abs(sk[1]-pos[a][1])
                    for b in cold:
                        dist=abs(sk[0]-pos[b][0])+abs(sk[1]-pos[b][1])
                        if dist>limit:continue
                        item=(dist-old,dist,a,b,i)
                        if best is None or item<best:best=item
            if best is None:blocked+=1;break
            _,_,a,b,i=best;P["leafsinks"][b].append(P["leafsinks"][a].pop(i));moved+=1
    flat=[(s[2],s[3]) for vs in P["leafsinks"].values() for s in vs]
    assert len(flat)==len(set(flat))
    P["local_balance"]={"moved_sinks":moved,"blocked_groups":blocked,"max_L1_limit_um":limit,"same_existing_sibling_tips_only":True}
    print("LOCAL_BALANCE",json.dumps(P["local_balance"]),flush=True)


'''
s=s.replace('def lattice_window_masters(',fn+'def lattice_window_masters(',1)
s=s.replace('P = lattice_build(sinks, ent, levels)\n    P["mz"]', 'P = lattice_build(sinks, ent, levels)\n    if fam.get("lattice_local_balance"):lattice_local_balance(P, float(fam.get("leaf_limit",35.0)))\n    P["mz"]',1)
s=s.replace('plan_rule="symmetric lattice (equal leg length per level)', 'local_balance=P.get("local_balance"),\n               plan_rule="symmetric lattice (equal leg length per level)',1)
p.write_text(s)
f=json.loads((r/'family_five.json').read_text());f['families'][0]['lattice_local_balance']=True;f['rule']+='; actual sink-only same-existing-sibling leaf balancing <=35um; same topology/masters perlevel, no dummy loads or padding.';(r/'family_balanced.json').write_text(json.dumps(f,indent=2)+'\n')
(r/'run.sh').write_text('''#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-qc-red-balance-1101
python3 tools/die_plan/core_family_slice.py run --family family_balanced.json --core qfd_dv_s5_red2_leaf --kit /srv/opentallas-scratch2/claude/codex-qc-red-power-1101/placed_input --work model_balanced --libtt INVBUF_TT.lib --libff INVBUF_FF.lib > model.log 2>&1
''')
