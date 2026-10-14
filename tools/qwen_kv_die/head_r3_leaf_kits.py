#!/usr/bin/env python3
"""Assign the r3 head's new leaf pins within the retained v1.1 subslot plan."""
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PLAN='results/arch/qwen_split_1014/head_native_r3_codex_1014/plan.json'
OUT='physical/qwen_head_r3_1014'
SPEC='tools/ref_tile/specs_qkh_r3_1014'

def bus(name,w):return [name] if w==1 else [f'{name}[{i}]' for i in range(w)]
def track(x):return round(0.012+0.048*round((x-0.012)/0.048),6)

def main():
    plan=json.loads((ROOT/PLAN).read_text());assert plan['valid'] and plan['clock_entries_per_head']==83
    common=json.loads((ROOT/'physical/ref_tile/qkh_native_stin_1014/spec.json').read_text())
    shapes={'front':(648.,32.4),'stin':(32.4,43.2),'stk':(32.4,21.6),'nb':(32.4,10.8)}
    tops={'front':'ot_qkh_head_front_native','stin':'ot_qkh_head_stin_native',
          'stk':'ot_qkh_head_stk_native','nb':'ot_qkh_head_nb_native'}
    negatives={'front':1,'stin':4,'stk':5,'nb':2}
    assignment={}
    (ROOT/OUT).mkdir(parents=True,exist_ok=True);(ROOT/SPEC).mkdir(parents=True,exist_ok=True)
    for kind,(w,h) in shapes.items():
        lines=[f'# Coordinator-assigned {kind} pins from {PLAN}; all coordinates are local um.']
        pins={};locations={};occupied=[]
        def pin(name,face,u):
            layer='M5' if face in 'NS' else 'M4'
            assert 0.096<=u<=(w if face in 'NS' else h)-0.096,(name,face,u)
            assert all(f!=face or abs(v-u)>=0.096-1e-6 for f,v in occupied),(name,face,u)
            occupied.append((face,u));pins.setdefault(face,[]).append(name)
            x,y={'S':(u,0.096),'N':(u,h-0.096),'W':(0.096,u),'E':(w-0.096,u)}[face]
            size='0.024 0.192' if face in 'NS' else '0.192 0.024'
            lines.append(f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{x:.6f} {y:.6f}}} -pin_size {{{size}}} -force_to_die_boundary')
            locations[name]={'face':face,'layer':layer,'place_pin_xy_um':[x,y]}
        def group(names,face,start):
            for i,n in enumerate(names):pin(n,face,track(start)+0.096*i)
        if kind=='front':
            ti=bus('c_in',4)+bus('row_in',1024)+bus('lt_in',12)+bus('q_valid_in',1)+bus('q_beat_in',6)+bus('q_data_in',512)
            assert len(ti)==1559
            for i,n in enumerate(ti):pin(n,'S',round(224.508-216+0.288*i,6))
            group(bus('e_in',16),'S',686.076-216)
            group(bus('hid',2),'S',474.012)
            for j,t in enumerate(plan['front_port_order_W_to_E']):
                group(bus(f'f_t{t}',233),'N',j*w/16+(w/16-0.096*232)/2)
            pin('pack_fault','N',plan['parent_data_pin_assignments']['front_pack_fault_N'][0]-216)
        elif kind=='stin':
            group(bus('cr_i',16)+bus('dr_i',217),'E',(h-0.096*232)/2)
            group(bus('cr_o',16)+bus('dr_o',217)+['lane_rst_n'],'S',(w-0.096*233)/2)
        elif kind=='stk':
            group(bus('kp_i',32)+['kpv_i','gf_i'],'N',(w-0.096*33)/2)
            group(bus('kp_o',32)+['kpv_o','gf_o'],'S',(w-0.096*33)/2)
        else:
            group(bus('nb_i',64),'W',(h-0.096*63)/2)
            group(bus('nb_o',64),'E',(h-0.096*63)/2)
        if kind=='nb':pin('clk','N',track(w/2))
        else:
            pin('clk','W',track(h/2));pin('rst_n','W',track(h/2)+0.096)
        io=f'{OUT}/{kind}_io.tcl';(ROOT/io).write_text('\n'.join(lines)+'\n')
        spec=json.loads(json.dumps(common));name=f'qkh_r3_{kind}_1014'
        spec.update(name=name,top=tops[kind],outline={'w':w,'h':h},io_tcl=io,
                    pins={f:list(dict.fromkeys(n.split('[')[0] for n in ns)) for f,ns in pins.items()},
                    params={'Q_FP32':1,'MUT':0} if kind=='front' else {'MUT':0},
                    reset_ports=[] if kind=='nb' else ['rst_n'])
        spec['sources'].insert(1,'rtl/qwen_sys/split_20261014/ot_qkh_head_native_r3.sv')
        spec['why_floorplan']='Coordinator-assigned child in retained v1.1 head slot; exported closed pins and region bounds in '+PLAN
        spec['slot_change_request']={'parent':'qkd_rhead','contract':'results/arch/qwen_split_1014/kvsys_v1_1/contract.json',
            'plan':PLAN,'assigned_pins':f'{OUT}/assignments.json','requested_outline_um':[w,h],
            'status':'child assignment inside retained slot; parent r3 has 83 separate clock entries and needs die binding'}
        spec['reroute_reason']={'kind':'slot_change' if kind in ['front','stin'] else 'rtl_change',
            'why':'retained v1.1 subslot and exact pin assignment; KP D2 / two NB D1 preserve all data stages'}
        spec['job'].update(owner='Codex:coordinator-kvsys-1014-pm',branch='codex/coordinator-takeover-1014-pm',tag='r3',
            purpose=f'Native head r3 {kind} leaf in the retained v1.1 head slot',
            structural_change='83 independently clocked children; no data-cycle or FP32 operation change',
            extra_paths=['rtl/hdc','rtl/proto','rtl/qwen_sys/split_20261014','rtl/test/qwen_split',
                         'tools/qwen_kv_die','physical/qwen_head_r3_1014',
                         'results/arch/qwen_split_1014/head_native_r3_codex_1014',
                         'results/arch/qwen_split_1014/kvsys_v1_1'])
        spec['job']['benches']=[dict(name='actual_head_exact',cmd='HEAD_R3=1 bash rtl/test/qwen_split/run_qkh_head_native.sh {RUN}/bench/pos 0',
            expect='pass',threads=8,peak_ram_gb=8,pass_regex='HEAD_NATIVE_PASS checks=3515',min_count_regex='HEAD_NATIVE_PASS checks=([0-9]+)'),
            dict(name=f'actual_{kind}_mutant',cmd=f'HEAD_R3=1 bash rtl/test/qwen_split/run_qkh_head_native.sh {{RUN}}/bench/m{negatives[kind]} {negatives[kind]}',
                 expect='fail',threads=8,peak_ram_gb=8,fail_regex='HEAD_NATIVE_FAIL checks=3515 errors=[1-9]')]
        (ROOT/SPEC/f'{name}.json').write_text(json.dumps(spec,indent=1)+'\n')
        assignment[kind]={'top':tops[kind],'outline_um':[w,h],'io_tcl':io,'pins':locations}
    instances={}
    for n,r in plan['children'].items():
        kind='nb' if n.startswith('nb') else ''.join(c for c in n if not c.isdigit())
        if kind not in assignment:continue
        xy=assignment[kind]['pins']['clk']['place_pin_xy_um']
        instances[n]={'kit':f'qkh_r3_{kind}_1014','slot':r,
            'assigned_clock_place_pin_xy_um':[round(r[0]+xy[0],6),round(r[1]+xy[1],6)]}
    assert len(instances)==65
    (ROOT/OUT/'assignments.json').write_text(json.dumps({'schema':'qkh-r3-child-pins/1','plan':PLAN,
        'rule':'each clock entry delivers phi minus its measured child insertion; exact exported clock coordinates verified after hardening',
        'parent_data_pins':'v1.1 unchanged, front ti/e bit matched and NB2 feeds each 64-bit E-face group',
        'leaves':assignment,'instances':instances},indent=1)+'\n')
    print('Assigned four leaf kits and 65 child clock pins; 18 closed-child pins stand.')

if __name__=='__main__':main()
