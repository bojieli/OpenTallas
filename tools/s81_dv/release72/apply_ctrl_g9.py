#!/usr/bin/env python3
"""Bind exact CLOSED native-configured CTRL FB; reroute after this source overlay."""
import argparse,copy,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
PACKET=ROOT/'results/arch/s81_die72_1021/g9_assembly/ctrl_first_closed/binding.json'

def apply(plan,table,packet):
    key='dsfd_ctrl_rg3_native32'
    assert key not in table['masters'],'CTRL overlay already present'
    blocks=[b for b in plan['blocks']if b['kind']=='ctrl'];assert len(blocks)==16
    original=table['masters'][blocks[0]['master']]
    assert original['module']==packet['module']=='dsfd_ctrl_rg3' and not original.get('view')
    assert all(table['masters'][b['master']]==original for b in blocks)
    placements={p['instance']:p for p in packet['placements']}
    assert set(placements)=={b['name']for b in blocks}
    for b in blocks:
        p=placements[b['name']];assert [b['x'],b['y']]==p['old_um'],'unexpected CTRL coordinates require fresh whole-view check'
        assert [b['w'],b['h']]==packet['outline_um']
        assert not any(v['offtrack']for v in p['candidate_after']['layers'].values())
    row=copy.deepcopy(original);row.update(view=packet['view'],ref=packet['source_ref'],view_ref=packet['record'],params={},
        view_note='CLOSED exact native-configured FB CTRL; SRAM_FIFO/P192/NATIVE32 explicit. Local resetrelease+1 vsdefaultG8, derivebootdates; no runtimecycle alias.')
    table['masters'][key]=row
    for b in blocks:
        b['master']=key;b['x'],b['y']=placements[b['name']]['candidate_um']
    defines=table.setdefault('defines',[])
    for d in packet['defines']:
        if d not in defines:defines.append(d)
    refs=table.setdefault('rtl_refs',{}).setdefault(packet['source_ref'],[]);prefer=table.setdefault('prefer',[])
    for p in packet['source_sha256']:
        if p not in refs:refs.append(p)
        selected=packet['source_ref']+'/'+p
        if selected not in prefer:prefer.append(selected)
    # Every old route is invalid after source placements change, even by nm.
    for l in plan['links']:
        for ep in l['e']:
            b=plan['blocks'][ep[0]]
            if b['name']in placements:
                p=placements[b['name']];ep[2]=round(ep[2]+p['delta_nm'][0]/1000,4);ep[3]=round(ep[3]+p['delta_nm'][1]/1000,4)
        for f in ('h','sp','s','L','station_dirs'):l.pop(f,None)
    plan['facts']['ctrl_closed_binding']={'master_key':key,'module':packet['module'],'record':packet['record'],'source':packet['source_ref'],'defines':packet['defines'],'instances':16,'physical_scope':'Only exact CLOSED CTRL view, no wholeG9 claim','placement':'All whole-hardview signalpins checked at perinstance R0 nativephase; XYcorrections <=69nm/8nm','reset_contract':packet['reset_contract'],'routing_status':'Fresh819route construction +actualpinprojection/peerPHYclocks required; no oldcalendar'}
    physical=plan['facts'].setdefault('physical72',{});physical.update(routing='INVALIDATED_BY_CTRL_CONFIGURED_SOURCE_AND_PHASE_OVERLAY',calendar='UNQUALIFIED; resetboot/source/view/pinprojection changed, no inherited dates')
    if 'stage_map' in plan['facts']:
        capacity=plan['facts'].pop('stage_map');capacity['bound_by']='CAPACITY INVENTORY ONLY; no inherited schedule/calendar qualification';plan['facts']['stage_map_capacity_only']=capacity
    for f in ('relays','relay_bit_stages','bit_mm','relay_channels_seed','phase_path_stages','scalar_exchange_stages'):plan['facts'].pop(f,None)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',required=True,type=Path);ap.add_argument('--table',required=True,type=Path);ap.add_argument('--packet',type=Path,default=PACKET);a=ap.parse_args()
    packet=json.loads(a.packet.read_text())
    for name,h in packet['view_sha256'].items():assert hashlib.sha256((ROOT/packet['view']/name).read_bytes()).hexdigest()==h,'exact CLOSED viewhash mismatch'
    plan=json.loads(a.plan.read_text());table=json.loads(a.table.read_text());apply(plan,table,packet);a.plan.write_text(json.dumps(plan,indent=1)+'\n');a.table.write_text(json.dumps(table,indent=1)+'\n');print('G9_CTRL_BOUND16 exactnativeconfiguredCLOSED FB; reroute+bootcalendar owed')
if __name__=='__main__':main()
