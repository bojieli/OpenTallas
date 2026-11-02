"""Read-only extraction of the actual QC SerDes domain boundary; no RTL rewrite."""
import argparse
import hashlib
import json
from pathlib import Path
import re

p=argparse.ArgumentParser()
p.add_argument('--source',type=Path,required=True)
p.add_argument('--bound',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
raw=json.loads((a.bound/'asbuilt.json').read_text())
top=raw['modules']['qfd_die']
clock_rx=top['cells']['clk_rx']['connections']
roots={bits[0]:name for name,bits in clock_rx.items() if name.startswith('pll_') and len(bits)==1}
native_phy={name:dict(module=top['cells'][name]['type'],
                     clock_root=roots[top['cells'][name]['connections']['clk'][0]])
            for name in ('io_serdes','io_serdes_1','io_serdes_2')}
face_clocks=top['cells']['io_collective']['connections']['face_ck']
face_roles=['cal_ck','cal_lck','tx_wck','tx_rck','rx_wck','rx_rck',
            'codec_phy_ck','codec_bank1','codec_bank2','codec_bank3','codec_bank4']
native_faces={str(i):{role:roots[face_clocks[i*11+j]] for j,role in enumerate(face_roles)} for i in (2,3,4)}
manifest=json.loads((a.source/'results/qc_die57_1031/bind/final_asbuilt.json').read_text())
top_text=(a.bound/'rtl/qwen_compute_bound_top.sv').read_text()
top_instances={}
for name in ['io_serdes','io_serdes_1','io_serdes_2','coll_n','coll_s','c_W5_bf_00','c_W5_bf_01']:
    m=re.search(r'^    (\w+)(?: #\([^\n]*\))? '+name+r' \(\n(.*?)\n    \);',top_text,re.M|re.S)
    assert m,name
    pins=dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[2]))
    top_instances[name]=dict(module=m[1],clock_inputs={k:v for k,v in pins.items() if k.startswith('clk')},
                             fdi_connections={k:v for k,v in pins.items() if 'serdes' in v})
boundaries=[]
forwarding=[]
for name in ['coll_n','coll_s','c_W5_bf_00','c_W5_bf_01']:
    module=top_instances[name]['module']
    text=(a.bound/'rtl'/f'{module}.sv').read_text()
    for line in text.splitlines():
        if 'serdes' not in line:continue
        if 'ot_dp_st' in line:
            m=re.search(r'ot_dp_st #\(\.W\((\d+)\)\) (\w+) \((.*)\);',line)
            if not m:continue
            rec=dict(partition=name,instance=m[2],payload_width=int(m[1]),
                     epoch_width=1,pins=dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[3])),source=line.strip())
            (boundaries if name in ('coll_n','coll_s') and m[2].startswith(('u_bin_','u_bout_')) else forwarding).append(rec)
    if name.startswith('coll_'):
        top_instances[name]['native_face_clocks']=dict(re.findall(
            r'\.(cal_ck|cal_lck|tx_wck|tx_rck|rx_wck|rx_rck|codec_phy_ck)\(([^()]*)\)',text))
lane_keys=['lane','src','dst','bus_out','bus_in','width','bound_stages','plan_cycles','macro_pin_reg_ends']
lanes=[{k:row.get(k) for k in lane_keys} for row in json.loads((a.bound/'bind_latency.json').read_text())['buses']
       if 'serdes' in row.get('lane','')]
assert len(boundaries)==15,(len(boundaries),'boundary count changed')
assert len(lanes)==15,(len(lanes),'lane inventory changed')
assert all(row['pins']['clk']=='clk' for row in boundaries)
assert {v['clock_root'] for v in native_phy.values()}=={'pll_serdes0','pll_serdes1','pll_serdes2'}
sources={}
for rel in ['tools/die_plan/clock_landings.py','tools/die_plan/bind.py',
            'tools/die_plan/clock_landing_verify.py','rtl/physical/ot_qfd_coll_static_face.sv']:
    content=(a.source/rel).read_text()
    lines=content.splitlines()
    if rel.endswith('clock_landings.py'):
        selected=[(i+1,l) for i,l in enumerate(lines) if 'body, count = re.subn' in l or 'Functional binding uses the region source' in l]
    elif rel.endswith('bind.py'):
        selected=[(i+1,l) for i,l in enumerate(lines) if 'def default_domain' in l or 'clk_{sv_id(dd)}' in l or 'self.clk_dom[p].add' in l
                  or 'ot_dp_st #' in l and any(n in l for n in ('u_bin_','u_bout_','u_ft_'))]
        start=next(i for i,l in enumerate(lines) if 'def default_domain' in l)
        selected.extend((i+1,lines[i]) for i in range(start+1,start+8))
    elif rel.endswith('clock_landing_verify.py'):
        selected=[(i+1,l) for i,l in enumerate(lines) if 'def clock(' in l or "('top','clk_region_'" in l]
    else:
        selected=[(i+1,l) for i,l in enumerate(lines) if 'qfd_static_ch546 u_' in l or '.wck(' in l]
    sources[rel]=dict(sha256=hashlib.sha256(content.encode()).hexdigest(),lines=selected)
result=dict(schema='opentallas.qc_serdes_clock_trace.v1',scope='READ_ONLY_CONTRACT_DIAGNOSIS',
            native_phy=native_phy,native_face_clock_roles=native_faces,
            source_clock_alias_rules=[r for r in manifest['sources'] if r.get('module')=='qfd_clkrx'],
            actual_bound_instances=top_instances,boundary_stations=boundaries,
            third_path_forwarding_stations=forwarding,lanes=lanes,source_excerpts=sources,
            candidate=dict(enabled=False,emit_allowed=False,target_existing_domain='clk_serdes',
                proposed_hard_pin_bindings={n:dict(clk='clk_serdes') for n in native_phy},
                missing_contract=['per-bus FDI domain for all 15 bin/bout groups',
                  'FDI-domain FT/CA/FCLK/START/reset membership through c_W5_bf_00 and c_W5_bf_01',
                  'per-domain latency/calendar rederivation for direct2 and TX26/RX28 third paths',
                  'qualified real SerDes clock service and PHY hard views'],
                reason='A three-PHY clock-only rewrite introduces unrelated-domain sampling outside native CDC; no source rewrite is permitted by this packet'),
            physical_qualification_eligible=False,global_model_swap=False)
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(result,indent=2)+'\n')
print('SERDES_CLOCK_CONTRACT_HOLD',len(boundaries),'boundary groups',len(forwarding),'third-path FT stations',len(lanes),'lanes')
