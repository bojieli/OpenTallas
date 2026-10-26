#!/usr/bin/env python3
"""Connect native MoE TOPK write packets to relative SVGs; never fabricate ID data.

This produces a structural successor contract. Physical grants, landed relay generation,
real TOPK compiler launch, and scoped-source rebind remain required before qualification.
"""
import argparse
import copy
import json
import re
from pathlib import Path

SRC = 'rtl/hbm_accel/loader/service_native/ot_hbm_router_ids_static.sv'
FIELDS = [('topk_k',0,4),('topk_order',4,1),('topk_n',5,20),('topk_m',25,20),
 ('topk_a_mirror',45,1),('topk_a_base',46,18),('topk_a_str',64,18),
 ('topk_o_mirror',82,1),('topk_o_base',83,18),('topk_o_str',101,18),
 ('topk_has_r',119,1),('topk_r_base',120,18),('topk_r_str',138,18)]


def integrate(original):
    d = copy.deepcopy(original)
    name = 'hb_router_ids'
    if name in d['instances']:
        raise ValueError('l17 already installed; regenerate from immutable l15/l16 input')
    inst = d['instances']
    ctl = inst['hb_idx__ctl']
    master = ctl['master']
    if master not in ('ot_hbm_idx_rootctl_static_am','ot_hbm_idx_rootctl_static_am_pin'):
        raise ValueError('unpriced TOPK master ' + master)
    vm_rt = int(ctl.get('params', {}).get('VM_RT', 1 if master.endswith('_pin') else 0))
    xrt = 1 + vm_rt
    ports = {p:dict(direction='input',bits=w) for p,w in
             [('clk',1),('rst_n',1),('run_v',1),('run_layer',8),('topk_go',1),
              ('topk_rec',156),('cq',338),('cq_seq',2)]}
    ports.update({p:dict(direction='output',bits=w) for p,w in
                  [('ids_v',1),('ids_layer',8),('ids',54),('ids_cohort',16),('fault',1)]})
    inst[name] = dict(master='ot_hbm_router_ids_static',source=SRC,params=dict(XRT=xrt,GO_DELAY=1,CQ_DELAY=1),
                      slot='router_ids',region='l17_router_ids',owner='HBM-ROUTER-IDS-CODEX',ports=ports,
                      note='real TOPK CQ capture; 79-bit landed broadcast, CP whole-layer run identity')

    def edge(source,sink):
        assert source[3]-source[2] == sink[3]-sink[2]
        d['edges'].append(dict(name=f'l17_{sink[0]}_{sink[1]}_{sink[2]}',bits=sink[3]-sink[2],source=source,sink=sink,
                              clock='stream',ready_or_credit=False,allowed_exception=None,
                              basis='actual CP launch / native TOPK VM-write producer',region='l17_router_ids'))

    def driver(i,p):
        rows = [e for e in original['edges'] if e['sink'][:2] == [i,p]]
        if len(rows)!=1 or rows[0]['sink'][2]!=0:
            raise ValueError(f'{i}.{p}: unique full source required')
        return rows[0]['source']

    edge(['cp_svg_SW0','run_v',0,1],[name,'run_v',0,1])
    if inst['cp_svg_SW0']['ports'].get('run_arg',{}).get('bits')!=8:
        raise ValueError('l15 relative CP run_arg8 required')
    edge(['cp_svg_SW0','run_arg',0,8],[name,'run_layer',0,8])
    edge(driver('hb_idx__ctl','topk_go'),[name,'topk_go',0,1])
    for p,lo,w in FIELDS:
        edge(driver('hb_idx__ctl',p),[name,'topk_rec',lo,lo+w])
    edge(['hb_idx__ctl','cq',0,338],[name,'cq',0,338])
    edge(['hb_idx__ctl','cq_seq',0,2],[name,'cq_seq',0,2])
    svgs=sorted(n for n in inst if re.fullmatch(r'svg_(SW|NW)[0-7]',n))
    if len(svgs)!=16:
        raise ValueError('16 relative SVG sinks required')
    for n in svgs:
        if inst[n]['master']!='ot_hbm_svc_sm_group_rel_id':
            raise ValueError(n+': l15 relative master required')
        inst[n]['params']['ID_COHORT']=1
        for p,w in [('ids_v',1),('ids_layer',8),('ids',54),('ids_cohort',16)]:
            if any(e['sink'][:2]==[n,p] for e in d['edges']):
                raise ValueError(n+'.'+p+': prior ID driver must not survive')
            inst[n]['ports'][p]=dict(direction='input',bits=w)
            edge([name,p,0,w],[n,p,0,w])
    for kind,port in [('clock','clk'),('reset','rst_n')]:
        rows=[r for r in d['clock_resets'] if r['instance']=='hb_idx__ctl' and r['port']==port]
        if len(rows)!=1:raise ValueError('missing native TOPK '+port)
        r=copy.deepcopy(rows[0]);r.update(instance=name,port=port);d['clock_resets'].append(r)
    d['die_pins'].append(dict(name=name+'__fault',direction='output',bits=1,instance=name,port='fault'))
    for gap in d.get('gaps',[]):
        if gap.get('id')=='G-SMB-ROUTER-IDS':
            gap.update(affects=[],missing_rtl='native CQ collector connected; physical broadcast/grant and actual compiler timing open',
                       undriven_ports=0,undriven_bits=0)
    report=dict(status='STRUCTURAL_ONLY_PHYSICAL_AND_COMPILER_OPEN',collector=name,sinks=svgs,
                source_master=master,xrt=xrt,go_delay=1,cq_delay=1,
                cq_edge_from_go=138+xrt+2,ids_publication_after_cq=2,
                identity='CP whole-layer accepted run count, reset=0; post-run native IDs only',
                boundary_bits_per_result=79,peak_bits_per_cycle=79,fanout_per_bit=16,
                obligations=['router_ids exact physical grant','79-bit registered/landed broadcast <=405um hops',
                             'matched CP run launch count at all 16 issuers','actual router_act and TOPK compiler image',
                             'finite latest-ID deadline before first expert reserve','source-bound native TT/FF closure'])
    return d, report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('contract');ap.add_argument('out');ap.add_argument('--report',required=True)
    a=ap.parse_args()
    d,r=integrate(json.loads(Path(a.contract).read_text()))
    Path(a.out).write_text(json.dumps(d,separators=(',',':'))+'\n')
    Path(a.report).write_text(json.dumps(r,indent=2)+'\n')
    print('L17_ROUTER_IDS_STRUCTURAL_ONLY sinks=16 native_CQ=1 cohort=16')


if __name__=='__main__':main()
