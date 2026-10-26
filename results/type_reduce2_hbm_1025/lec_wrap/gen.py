import json,re,sys
import os; WT=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../..'))
can=json.load(open(WT+'/physical/die_plan/hbm/cores/harden/canonical_ports_split.json'))['types']
plan=json.load(open(WT+'/physical/die_plan/hbm_arch/B2n/die_plan.json'))
cases={}
for t in plan['partition_types'].values():
    for h in t.get('hard_cores',[]):
        if h.get('straps'): cases.setdefault(h['module'],{})[json.dumps(h['straps'],sort_keys=True)]=h['straps']
for wm,vals in cases.items():
    cn={'ot_hgi_sfu_split3_lane_core_strap':'sfu_lane','ot_hbm_su_pg_lane_exp_core_strap':'pg_lane_exp','ot_hbm_su_pg_lanes4_core_strap':'pg_lanes4'}[wm]
    c=can[cn]; top=c['top']; ports=c['ports']
    # blackbox master stub
    stub=f"(* blackbox *) module {top}(" + ', '.join(f"{d} wire {f'[{w-1+l}:{l}] ' if w>1 or l else ''}{n}" for n,d,w,l in ports) + "); endmodule\n"
    vs=list(vals.values())
    for k,st in enumerate([vs[0],vs[-1]]):
        cv={s['port'][len('strap_'):]: s['value'] for s in st}
        ext=[p for p in ports if p[0] not in cv]
        hdr=', '.join(f"{d} wire {f'[{w-1+l}:{l}] ' if w>1 or l else ''}{n}" for n,d,w,l in ext)
        gold=f"module gold({hdr});\n {top} u_core(" + ', '.join(f".{n}({cv[n] if n in cv else n})" for n,_d,_w,_l in ports) + ");\nendmodule\n"
        gate=f"module gate({hdr});\n {wm} u_w(" + ', '.join(f".{('strap_'+n) if n in cv else n}({cv[n] if n in cv else n})" for n,_d,_w,_l in ports) + ");\nendmodule\n"
        wfile=c['file'].rsplit('/',1)[0]+f'/{wm}.sv'
        name=f'{wm}_{k}'
        open(name+'.v','w').write(stub+gold+gate)
        open(name+'.ys','w').write(f"""read_verilog -sv {name}.v
read_verilog -sv {wfile}
hierarchy -check
flatten gate
flatten gold
equiv_make gold gate eq
hierarchy -top eq
equiv_simple
equiv_status -assert
""")
        print(name, cv)
