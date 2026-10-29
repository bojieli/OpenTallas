#!/usr/bin/env python3
"""Build source-preserving HEAD ctl/host/mesh kits; generation only, no P&R."""
import argparse,json,shutil,sys
from pathlib import Path

def build(plan_path,sidecar,out,repo,types):
    plan_path,sidecar,out,repo=map(lambda p:Path(p).resolve(),(plan_path,sidecar,out,repo))
    if out.exists():raise ValueError('fresh output directory required')
    sys.path[:0]=[str(repo/'tools/die_plan'),str(repo/'tools/s81_head')]
    import gen_phys
    from head_count_strap_sites import apply
    from head_start_reset_aliases import patch_rtl
    raw=json.loads(plan_path.read_text());side=json.loads(sidecar.read_text())
    raw,sites=apply(raw,plan_path,repo,types=set(types))
    for t in raw['partition_types'].values():
        for c in t.get('hard_cores',[]):
            if c.get('pins_file') and not Path(c['pins_file']).is_absolute():
                c['pins_file']=str((plan_path.parent/c['pins_file']).resolve())
    out.mkdir(parents=True);candidate=out/'source_plan_count_sites.json'
    candidate.write_text(json.dumps(raw,indent=1)+'\n')
    kits=gen_phys.write_phys(raw,out/'kits',repo,types=types,trial=True,plan_path=candidate,landing=side)
    reports={}
    for name,kd in zip(sorted(types),kits):
        t=raw['partition_types'][name];wrapper=out/'kits/_rtl'/f"{t['module']}.sv"
        rows=t.get('reset_start_raw_exports',[])
        text=patch_rtl(wrapper.read_text(),rows)
        wrapper.write_text(text);(Path(kd)/'rtl'/wrapper.name).write_text(text)
        reports[name]=dict(count_sites=sites.get(name,{}),registered_raw_aliases=sum(not r.get('existing_port') for r in rows),cycles_added=0)
    receipt=dict(types=reports,source_plan=str(plan_path),sidecar=str(sidecar),route_qualified=False)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps(receipt))
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan');p.add_argument('sidecar');p.add_argument('--out',required=True)
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--types',default='hd_ctl,hd_host,hd_mesh');a=p.parse_args()
    build(a.plan,a.sidecar,a.out,a.repo,a.types.split(','))
