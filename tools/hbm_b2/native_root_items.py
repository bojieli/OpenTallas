#!/usr/bin/env python3
"""B2o root neighbour binding: ep_S1 pass-through and both-half run identity.
The root relay owns one cycle in each direction; plan relay insertion must
subtract that owned stage from the corresponding L153/L154 path budget.
"""
import argparse,json
from pathlib import Path

def apply(d, router_params):
    rb=d['rebuild'];rm=d['remaster'];ap=d['add_ports'];ow=d['out_width']
    rm.setdefault('hb_router_ids',dict(params=router_params))['master']='ot_hbm_router_ids_static_2src'
    ap.setdefault('hb_router_ids',{}).update(run1_v='in',run1_layer='in')
    rb.setdefault('hb_router_ids',{}).update(run1_v=[['cp_svg_NW4','run_v',0,0]],run1_layer=[['cp_svg_NW4','run_arg',0,7]])
    r='b2_ep1_root'
    d.setdefault('add_instances',{})[r]=dict(master='ot_hbm_b2_ep_root_relay',params='',
        ports=dict(clk='in',rst_n='in',rx_i='in',tx_i='in',rx_o='out',tx_o='out'))
    ow[r]=dict(rx_o=615,tx_o=632)
    rx=[['ep_S1','rx_pin_flit',0,611],['ep_S1','rx_pin_v',0,0],['ep_S1','phy_up',0,0],['ep_S1','fault',0,0]]
    ep=rb['ep_S1'];tx=ep['tx_frame']+ep['tx_v']+[['epcal_NW','payload',38,56]]
    offsets=dict(rx_pin_flit=0,rx_pin_v=612,phy_up=613,fault=614)
    for n,ports in rb.items():
        for p,segs in ports.items():
            ports[p]=[[r,'rx_o',offsets[s[1]]+s[2],offsets[s[1]]+s[3]]
                      if s[0]=='ep_S1' and s[1] in offsets else s for s in segs]
    ep['tx_frame']=[[r,'tx_o',0,611]];ep['tx_v']=[[r,'tx_o',612,612]]
    for p,(o,w) in dict(rx_arm_v=(0,1),rx_arm_bank=(1,1),rx_block_words=(2,7),rx_release_v=(9,1),
                       rx_release_bank=(10,1),rx_slot_v=(11,1),rx_slot_bank=(12,1),rx_slot_index=(13,6)).items():
        ep[p]=[[r,'tx_o',613+o,613+o+w-1]]
    rb[r]=dict(clk=[['hb_ckgen','pll_stream',0,0]],rst_n=[['hb_ckgen','por_stream',0,0]],rx_i=rx,tx_i=tx)
    d['items'].append(dict(id='R-ROOT-NEIGHBOUR',status='implemented; bit-exact benches and strict bind required',
        what='ep_S1 615bRX/632bTX root pass-through; router run identity source0cp_svg_NW0/source1cp_svg_NW4',
        census_additions={r:'root'},owned_transport_stages={r:dict(rx=1,tx=1)},
        latency='ep_S1 +1 edge each direction (owned plan stage); router source select +0 edges'))
    return d

def main():
    p=argparse.ArgumentParser();p.add_argument('delta');p.add_argument('--out',required=True);a=p.parse_args()
    from b2_top import Die
    die=Die('physical/die_plan/hbm/bind/inputs/die_r18h5.v.gz',[])
    d=apply(json.loads(Path(a.delta).read_text()),die.insts['hb_router_ids']['params']);Path(a.out).write_text(json.dumps(d,indent=1));print('NATIVE_ROOT_BIND',d['items'][-1])
if __name__=='__main__':main()
