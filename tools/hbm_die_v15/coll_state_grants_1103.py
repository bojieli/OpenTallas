#!/usr/bin/env python3
"""Reserve source-exact COLL state leaves; complete parent packing remains open."""
import argparse
import hashlib
import json
from pathlib import Path
from leaf_grants_1103 import pins

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_pring_static.sv'
SOURCE_SHA = 'c827fb8dc971baca5e155b88a3381eab218999b127e3a4b9f419f3f28e77d514'


def apply(h):
    assert hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest() == SOURCE_SHA
    h['slots'] = [s for s in h['slots'] if not s.get('coll_state_grant_1103')]
    faces = dict(W=[('lp_we',1),('lp_tag',3),('lp_data',32),('acc_we',1),('acc_tag',3),
                    ('acc_data',32),('carry_we',2),('carry0_tag',3),('carry1_tag',3),
                    ('carry0_src',2),('carry1_src',2),('carry0_data',32),('carry1_data',32),
                    ('read_add',1),('read_tx',1),('read_rr',1),('read_rhs_acc',1),
                    ('read_tx_acc',1),('add_tag',3),('tx_tag',3),('rr_tag',3),('add_src',2)],
                 E=[('rhs_add',32),('carry_add',32),('tx_data',32),('acc_rr',32)], N=[('clk',1)])
    assert sum(b for _, b in faces['W']) == 164
    for q in ('SW','SE','NW','NE'):
        parent = next(s for s in h['slots'] if s['name'] == 'coll_'+q)
        for lane in range(8):
            x, y = 172.8 + 86.4*(lane%4), 432.0 + 86.4*(lane//4)
            assert x+51.84 <= parent['outline']['w'] and y+51.84 <= parent['outline']['h']
            h['slots'].append(dict(name=f'coll_{q}_state{lane}',cell='ot_hgi_coll_pring_static_state_lane',
                source=SOURCE,source_sha256=SOURCE_SHA,source_prerequisite='3729cb8fc',params={},
                instance=f'hb_coll_{q}/u_q/u_ring/g_lane[{lane}]/u_state',
                kind='tile',parent='coll_'+q,outline=dict(w=51.84,h=51.84),
                origin=dict(x=round(x,6),y=y,orient='R0'),
                clock_entry=dict(pin='clk',face='N',layer='M5'),
                clock_source=f'hb_coll_{q}/clk_ring[{lane+1}] -> u_q/u_ring/clk_state[{lane}]',
                clock_domain='stream',clock_period_ps=833.333333,pg_layer='M5',strap_layer='M6',
                signal_max_layer='M5',layer_cap='M5',layer_rule='tile',
                io_budget=dict(in_delay_frac=.2,out_delay_frac=.2),pins=pins(faces,(51.84,51.84)),
                version=1,coll_state_grant_1103=True,measured_std_um2=1058.95998,measured_ff=1664,
                logical_cycles='unchanged state update/read edges',
                reservation_basis='disjoint interior reservation; at least21.6um from writer and parent edges',
                qualification_scope='independent source-exact leaf CTS candidate only; assigned final pin rectangles/native timing/route not yet available; complete COLL parent packing, all incident registered paths and clock delivery OPEN'))
    return h


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();h=apply(json.loads(a.input.read_text()));a.out.write_text(json.dumps(h,indent=1)+'\n')
    print(json.dumps(dict(master='ot_hgi_coll_pring_static_state_lane',replicas=32,source_sha256=SOURCE_SHA)))
