#!/usr/bin/env python3
"""Approved7.11 NEW R0 SU core aspect candidate; no adoption or signed-view alias.

Uses the explicit NEW named native-pin profile (1318 BTAB /1393 programme),
not a rescaled old view. BOTH children must become SIGNED and their final LEFs
must match these contracts before parent adoption. Old prog_s8b remains immutable. No RTL/stage edits.
"""
import json
from pathlib import Path

LAYOUT = {
 'u_suvm_u_vm8q_u_pg': ([17.28,380.16],[354.24,259.2]),
 'u_suvm_u_vm8q_u_ch': ([388.8,380.16],[259.2,276.48]),
 'u_suvm_u_vm8q_u_bt': ([665.28,380.16],[354.24,259.2]),
 'u_suvm_u_su8': ([1036.8,380.16],[172.8,129.6]),
}
RESHAPED = {'u_suvm_u_vm8q_u_pg','u_suvm_u_vm8q_u_bt'}


def apply(raw, plan_dir, candidate_dir, native_profiles):
    if raw.get('die',{}).get('name')!='qwen_compute':raise ValueError('QC only')
    plan_dir=Path(plan_dir);candidate_dir=Path(candidate_dir)
    changed=[]
    for tn in ('sle_su_c','slw_su_c'):
        t=raw['partition_types'][tn]
        if t['outline_um']!=[1226.88,1339.2]:raise ValueError('parent outline changed')
        contents={c['inst']:c for c in t['contents']}
        for h in t['hard_cores']:
            name=h['inst']
            if name not in LAYOUT:continue
            old_origin=list(h['origin_um']);old_size=list(h['outline_um'])
            origin,size=LAYOUT[name]
            if h.get('orient','R0')!='R0':raise ValueError('no orientation waiver')
            if abs(old_size[0]*old_size[1]-size[0]*size[1])>1e-5:raise ValueError('core area changed')
            if name in RESHAPED:
                if old_size!=[259.2,354.24]:raise ValueError('not the approved old aspect')
                pinpath=Path(h['pins_file'])
                key='prog' if name.endswith('_pg') else 'btab'
                doc=json.loads(Path(native_profiles[key]).read_text())
                if doc.get('core')!=h['module'] or 'NOT SIGNED' not in doc.get('source',''):
                    raise ValueError('require the approved NEW named native-pin contract, explicitly unqualified')
                want=1393 if key=='prog' else 1318
                if len(doc['pins'])!=want or len({p['name'] for p in doc['pins']})!=want:
                    raise ValueError('new child native pin inventory mismatch')
                newpath=pinpath.with_name(pinpath.stem+'_aspect1713.json')
                dst=candidate_dir/newpath;dst.parent.mkdir(parents=True,exist_ok=True)
                dst.write_text(json.dumps(doc,indent=1)+'\n')
                h['track_offset_um']=[.012,.012]
                for pin in doc['pins']:
                    if pin['layer'] not in ('M4','M5'):continue
                    axis=1 if pin['layer']=='M4' else 0
                    value=pin['y' if axis else 'x']+origin[axis]+.012
                    phase=(value-.024)/.048
                    if abs(phase-round(phase))>1e-5:raise ValueError('native pin off parent track grid')
                h['pins_file']=str(newpath)
                h['note']+='; NEW R0 ASPECT UNQUALIFIED: old signed view not applicable, require both new child SIGNED'
            h['origin_um']=list(origin);h['outline_um']=list(size)
            contents[name]['origin_um']=list(origin);contents[name]['outline_um']=list(size)
            for tap in t['clock'].get('taps',[]):
                if tap.get('name')!=name+'.ck':continue
                if name in RESHAPED:
                    ck=[p for p in doc['pins'] if p['name']=='ck']
                    if len(ck)!=1:raise ValueError('one native child ck pin required')
                    tap['xy']=[round(origin[0]+.012+ck[0]['x'],4),round(origin[1]+.012+ck[0]['y'],4)]
                    tap['budget_owner']='UNQUALIFIED new-aspect planning budget only; fresh native child insertion contract required before adoption'
                else:
                    tap['xy']=[round(tap['xy'][i]+origin[i]-old_origin[i]+(size[i]-old_size[i])/2,4) for i in (0,1)]
            changed.append(dict(type=tn,core=name,old_origin_um=old_origin,new_origin_um=origin,
                                old_outline_um=old_size,new_outline_um=size))
    return dict(schema='opentallas.qc-su-aspect-candidate.v1',status='UNQUALIFIED_NEW_CHILDREN_REQUIRED',
                changed=changed,core_area_delta_um2=0,FF_added=0,data_cycles_added=0,token_cycles_added=0,
                partition_boundary_changed=False,parent_outline_changed=False,old_signed_prog_mutated=False,
                adoption_gate='Both new prog/btab physical views SIGNED + actual pin/clock replacement + parent G0/G2/GEOM',
                channel_fallback='UNADOPTED estimated cws1/cws2 +2 stages each')
