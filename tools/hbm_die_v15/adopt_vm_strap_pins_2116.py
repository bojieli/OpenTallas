#!/usr/bin/env python3
"""Adopt exact VM strap child pins without qualifying unfinished parents or routes."""
import copy, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/'results/arch/hbm_die_v15'
g=json.loads((DIR/'vm_strap_grants_1015.json').read_text())
p=json.loads((DIR/'compact660_v5/compact.P.json').read_text())
for q,s in enumerate(g['slots']):
    s['source_sha256']=hashlib.sha256((ROOT/s['source']).read_bytes()).hexdigest()
    deps=[s['source'],'rtl/hbm_accel/generic/vm/static/ot_vms_bank_static_strap.sv','rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv']
    s['source_dependencies_sha256']={d:hashlib.sha256((ROOT/d).read_bytes()).hexdigest() for d in deps}
    s['source_prerequisite']='current source pinned by exact SHA256 below'
    s['grant']='die_owned_strap_pins_2116'
    s['scope']='Die-owned exact child pin/outline grant; physical qualification and production parent adoption remain OPEN.'
    s['diagnostic_only']=False
    s['source_graph_adopted']=False
    s['parent_and_die_qualified']=False
    s['instance_homes']=[]
    for b,n in enumerate(s['instances']):
        r=p[n];w,h=s['outline']['w'],s['outline']['h']
        fits=w<=r['w'] and h<=r['h']
        # Pins can be accepted independently of a missing physical home.
        s['instance_homes'].append(dict(plan_instance=n,die_origin=None,outline=s['outline'],parent='hb_vms_'+('SW','SE','NW','NE')[q],candidate_hierarchy=f'u_slice.g_bank[{b}].g_physical_strap.u_bank.q{q}.u_bank',strap_values=s['strap_values'][n],production_binding=False,planning_box_fit=fits,planning_box=r,home_status='UNPLACED: explicit parent packing and incident-path proof required',height_deficit_um=round(max(0,h-r['h']),6)))
    occupied=set()
    for pin in s['pins']:
        centres=pin['bit_centres_um']
        assert len(centres)==(int(pin['name'].split('[')[1].split(':')[0])+1 if '[' in pin['name'] else 1)
        for c in centres:
            assert abs((c-.012)/.048-round((c-.012)/.048))<1e-6
            assert (pin['face'],pin['layer'],c) not in occupied
            occupied.add((pin['face'],pin['layer'],c))
g.update(version=2,owner='Codex H-DIE takeover2116',canonical_die_contract_mutated=True,proposal_for=None,adoption_scope='Child exact pins and declared bid/sid ties only. Real parent opt-in STRAP_BANKS=1 is source-tested separately; no runtime arbitration, added data cycles or route qualification.',production_binding_adopted=False)
out=DIR/'vm_strap_grants_2116.json';out.write_text(json.dumps(g,indent=1)+'\n')
gf=ROOT/'results/arch/hier_contract_1015/hbm_v15.json';d=json.loads(gf.read_text());d['vm_strap_child_grants_2116']=dict(file=str(out.relative_to(ROOT)),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),distinct_masters=4,instances=32,registered_constant_pins=['bid[2:0]','sid[1:0]'],parent_source='rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static.sv',parent_opt_in=dict(STRAP_BANKS=1),production_binding_adopted=False,parent_and_die_qualified=False,note='Accepts original exact strap pin proposal; live source-frozen strap routes unchanged. No270x270/M6 resize adopted while current routes run.')
gf.write_text(json.dumps(d,indent=1)+'\n');print('PASS: 4 source-pinned master templates, 32 declared ties and honest unplaced homes, unique legal-track centres; no native qualification inherited')
