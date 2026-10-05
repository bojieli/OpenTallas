#!/usr/bin/env python3
"""Terminal complete-map survival gate; gives no CTS/SSFF/P&R credit."""
import argparse,hashlib,json,re
from pathlib import Path
TOP='ot_qwen_rom_fulltile_tp4_context_top'

def ff_endpoints(net,bits):
    drivers={};links={}
    for name,c in net['cells'].items():
        con=c['connections'];kind=c['type']
        if kind.startswith('DFF') and kind.endswith('_ASAP7_75t_R'):
            for pin in ('Q','QN'):
                for b in con.get(pin,[]):
                    if b in drivers:raise ValueError('multiply driven FF bit')
                    drivers[b]=name
        elif kind.startswith(('INV','BUF')) and kind.endswith('_ASAP7_75t_R'):
            if len(con.get('A',[]))==len(con.get('Y',[]))==1:links[con['Y'][0]]=con['A'][0]
    endpoints=[]
    for b in bits:
        seen=set()
        while b not in drivers and b in links:
            if b in seen:raise ValueError('cyclic endpoint path')
            seen.add(b);b=links[b]
        if b not in drivers:raise ValueError('register bit has no actual mapped FF')
        endpoints.append(drivers[b])
    if len(set(endpoints))!=len(bits):raise ValueError('replicas merged or aliased')
    return endpoints


def check(work):
    terminal=json.loads((work/'terminal.json').read_text())
    if terminal['status']!='PASS_COMPLETE_SOURCE_MAP_ONLY_CONTEXT_OPEN':raise ValueError('complete source map did not PASS')
    pins=json.loads((work/'sourcepins.json').read_text());assert pins['SMIN']==6
    net=json.loads((work/'mapped.json').read_text())['modules'][TOP]
    def selected(pattern,expected):
        bits=[b for name,n in net['netnames'].items() if re.fullmatch(pattern,name) for b in n['bits']]
        if len(bits)!=expected:raise ValueError('missing target register nets '+pattern)
        return ff_endpoints(net,bits)
    base=r'u_tile\.u_logic\.'
    endpoints={
      'ROM_capture':selected(base+r'g_pair\[[01]\]\.g_bank\[[0-4]\]\.g_cap\.g_direct\.cap',2560),
      'mask':selected(base+r'g_pair\[[01]\]\.g_bank\[[0-4]\]\.g_cap\.g_direct\.g_mask\[[0-7]\]\.local_sel',80),
      'bank_strobe':selected(base+r'code_rd_bank',5),
      'early_select':selected(base+r'code_sel_q',5),
      'KV_capture':selected(base+r'g_kv_local\.g_kvcap\.cap',512),
      'address_producer':selected(base+r'u_me\.wrom_addr',24),
      'read_producer':selected(base+r'u_me\.wrom_re',1)}
    macro_counts={n:sum(c['type']==n for c in net['cells'].values()) for n in ('ot_rom_4096x266_m8','ot_sram_1r1w_128x256_m1_r2c2')}
    assert list(macro_counts.values())==[10,2]
    tree=[name for name,c in net['cells'].items() if '.u_tree.' in name and c['type']=='BUFx4_ASAP7_75t_R']
    if len(tree)!=76:raise ValueError('actual source distribution76BUF did not survive')
    model=json.loads((work/'model.json').read_text())
    assert terminal['mapped_cell_area_um2']<=model['slot']['complete_cell_area_ceiling_um2']
    return dict(status='PASS_COMPLETE_MAPPED_SURVIVAL_ONLY',source_commit=pins['commit'],
      files={name:hashlib.sha256((work/name).read_bytes()).hexdigest() for name in ('terminal.json','mapped.json','mapped.v','sourcepins.json','model.json')},
      macro_counts=macro_counts,FF_endpoints=endpoints,source_distribution_buffers=tree,
      mapped_cell_area_um2=terminal['mapped_cell_area_um2'],
      source_root_reset_producer_installed=False,CTS_installed=False,contextual_SSFF=False,P_and_R_admitted=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise SystemExit('refuse overwrite')
    try: result=check(a.work)
    except Exception as e:result=dict(status='FAIL_OR_INCOMPLETE_RETAINED',reason=str(e),contextual_SSFF=False,P_and_R_admitted=False)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
    raise SystemExit(0 if result['status'].startswith('PASS') else 1)
