import json,re,math,sys
plan=json.load(open('hm_r12.json')); cen=json.load(open('r13_census.json'))['modules']
CORES='cores/'
types={}
for tn,t in plan['partition_types'].items():
    for hc in t.get('hard_cores',[]):
        types.setdefault(hc['module'],{'outline':hc['outline_um'],'pins':set(),'parts':set(),'n':0})
        d=types[hc['module']]; d['pins'].add(hc['pins_file'].split('/')[-1]); d['parts'].add(tn); d['n']+=1
scope=['qkd_ectlk_q0','qkd_ectlk_q1','qkd_ectlk_q2','qkd_ectlk_q3','qkd_ahub','qkd_kvs_ctl','kv3_astk','ot_qwen_tp8_pv_join_t','qkd_kvs_pc_h_head_p']+sorted(m for m in types if m.startswith('qkd_hr_'))
L=4.32
out={}
for m in scope:
    d=types[m]; W,H=d['outline']; pf=sorted(d['pins'])[0]
    P=json.load(open(CORES+pf))['pins']
    ck=[(p['name'],p['layer'],p['x'],p['y']) for p in P if re.match(r'^(ck|clk|ck_phy)(\[\w+\])?$',p['name'])]
    c=(round(W/2/L)*L, round(H/2/L)*L); c2c=math.hypot(W/2,H/2)
    isl=[[x,y,r] for x,y,r in cen.get(m,{}).get('top',[[[],0]])[0][0]]
    quad=[[round(W*a/L)*L, round(H*b/L)*L] for a in (0.25,0.75) for b in (0.25,0.75)] if c2c>200 else []
    ckd=[min(math.hypot(x-c[0],y-c[1]) for _,_,x,y in ck)] if ck else None
    out[m]=dict(outline=[W,H],instances=d['n'],partitions=sorted(d['parts']),pins_files=sorted(d['pins']),
      plan_clock_pins=ck, clock_pin_to_centre_um=ckd and round(ckd[0],2), centre_entry_12_8a=[round(c[0],3),round(c[1],3)],
      centre_to_corner_um=round(c2c,1), r13_pushdown_islands=isl, quadrant_islands_needed_12_8b=quad)
json.dump(out,open('out/kv_core_slice_gate.json','w'),indent=1)
for m,v in out.items(): print(m.ljust(24), v['outline'], v['instances'], v['plan_clock_pins'][:1], 'd_ck_ctr', v['clock_pin_to_centre_um'], 'c2c',v['centre_to_corner_um'], 'r13isl',len(v['r13_pushdown_islands']), 'quad',len(v['quadrant_islands_needed_12_8b']), v['partitions'][:2])
