#!/usr/bin/env python3
"""Apply actual SU cuts to one QC plan event, keeping every outline and origin.

Run AFTER bind.py emits the canonical parameter-qualified SU wrappers. Both the
physical pin tables and the grouped bound frames are products of that same cut.
Never replace those frames with bind output from before this transformation.
"""
import argparse
import collections
import copy
import json
import re
from pathlib import Path
import qc_su_lane_cut as C


def output_roles(source):
    widths = {n: int(h)+1 if h else 1 for h,n in C.WIRE.findall(source)}
    result = collections.defaultdict(set)
    for name, expr in re.findall(r'u_bout_(\w+).*?\.d\((.*?)\), \.ea', source):
        role = ('c_o' if 'su_c' in name or 'flt' in name else 'ctl_o' if 'ctl' in name else
                'stm_o' if 'stm' in name else 'sc_o' if 'sc' in name else None)
        if role is None:
            continue
        for n, bits in C.refs(expr, widths).items():
            for bit in bits:
                result[n,bit].add(role)
    return result


def pins_for_cut(old, report, source, outline):
    slots = collections.defaultdict(list)
    for p in old:
        m = re.fullmatch(r'(\w+)\[(\d+)\]',p['name'])
        if m:
            slots[m[1]].append((int(m[2]),p))
    slots = {k: [p for _,p in sorted(v)] for k,v in slots.items()}
    if len(slots.get('c_i',[])) != report['input_bits']:
        raise ValueError('actual SU input count does not match the approved input-slot capacity')
    roles = output_roles(source)
    out = [dict(p, name=f'c_i[{i}]',direction='input') for i,p in enumerate(slots['c_i'])]
    used = collections.Counter()
    for i,q in enumerate(report['outputs']):
        ds = roles[q['name'],q['bit']]
        # Pick an existing slot facing a real consumer. Aliases to other sinks remain
        # parent wiring, not duplicate output pins or tie-offs on the hardened core.
        role = next((x for x in ('c_o','ctl_o','stm_o','sc_o') if x in ds),None)
        if role is None or used[role] >= len(slots.get(role,[])):
            raise ValueError(f'no approved source-facing pin slot for {q}: {sorted(ds)}')
        out.append(dict(slots[role][used[role]],name=f'c_o[{i}]',direction='output'))
        used[role] += 1
    w,h = outline
    def control(name,x):
        x = .024 + round((x-.024)/.048)*.048
        for _ in range(100):
            if all(abs(p['x']-x)>.192 or abs(p['y']-(h-.096))>.192 for p in out):
                out.append(dict(name=name,layer='M5',x=round(x,4),y=round(h-.096,4),direction='input'))
                return
            x += .048
        raise ValueError('no free north-face clock/reset pin site')
    control('clk',w/2)
    control('rst_n',w/2+.864)
    return out,dict(used)


def apply(plan, plan_dir, bound_dir, outdir, alignment=3):
    result=copy.deepcopy(plan)
    ledger=[]
    for tn,t in sorted(result['partition_types'].items()):
        if tn not in ('sle_su_l0','sle_su_l1','slw_su_l0','slw_su_l1'):
            continue
        p=bound_dir/'rtl'/(t['module']+'.sv')
        source=p.read_text()
        original=source
        for hc in t['hard_cores']:
            m=re.fullmatch(r'u_lane(\d+)',hc['inst'])
            if not m:
                raise ValueError(f'{tn}: unexpected SU hard-core group {hc["inst"]}')
            lane=int(m[1]); mod=f'qfd_qc_su_lane_{tn[2]}_l{lane}'
            rtl,frame,report=C.cut(source,lane,mod,memory_alignment=alignment)
            old=json.loads((plan_dir/hc['pins_file']).read_text())['pins']
            pins,roles=pins_for_cut(old,report,original,hc['outline_um'])
            rel=Path('cores/su_exact')/(tn+'_'+hc['inst']+'_pins.json')
            dst=outdir/rel;dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_text(json.dumps(dict(schema='opentallas.core_pins.v1',core=mod,pins=pins,
                                         source='exact bound SU cut; original physical pin slots'),indent=1)+'\n')
            rd=outdir/'rtl';rd.mkdir(parents=True,exist_ok=True)
            (rd/(mod+'.sv')).write_text(rtl)
            (rd/(mod+'.cut.json')).write_text(json.dumps(report,indent=1)+'\n')
            hc.update(module=mod,pins_file=str(rel),note='Exact five-leaf source group;0 added cycles; dedicated face gates required')
            ledger.append(dict(type=tn,instance=hc['inst'],module=mod,inputs=report['input_bits'],
                               outputs=report['output_bits'],output_slot_families=roles,added_cycles=0,
                               memory_alignment=report['memory_alignment'],outline_um=hc['outline_um'],origin_um=hc['origin_um']))
            source=frame
        (outdir/'rtl'/p.name).write_text(source)
    if len(ledger)!=16:
        raise ValueError(f'expected16 real SU lane groups, found{len(ledger)}')
    return result,ledger


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--bound',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--memory-alignment',type=int,default=3)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    plan,ledger=apply(json.loads(a.plan.read_text()),a.plan.parent,a.bound,a.out,a.memory_alignment)
    (a.out/'die_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    (a.out/'su_cut_ledger.json').write_text(json.dumps(ledger,indent=1)+'\n')
    print(f'EXACT_SU_CUT groups{len(ledger)} added_cycles0 alignment{a.memory_alignment}; raw face gates and G0/G2/review remain')


if __name__=='__main__':
    main()
