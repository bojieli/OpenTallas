#!/usr/bin/env python3
"""Native VM ABI + nine scalar local clock entries; no old hard-view alias.

Uses the current270um cap-M6 bank grant and leaves data on its assigned peer
face, including the explicit native read remap and additional SM writer.
Native physical clock closure remains the consuming kit owner's obligation.
"""
import argparse
import copy
import hashlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import hbm_die_views as V

CLOCKS=dict(clk_pin=('W',135),clk_ctrl=('N',135),clk_s1=('W',137),clk_s2=('W',139),
            clk_ecc=('E',135),clk_out=('E',137),clk_ma=('W',30.012),
            clk_mb=('W',100.524),clk_mc=('W',171.036))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-ref',required=True)
    ap.add_argument('--template-ref',default='origin/main')
    ap.add_argument('--out',default='results/arch/hbm_die_v15/vm_native_local_grants_1016.json')
    a=ap.parse_args()
    blob=lambda ref,path:subprocess.check_output(['git','-C',str(ROOT),'show',f'{ref}:{path}'])
    template_path='results/arch/hbm_die_v15/vm_strap_grants_2210.json'
    raw=blob(a.template_ref,template_path);old=json.loads(raw)
    slots=[]
    for q in range(4):
        s=copy.deepcopy(old['slots'][q]);source=f'rtl/hbm_accel/generic/vm/static/physical/hfd_vms_bank_local_q{q}.sv'
        data=blob(a.source_ref,source)
        with tempfile.NamedTemporaryFile(suffix='.sv') as f:
            f.write(data);f.flush();ports=V.L.parse_module(f.name,f'hfd_vms_bank_local_q{q}',{})['ports']
        assert set(CLOCKS)<=set(ports) and 'clk' not in ports
        mapping={}
        for pin in s['pins']:
            name=pin['name'].split('[')[0]
            if name=='clk':continue
            if q>=2:
                if name in ['rq3','rr3']:continue
                if name in ['rq4','rr4']:name=name[:2]+'3'
                elif name in ['rq5','rr5']:name=name[:2]+'4'
            mapping[name]=pin['face']
        if q<2:mapping.update(wq1='E',wq_done1='E')
        assert set(mapping)|set(CLOCKS)==set(ports),(q,set(ports)-(set(mapping)|set(CLOCKS)),set(mapping)-set(ports))
        pins=[];used={f:[] for f in 'NSEW'}
        def center(pos):return round(.012+round((pos-.012)/.048)*.048,6)
        # Explicit local clock roles, all distinct registered/root ports.
        for name,(face,want) in CLOCKS.items():
            pos=center(want);used[face].append(pos)
            pins.append(dict(name=name,face=face,layer='M5' if face in 'NS' else 'M4',offset=pos,
                             span_um=[round(pos-.048,6),round(pos+.048,6)],bit_centres_um=[pos],bit_pitch_um=.096,
                             role='raw_macro_clock' if name in ['clk_ma','clk_mb','clk_mc'] else 'local_root_clock'))
        for face in 'NSEW':
            names=[n for n,f in mapping.items() if f==face]
            # Keep reset/straps near the old north root; spread all payloads.
            controls=[n for n in ['rst_n','bid','sid'] if n in names]
            cursor=135.18
            for name in controls:
                bits=ports[name][1];cs=[]
                for k in range(bits):
                    pos=center(cursor);cursor=pos+.192;used[face].append(pos);cs.append(pos)
                pins.append(dict(name=name if bits==1 else f'{name}[{bits-1}:0]',face=face,layer='M5',
                                 offset=(cs[0]+cs[-1])/2,span_um=[cs[0]-.048,cs[-1]+.048],
                                 bit_centres_um=cs,bit_pitch_um=.192))
            names=[n for n in names if n not in controls]
            count=sum(ports[n][1] for n in names)
            avail=[]
            for spacing in [.192,.144]:
                avail=[]
                for k in range(math.ceil((2.2-.012)/.048),math.floor((267.8-.012)/.048)+1):
                    pos=round(.012+k*.048,6)
                    if all(abs(pos-c)>=.192-1e-8 for c in used[face]) and (not avail or pos-avail[-1]>=spacing-1e-8):avail.append(pos)
                if len(avail)>=count:break
            assert len(avail)>=count,(q,face,count,len(avail))
            pick=[avail[round(i*(len(avail)-1)/(count-1))] for i in range(count)] if count>1 else avail[len(avail)//2:len(avail)//2+count]
            cursor=0
            for name in names:
                bits=ports[name][1];cs=pick[cursor:cursor+bits];cursor+=bits
                pins.append(dict(name=name if bits==1 else f'{name}[{bits-1}:0]',face=face,
                                 layer='M5' if face in 'NS' else 'M4',offset=round((cs[0]+cs[-1])/2,6),
                                 span_um=[round(cs[0]-.048,6),round(cs[-1]+.048,6)],bit_centres_um=cs,
                                 bit_pitch_um=min([b-a for a,b in zip(cs,cs[1:])] or [.192])))
        for f in 'NSEW':
            cs=sorted(c for p in pins if p['face']==f for c in p['bit_centres_um'])
            assert len(cs)==len(set(cs)) and all(b-a>=.096-1e-8 for a,b in zip(cs,cs[1:]))
        entries=[dict(pin=n,face=f,layer='M5' if f in 'NS' else 'M4',offset=center(pos),
                      role='raw_liberty_reference' if n in ['clk_ma','clk_mb','clk_mc'] else 'phi_minus_measured_R_required')
                 for n,(f,pos) in CLOCKS.items()]
        s.update(cell=f'hfd_vms_bank_local_q{q}',source=source,source_sha256=hashlib.sha256(data).hexdigest(),
                 source_prerequisite=a.source_ref,pins=pins,clock_entry=entries[0],clock_entries=entries,
                 pin_status='SOURCE_PINNED_LOCAL_CLOCK_CANDIDATE_NO_VIEW',physical_view=None,
                 face_density={f:round(sum(len(p['bit_centres_um']) for p in pins if p['face']==f)*.096/270,5) for f in 'NSEW'},
                 scope='Distinct native ABI + six independent soft roots and three direct raw macro clocks; no old CLOSED alias.',
                 grant='native_vm_nine_scalar_clock_proposal_1016',version=1)
        s['name']=f'vmb_{("SW","SE","NW","NE")[q]}_local_clock_master'
        for stale in ['instance_homes','status_cycles_added','data_cycles_added']:
            s.pop(stale,None)
        s['minimum_nonclock_bit_pitch_um']=round(min(b-a for p in pins if p['name'] not in CLOCKS
                                                     for a,b in zip(p['bit_centres_um'],p['bit_centres_um'][1:])),6)
        s['pin_assignment_note']='Exact source ABI coverage; full-face payload spread, 0.012+0.048k track centres, >=0.144um data pitch; nine scalar clock entries reserved. Actual native kit ODB/PG readback mandatory.'
        s['cycle_delta_from_native_abi']=0
        s['native_abi_baseline_ref']='ce05a10ee'
        s['global_instance_homes']='UNBOUND: parent/die adoption and current geometry required'
        s['pin_ranges']={p['name']:p['span_um'] for p in pins}
        assert max(s['face_density'].values())<=.60
        slots.append(s)
    out=dict(schema='opentallas.hier_contract.v1',die='hbm_v15',slots=slots,source_ref=a.source_ref,
             template_path=template_path,template_sha256=hashlib.sha256(raw).hexdigest(),
             canonical_die_contract_mutated=False,production_binding_adopted=False,qualification=False,
             layer_obligation='Retain current270um M6PG/M6cap bank grant; data pins M4/M5, no M5 PG stripes. Actual ODB readback mandatory.',
             clock_obligation='Every root gets actual phi-R from its own measured insertion; raw macro clocks use Liberty reference, not a common pin phase.')
    path=ROOT/a.out;path.parent.mkdir(exist_ok=True,parents=True);path.write_text(json.dumps(out,indent=1)+'\n')
    print(json.dumps({s['cell']:s['face_density'] for s in slots}))


if __name__=='__main__':main()
