#!/usr/bin/env python3
"""Produce unrouted BE target contacts; never export a wired successor view."""
import argparse,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import child_lint as C
import abstract_pin_stub as A

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--kit',type=Path);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    source=ROOT/'results/arch/s81_be_native_mc_placement_1014/inputs/be_sl_c15e2bf6a.lef';s=source.read_text();model=C.parse_lef(s);head,_=A.split_lef(s);changes=[]
    moved={'bl_d[1000]':('M4',302.208,6.,302.4,6.024),'cks[0]':('M4',302.208,6.48,302.4,6.504)}
    def pin(match):
        name,body=match.group(1),match.group(2)
        if model['pins'][name]['use']!='SIGNAL':return match.group(0)
        old=model['pins'][name]['rects'];new=[]
        for r in old:
            layer,x,y,u,v=r
            if name in moved:r=moved[name]
            elif layer=='M5':cx=(x+u)/2;r=(layer,cx-.036,y,cx+.036,v)
            elif layer=='M7':r=(layer,x+.016,y,u+.016,v)
            new.append(r)
        if new!=old:changes.append(dict(pin=name,old=old,target=new,old_face=C.face_of(old[0],model['W'],model['H']),target_face=C.face_of(new[0],model['W'],model['H'])))
        geometry=''.join('      LAYER '+r[0]+' ;\n        RECT '+' '.join(f'{v:.6f}' for v in r[1:])+' ;\n' for r in new)
        body=re.sub(r'    PORT\n.*?    END','    PORT\n'+geometry+'    END',body,flags=re.S)
        return '  PIN '+name+'\n'+body+'\n  END '+name
    head=re.sub(r'  PIN (\S+)\n(.*?)\n  END \1',pin,head,flags=re.S)
    text='# UNROUTED TARGET CONTACTS ONLY; no electrical connection or routed OBS qualification.\n'+head+'\n  OBS\n  END\nEND dsfd_vm_be_sl\nEND LIBRARY\n'
    lef=a.out/'target_contacts_unrouted.lef';lef.write_text(text);after=C.parse_lef(text);assert set(after['pins'])==set(model['pins'])
    contacts=[]
    for n,p in after['pins'].items():
        if p['use']=='SIGNAL':
            assert len(p['rects'])==1
            r=p['rects'][0];contacts.append((n,*r))
    assert len(contacts)==4094
    io=''.join('place_pin -pin_name {'+n+'} -layer '+l+' -location {'+f'{(x+u)/2:.6f} {(y+v)/2:.6f}'+'} -pin_size {'+f'{u-x:.6f} {v-y:.6f}'+'}\n' for n,l,x,y,u,v in contacts)
    (a.out/'io_place.tcl').write_text(io)
    ports={}
    for r in contacts:ports.setdefault(re.sub(r'\[\d+\]$','',r[0]),{'pins':[]})['pins'].append(r)
    for p in ports.values():
        layers={r[1] for r in p['pins']};p['layer']=next(iter(layers)) if len(layers)==1 else 'MIXED'
    portjson=dict(master='dsfd_vm_be_sl',die='be_access_m7_candidate',w_um=302.4,h_um=92.88,obs_top=7,domain='serial0p9/stream1p2 actuallegacyclocks',ports=ports)
    (a.out/'ports.json').write_text(json.dumps(portjson,indent=2)+'\n')
    if a.kit:
        (a.kit/'io_place.tcl').write_text(io);(a.kit/'ports.json').write_text(json.dumps(portjson,indent=2)+'\n')
    mapping=[]
    plan=json.loads((ROOT/'results/arch/s81_be_native_mc_placement_1014/request.json').read_text())
    changed={r['pin']:r for r in changes}
    for pair in plan['pairs']:
        for side in ['source','destination']:
            ep=pair.get(side+'_endpoint',{})
            if ep.get('master')=='dsfd_vm_be_sl' and ep.get('pin') in changed:mapping.append(dict(net=pair['net'],side=side,endpoint=ep,change=changed[ep['pin']],qualified=False))
    for sl in range(4):
        mapping.append(dict(instance=f'g_s[{sl}].u_sl',pin='bl_d[1000]',parent=f't_bl[{3696+128*sl}]',rtl_line=1674,local_target=moved['bl_d[1000]'],requested_VM_target=[64.8+475.2*sl+302.304,21.6+6.012],destination_physical_pin='OPEN; die f_capture manifest cannot be inferred as this endpoint',qualified=False))
    record=dict(schema='opentallas.be_pinface_successor_request.v1',status='REQUESTED_UNALLOCATED_UNROUTED',top='dsfd_vm_be_sl',outline_um=[302.4,92.88],actual_cap='M7',parent_strap='M8',source_LEF_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),changes=changes,changed_contacts=len(changes),signal_contacts=4094,
        physical_fix='Two measured failed pins move to E/M4; all S/M5 contacts widen24→72nm (96nm pitch retains24nm gap); all N/M7 signal contacts shift+16nm to align global VM origin14036.112 plus requested BE R0 x64.8+475.2s with actual M7 .016/.064 track grid. Full-depth72nm above-layerhalo and inward M5 PG stripe remain required.',
        candidate_VM_global_origin_um=[14036.112,12804.48],parent_requested_origin_um=[64.8,21.6],parent_requested_pitch_um=475.2,parent_pair_mapping=mapping,rtl_state_latency_changed=False,raw_route_connectivity_verified=False,old_CLOSED_replaced=False,global_clock_reset_source_bound=False,strict_lint_AP_scope='target-contact geometric feasibility only; no internal signal OBS or routed connectivity represented; fresh raw-route lint/AP/SS/FF/DRC required')
    (a.out/'request.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:record[k] for k in ['status','changed_contacts','signal_contacts']}))
if __name__=='__main__':main()
