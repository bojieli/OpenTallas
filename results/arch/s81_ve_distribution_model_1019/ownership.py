import gzip,json,hashlib,collections,math,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent;WT=P.parents[2]
f=json.loads((P/'fixed_point.json').read_text());a=json.loads((P/'price.json').read_text())
r=json.loads(gzip.decompress((P.parent/'s81_ve_current_model_1019/endpoint_roots.json.gz').read_bytes()))
inv={x['driver']['pin'].rsplit('/',1)[0]:x for x in r if (x['driver']['master'] or '').startswith('CKINV')}
for x in r:
    end={}
    for t in x['sinks']:
        for z in inv[t['pin'].rsplit('/',1)[0]]['sinks'] if t['pin'].rsplit('/',1)[0] in inv else [t]:end[z['pin']]=z
    x['sinks']=list(end.values())
r=[x for x in r if x['driver']['pin'].rsplit('/',1)[0] not in inv]
n={x['instance']:math.ceil(x['original_max_load']/32) for x in f['copies']}
fail=[]
for x in r:
    if x['driver']['pin']=='PORT/clk' or x['driver']['signal']=='CLOCK':continue
    load=sum(n.get(s['pin'].rsplit('/',1)[0],1) if s['role']!='output' else 1 for s in x['sinks'])
    cap=32*n.get(x['driver']['pin'].rsplit('/',1)[0],1)
    if load>cap:fail.append(dict(driver=x['driver']['pin'],load=load,capacity=cap))
assert fail
resets=[x for x in f['copies'] if 'reset_leaf' in x['instance'] or 'rst_n__ot_rl' in x['instance']]
outputs=json.loads((P.parent/'s81_ve_current_model_1019/native_corrected.json').read_text())['outputs_nonff']
ports=[x['sink']['pin'] for x in outputs]
assert len(ports)==130 and set(ports)=={'PORT/p_hh[31]','PORT/p_kk[31]'}|{f'PORT/o_y[{32*w+b}]' for w in range(8) for b in range(16)}
coeff=a['coefficient_by_corner'];pincost=dict(ff=130,added_area_um2=130*coeff['TT']['DFFHQNx1_ASAP7_75t_R']['area_um2'],clock_fF={c:130*coeff[c]['DFFHQNx1_ASAP7_75t_R']['clock_cap_fF'] for c in ('TT','FF')})
out=dict(reset_copies=resets,reset_added_ff=sum(x['added'] for x in resets),reset_contract='Each existing synchronizer stage copied at same age, same asynchronous clear source, same D function, all upstream loads in fixed point. Never append ot_rst_relay TREE_STAGES: that would change release age. Actual native/Yosys reset identity and assertion/release/occupied restart remain required.',output_constant_ports=ports,constant_semantics='o_y low16 explicitly zero in actual source. p_hh/p_kk sign roots actually TIELO in native graph; squares have sign a31 XOR a31=0; refused nonfinite/overflow emit zero, additions of nonnegative terms preserve nonnegative sign. Exact source/native proof and no-mask mutant remain required for these two.',constant_pin_register_variant=pincost,total_added_ff_with_pin_registers=1716+130,total_added_area_um2_with_pin_registers=a['added_area_um2_by_corner']['TT']+pincost['added_area_um2'],total_added_clock_fF_with_pin_registers={c:a['added_clock_cap_fF_by_corner'][c]+pincost['clock_fF'][c] for c in ('TT','FF')},lower_bound_no_upstream_mutant=dict(rejected=True,unsafe_roots=len(fail),examples=fail[:8]),source_sha256={})
for rel in ['rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv','rtl/hdc/ot_hdc_delay_rf.sv','rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv','rtl/hdc/ot_hdc_fastfp_lat_f12.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/lib/ot_rst_relay.sv','rtl/hdc/ot_hdc_fp32_f12.sv','rtl/hdc/v41x/ot_dsrom_su_norm.sv']:
    raw=subprocess.check_output(['git','-C',str(WT),'show','78ad1399f:'+rel]);out['source_sha256'][rel]=hashlib.sha256(raw).hexdigest()
(P/'ownership.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('reset_copies','source_sha256','output_constant_ports')},indent=2))
