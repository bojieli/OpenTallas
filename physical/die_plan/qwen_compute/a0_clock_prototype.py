#!/usr/bin/env python3
"""ROOT-approved PLANNED A0c42/41 clock prototype, never a native/SIGNED alias.

Legacy one-ck pin files/views remain untouched. The current bound functional
leaf is rr39/35, so physical composite/source/view matching is an explicit future
G3 gate. This opt-in candidate only exposes real canonical header ABI names and
assigned v8 sites, consistently snapped for the parent and the new planned pins.
"""
import copy,json,re,sys
from pathlib import Path

ABI={'qfd_tile_nk_a0c':('nk',42),'qfd_tile_nl_a0c':('nl',41)}
REQUIRED_DEFINES={
 'nk':['OT_A0_CK_TAPS','OT_A0_CK_TAPS24','OT_A0_CK_TAPS31','OT_A0_CK_TAPS32','OT_A0_CK_TAPS37','OT_A0_CK_TAPS38','OT_A0_CK_TAPS42'],
 'nl':['OT_A0_CK_TAPS','OT_A0_CK_TAPS24','OT_A0_CK_TAPS31','OT_A0_CK_TAPS32','OT_A0_CK_TAPS37','OT_A0_CK_TAPS41'],
}


def apply(raw, plan_dir, candidate_dir):
    if raw.get('die',{}).get('name')!='qwen_compute':raise ValueError('QC only')
    root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root/'tools/die_plan'))
    import schema as S,gen_phys as GP
    plan_dir=Path(plan_dir);out=Path(candidate_dir)
    spec=json.loads((plan_dir/'inputs/a0_core_taps.json').read_text())
    P=S.Plan(raw);master_pins={};changed=[];max_snap=0
    for tn,t in raw['partition_types'].items():
        if not tn.startswith(('cbf_','cbn_','cbx_')):continue
        cores=[h for h in t.get('hard_cores',[]) if h.get('module') in ABI]
        if not cores:continue
        if len(cores)!=4:raise ValueError('A0 quad must have exactly four declared core instances')
        before=len(S.tap_grid(P,tn));meta={q['name']:q for q in t['clock'].get('taps',[]) if q.get('kind')=='core'}
        expected=0
        for h in cores:
            module=h['module'];variant,count=ABI[module]
            if h.get('lef') or h.get('lib'):raise ValueError('never replace any existing physical view with this prototype')
            if h.get('orient','R0')!='R0':raise ValueError('unsupported core orientation')
            assigned=spec['variants'][variant]
            if assigned['module']!=module or len(assigned['taps'])!=count:raise ValueError('canonical assigned-site ABI mismatch')
            names={'ck'}|{f'ck_t{i}' for i in range(1,count)}
            if {q['name'] for q in assigned['taps']}!=names:raise ValueError('missing/extra canonical clock port')
            if {q.split('.',1)[1] for q in meta if q.startswith(h['inst']+'.')}!=names:
                raise ValueError('advisory metadata differs from canonical ABI; no silent port omission')
            old=json.loads((plan_dir/h['pins_file']).read_text());pins=copy.deepcopy(old['pins'])
            pins=[q for q in pins if not re.fullmatch(r'ck(?:_t[0-9]+)?',q.get('name',''))]
            ox,oy=h['origin_um'];dx,dy=h.get('track_offset_um',[0,0]);local=[]
            for q in assigned['taps']:
                x,y=q['xy'];gx,gy=ox+dx+x,oy+dy+y
                sx,sy=GP._snap_tap(P,gx,gy)
                max_snap=max(max_snap,abs(sx-gx)+abs(sy-gy))
                pin=dict(name=q['name'],layer='M7',x=round(sx-ox-dx,4),y=round(sy-oy-dy,4),dir='in')
                local.append(pin);tp=meta[h['inst']+'.'+q['name']]
                tp['xy']=[sx,sy]
                tp['budget_owner']='PLANNED canonical A0 clock prototype only: TT250/FF202.5 model budget, native/source/view closure OPEN'
                tp['insertion_ps']=250;tp['insertion_ff_ps']=202.5
            if module in master_pins and master_pins[module]!=local:raise ValueError('clock pin geometry differs across replicas of one master')
            master_pins[module]=local;pins+=local
            path=Path('cores')/f'a0_{variant}_clock{count}_PLANNED1713.json'
            dest=out/path;dest.parent.mkdir(parents=True,exist_ok=True)
            doc=dict(schema='opentallas.core_pins.v1',core=module,frame='core R0 origin(0,0)',
                     source='PLANNED canonical clock prototype only; current rr39/35 is NOT a matched physical composite; NOT SIGNED',pins=pins)
            dest.write_text(json.dumps(doc,indent=1)+'\n');h['pins_file']=str(path)
            h['note']+='; PLANNED canonical clock prototype, legacy one-ck view untouched; source/composite/native matching and SIGNED required'
            expected+=count
        t['clock']['core_taps']='early'
        actual=len(S.core_taps(P,tn))
        if actual!=expected:raise ValueError('actual emitted core clock port inventory mismatch')
        changed.append(dict(type=tn,glue_ports_before_density=before,planned_separate_core_ports=actual))
    return dict(schema='opentallas.qc-a0-clock-prototype.v1',status='PLANNED_ONLY_NO_NATIVE_BRIDGE_CREDIT',
                changed=changed,max_assigned_site_snap_L1_um=round(max_snap,4),required_defines=REQUIRED_DEFINES,
                current_functional_leaf_clock_ports=dict(nk_rr=39,nl_rr=35),
                required_data_parameters=dict(G4_ROOTS=1,REGROOT_MODE=3,OT_QWEN_LSL_FP1=False),
                experimental_MODE9_FP1='UNADOPTED: requires separate miter/calendar/boot pricing and fresh source binding',
                source_ownership='canonical A0c ABI/header c51d + inputs/a0_core_taps.json v8; physical A0 owner',
                root_ownership='die clock -> generated clk_c port -> proposed named native A0 clock pin; one shared clock domain',
                corners=dict(TT=dict(model_core_insertion_ps=250,model_early_ps=0),FF=dict(model_core_insertion_ps=202.5,model_early_ps=0)),
                native_per_corner_effect='UNMEASURED, no SIGNED/G4 credit',RTL_or_token_cycles_added=0,
                release_gate='current rr+front composition/source proof + exact native pin/clock profile + child SIGNED + parent contract')
