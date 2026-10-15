#!/usr/bin/env python3
"""Assert mapped direct flop-Q output pins after flattening actual HBM RTL."""
import argparse,json,pathlib
p=argparse.ArgumentParser();p.add_argument('netlist',type=pathlib.Path);p.add_argument('out',type=pathlib.Path);a=p.parse_args()
v=json.loads(a.netlist.read_text());m=v['modules']['ot_hgi_coll_static_link_seq'];qbits=set();ffbits=0;clock_bits=m['ports']['ck']['bits'];per_clock=[0]*5
for c in m['cells'].values():
    t=c['type'].lower()
    if 'dff' in t:
        q=c['connections']['Q'];qbits.update(q);ffbits+=len(q)
        clock=c['connections'].get('C',c['connections'].get('CLK'))
        if not clock or len(clock)!=1 or clock[0] not in clock_bits:raise SystemExit(f'unknown flop root {c}')
        per_clock[clock_bits.index(clock[0])]+=len(q)
ports={}
for name,port in m['ports'].items():
    if port['direction']!='output':continue
    pins=port['bits'];bad=[b for b in pins if isinstance(b,int) and b not in qbits]
    if bad:raise SystemExit(f'NON_REGISTERED_OUTPUT {name}: {bad[:12]}')
    constants=[b for b in pins if isinstance(b,str)]
    if any(b not in ('0','1') for b in constants):raise SystemExit(f'UNDEFINED_OUTPUT {name}')
    ports[name]={'bits':len(pins),'direct_FF_Q_bits':len(pins)-len(constants),'constant_tie_bits':len(constants)}
macros=sum(c['type']=='ot_sram_1r1w_64x512_m1_r2c2' for c in m['cells'].values())
if macros!=4:raise SystemExit(f'wrong actual macro count {macros}')
control_bits=per_clock[0]
if control_bits>=15000:raise SystemExit(f'control root over budget: {control_bits}')
result={'status':'PASS: techmapped actual flattened RTL output pins are direct flop Q or constant tie, no post-FF fault/data mux',
        'top':'ot_hgi_coll_static_link_seq','native_macro_instances':macros,'all_output_ports':ports,
        'total_register_bits':ffbits,'register_bits_per_actual_clock_root':per_clock,'control_root_register_bits':control_bits,
        'limitations':'generic Yosys mapped netlist, not standard-cell placement/TTsetup/FFhold or PHY/retry qualification'}
a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
