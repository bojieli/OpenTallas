#!/usr/bin/env python3
"""Inventory real flattened RTL reset loads; does not qualify hard-child views."""
import argparse
from collections import Counter, defaultdict
import json
import re
from pathlib import Path


def block(name):
    # Flattened Yosys names retain full instance paths. Preserve each raw path
    # in the receipt as well; these bins are explanatory, not view waivers.
    for token,label in [('u_amax','amax_soft'),('u_scalar','scalar_soft'),
                        ('u_sc.','scalar_soft'),('u_stn','station_soft'),
                        ('u_vm','vm_soft'),('u_stream','stream_soft'),
                        ('u_str.','stream_soft'),('u_stm.','stream_soft'),('u_su.g_lane','lane_rtl_included'),
                        ('u_hd','head_rtl_included')]:
        if token in name:return label
    return 'other_soft_or_unclassified'


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('netlist');ap.add_argument('--top',default='qfd_dv_slice2_w')
    ap.add_argument('--out',required=True);a=ap.parse_args()
    design=json.loads(Path(a.netlist).read_text());m=design['modules'][a.top]
    aliases=defaultdict(list)
    for name,n in m['netnames'].items():
        for idx,b in enumerate(n['bits']):
            if isinstance(b,int):aliases[b].append(name+(f'[{idx}]' if len(n['bits'])>1 else ''))
    loads=defaultdict(list);rloads=defaultdict(list);types=Counter()
    for name,c in m['cells'].items():
        types[c['type']]+=1
        for pin,bits in c['connections'].items():
            if c.get('port_directions',{}).get(pin)!='input':continue
            for b in bits:
                if not isinstance(b,int):continue
                loads[b].append((name,pin))
                if pin in ('R','ARST','SRST','CLR','RESET','RST','rst','rst_n'):
                    rloads[b].append((name,pin))
    rows=[]
    for b,rs in rloads.items():
        names=sorted(aliases[b],key=lambda s:(s.startswith('$'),len(s),s))
        rows.append(dict(bit=b,names=names[:24],reset_pin_loads=len(rs),
                         all_input_pin_loads=len(loads[b]),
                         reset_load_blocks=dict(Counter(block(n) for n,p in rs)),
                         reset_load_examples=[dict(cell=n,pin=p) for n,p in rs[:40]],
                         all_load_blocks=dict(Counter(block(n) for n,p in loads[b]))))
    rows.sort(key=lambda x:(-x['all_input_pin_loads'],-x['reset_pin_loads']))
    result=dict(status='RTL_INVENTORY_NOT_NATIVE_TIMING_SIGNOFF',top=a.top,
                cells=len(m['cells']),cell_types=dict(types),reset_nets=rows,
                note='All real lane/head/SFU RTL was flattened; closed hard-child internal loads are included here for diagnosis only. Parent hard-bound load is one pin per matching native instance. New ML5 heads require new closure.',
                named_reset_total_load_excess=[dict(bit=b,names=sorted(aliases[b])[:12],loads=len(ls))
                    for b,ls in loads.items() if len(ls)>32 and
                    any(re.search(r'rst|reset|rsafe',n,re.I) for n in aliases[b])])
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cells=result['cells'],reset_nets=len(rows),
                         over32=sum(r['all_input_pin_loads']>32 for r in rows),
                         worst=rows[:10]),indent=2))


if __name__=='__main__':main()
