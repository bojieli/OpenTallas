#!/usr/bin/env python3
"""Source-pinned VM regional-glue sizing and graph cuts; never a closure claim.

Usage: vm_distributed_plan.py NET RESERVATIONS OUT
The graph is an endpoint lower bound, not an obstacle-avoiding physical route.
All active stages exist together, so cuts sum their wires, not their duty factors.
"""
import argparse, hashlib, json, math, subprocess, sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'results/arch/qwen_tp8_1012'))
import cuts as C

REF='87256eef919f75f48fa9d713940d0eefab803dbd'
RTL='rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv'
SPEC='tools/ref_tile/specs_qsp/qfd_vm_grp_c.json'

def obj(path):
    return subprocess.check_output(['git','show',f'{REF}:{path}'])
def overlap(a,b):
    return a['x'] < b['x']+b['w'] and b['x'] < a['x']+a['w'] and a['y'] < b['y']+b['h'] and b['y'] < a['y']+a['h']
def model_exact():
    # Identity-labelled banks detect every permutation error, independently of FP arithmetic.
    bank=list(range(64)); checks=0; mutant=0
    for shift in range(64):
        coarse=bank
        for bit in (3,4,5):
            n=1<<bit
            coarse=[coarse[(i+n)%64] if shift&n else coarse[i] for i in range(64)]
        fine=coarse
        for bit in (0,1,2):
            n=1<<bit
            fine=[fine[(i+n)%64] if shift&n else fine[i] for i in range(64)]
        assert fine == [bank[(i+shift)%64] for i in range(64)]
        for off in range(16):
            words=[16*b+e for b in fine for e in range(16)]
            # BEAT=1008 leaves 16 elements for the final variable element offset.
            result=words[off:off+1008]
            golden=[((shift*16+off+i)%1024) for i in range(1008)]
            assert result == golden
            mutant += sum(a!=b for a,b in zip(result,words[(off+1)%16:(off+1)%16+1008]))
            checks += 1008
    assert mutant > 0
    return dict(verdict='PASS_MODEL_ONLY',element_comparisons=checks,shift_plus_one_mutant_mismatches=mutant,
                covers='64 bank rotations x16 element offsets, exact identity permutation; no RTL, SRAM, queue or cycle equivalence')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('net');ap.add_argument('reservations');ap.add_argument('out');a=ap.parse_args()
    d=json.loads(Path(a.net).read_text());r=json.loads(Path(a.reservations).read_text());groups=r['reservations'][:8]
    original=[i for i in d['insts'] if i['n']!='sp_vector_memory' and not i['m'].startswith(('qfd_rly','qkd_rly'))]
    bays=[]
    for g in groups:
        k=int(g['n'].split('_')[-1])
        if k==7:
            bay=dict(n=f'vm_region_{k}',m='UNSIZED_REGIONAL_GLUE',x=14467.68,y=g['y'],w=164.16,h=g['h'])
        else:
            h=216 if k<3 else 86.4 if k<5 else 103.68
            bay=dict(n=f'vm_region_{k}',m='UNSIZED_REGIONAL_GLUE',x=g['x'],y=g['y']+g['h']+20.736,w=g['w'],h=h)
        collisions=[i['n'] for i in original+groups+bays if overlap(bay,i)]
        if collisions: raise ValueError((bay,collisions))
        bays.append(bay)
    C.CAP_MODE='v3';C.CLUSTER=C.CLUSTER+('ot_qfd_vm_grp',)
    # Every raw group remains M7, despite v3's default-M5 classification of an unknown master.
    insts=original+groups
    blocks,cap5,clb=C.block_model(insts)
    stages=[];links=[]
    for bit in range(6):
        shift=1<<bit
        # Coarse shifts move whole groups; fine shifts move only the boundary rows.
        step=shift//8 if bit>=3 else 1
        width=4096 if bit>=3 else shift*512
        stage=dict(name=f'x_bank_shift_{shift}',boundary_bits_per_group=width,
                   select=f'rot[{bit}]',logical_latency_engine_edges=1,clock_roots=8,
                   data_register_bits=32768)
        lengths=[]
        for k in range(8):
            dst=(k-step)%8; p=bays[k]; q=bays[dst]
            A=[p['x']+p['w']/2,p['y']+p['h']/2]; B=[q['x']+q['w']/2,q['y']+q['h']/2]
            length=abs(A[0]-B[0])+abs(A[1]-B[1]); lengths.append(length)
            links.append(dict(name=f"{stage['name']}_g{k}_g{dst}",stage=stage['name'],src=k,dst=dst,
                              bits=width,source_xy=A,sink_xy=B,manhattan_um=length,
                              minimum_wire_stages=math.ceil(length/500)))
        stage['equalized_minimum_wire_stages']=max(math.ceil(x/500) for x in lengths)
        stage['note']='All bypasses and select/valid/me_en tags must match this count; physical detours can add stages.'
        stages.append(stage)
    # Topological cuts use linear endpoint interpolation, as the inherited cut model.
    # Real corridors/relays must be placed before this becomes a route demand claim.
    S=np.array([v['source_xy']+v['sink_xy']+[v['bits']] for v in links]);coarse=[];fine=[]
    for ax,axis,other in [('x',0,1),('y',1,0)]:
        for cp in np.arange(13288 if ax=='x' else 8800,18467 if ax=='x' else 17000,100):
            selected=(np.minimum(S[:,axis],S[:,axis+2])<cp)&(cp<np.maximum(S[:,axis],S[:,axis+2]))
            T=S[selected]
            cross=T[:,other]+(T[:,other+2]-T[:,other])*(cp-T[:,axis])/(T[:,axis+2]-T[:,axis])
            edges=np.array([8800.,17000.]) if ax=='x' else np.array([13288.,18467.])
            cap,cov=C.usable(ax,cp,edges,blocks,cap5,clb);bits=float(T[:,4].sum())
            coarse.append(dict(ax=ax,pos=float(cp),bits=int(bits),usable=float(cap[0]),util=bits/cap[0]))
            for low in np.arange(edges[0],edges[-1]-260,130):
                bounds=np.array([low,low+260]);cap,_=C.usable(ax,cp,bounds,blocks,cap5,clb)
                bits=float(T[(cross>=low)&(cross<low+260),4].sum())
                if bits: fine.append(dict(ax=ax,pos=float(cp),win=[float(low),float(low+260)],bits=int(bits),usable=float(cap[0]),util=bits/cap[0]))
    # Preferred alternative: the real, already closed M5 bank/SU views appear
    # directly in the die, with no opaque M7 bank-group parent view.
    child_fp=json.loads(obj('physical/ref_tile/qfd_vm_grp_c/floorplan.json'))
    children=[]
    for group in groups:
        gid=int(group['n'].split('_')[-1])
        for child in child_fp['blocks']:
            if child['kind'] != 'child': continue
            children.append(dict(n=f"vm_g{gid}_{child['master']}_{child['idx']}",m=child['master'],
                x=round(group['x']+child['x'],6),y=round(group['y']+child['y'],6),
                w=child['w'],h=child['h'],orient=child['orient'],view=child['view'],layer_cap='M5',region=gid))
    assert len(children)==112
    assert not any(overlap(v,u) for j,v in enumerate(children) for u in children[:j]+original)
    flat_blocks,flat_cap5,flat_clb=C.block_model(original+children)
    flat_coarse=[]
    for row in coarse:
        edge=np.array([8800.,17000.]) if row['ax']=='x' else np.array([13288.,18467.])
        capacity,_=C.usable(row['ax'],row['pos'],edge,flat_blocks,flat_cap5,flat_clb)
        flat_coarse.append(dict(row,usable=float(capacity[0]),util=row['bits']/capacity[0]))
    leaf_area=sum(v['w']*v['h'] for v in children)
    flattened=dict(status='PREFERRED_PHYSICAL_CANDIDATE_NOT_ADOPTED',children=children,
        child_count=dict(bank=64,su=48),child_area_mm2=leaf_area/1e6,
        eight_region_area_mm2=sum(g['w']*g['h'] for g in groups)/1e6,
        free_region_area_mm2=(sum(g['w']*g['h'] for g in groups)-leaf_area)/1e6,
        unchanged_real_views=True,hard_overlaps=0,layer_contract='Existing M5 bank/SU leaves. Die owns M6/M7 and M8/M9 over them; M4/M5 remain leaf-owned. New regional glue defaults M5.',
        coarse_rotation_worst=max(flat_coarse,key=lambda x:x['util']),
        region_clock='Local roots per stage/lane region, each <=15000 sinks. Match routed child insertion; no M7 group clock spine.',
        rtl_requirement='Implement leaf-preserving decomposition of group FIFO/tags plus distributed parent rotations. Keep bank and SU leaf RTL/view bytes identical.',
        next='Spread lane-level exchange endpoints through actual free region area, assign corridors and <=500um relay sites, then compose every interface with existing demand.')
    raw=obj(RTL); spec=json.loads(obj(SPEC));spec['name']='qfd_vm_grp_nso_candidate';spec['pins']['E'].remove('so');spec['pins']['N']=['so']
    spec['job']=dict(submit=False,reason='Source dependency absent from main; regional glue/corridor/fine-cut gates remain open. Preserve live r6c.')
    widths=dict(re=8,ra=64,we=8,wl=64,wm=128,wd=4096,sre=6,sra=60,swe=2,swl=20,swm=32,swd=1024,
                xo=4096,ro=512,ovf=1,xv=1,rq=1,rqb=3,sv=3,pop=1,me_in=1,so=3072,clk=1,rst_n=1)
    pinplan={};pitch=.16
    for face,ports in spec['pins'].items():
        count=sum(widths[p] for p in ports);at=(1149.12-count*pitch)/2;pinplan[face]=[]
        for p in ports:
            pinplan[face].append(dict(port=p,bits=widths[p],range=f'{p}[{widths[p]-1}:0]' if widths[p]>1 else p,
                                      first_um=round(at,6),last_um=round(at+(widths[p]-1)*pitch,6),pitch_um=pitch))
            at += widths[p]*pitch
    report=dict(status='ARCHITECTURE_CANDIDATE_NOT_ADOPTED',source=dict(ref=REF,rtl=RTL,sha256=hashlib.sha256(raw).hexdigest()),
                flattened_child_alternative=flattened,group_pin_plan=pinplan,pin_plan_status='Exact ordered relative coordinates; requires new M7 cluster layer grant and routed view. No live kit edited.',
                candidate_group_spec=spec,regional_bays=bays,regional_area_mm2=sum(v['w']*v['h'] for v in bays)/1e6,
                glue_capacity_reservation=r['reservations'][8],bay_validation=dict(hard_overlaps=0,group_overlaps=0,
                   note='Existing relay objects excluded because all affected relay chains must be regenerated.'),
                x_rotation_stages=stages,x_rotation_links=links,exactness=model_exact(),
                x_rotation_data_register_bits=6*32768,extra_vs_two_rotation_registers=4*32768,
                minimum_engine_edges=sum(s['equalized_minimum_wire_stages'] for s in stages),
                cuts=dict(capacity_model='M8/M9 .75, free M6/M7 .75 and M4/M5 .5; existing v3 caps; groups explicitly M7',
                          coverage='X bank rotation network only; excludes original die demand, descriptors/writes/SU/row/final fanout and route detours.',
                          coarse_worst=max(coarse,key=lambda x:x['util']),fine_worst=sorted(fine,key=lambda x:x['util'],reverse=True)[:12],
                          verdict='PRELIMINARY_ONLY: endpoint interpolation needs corridor allocation and existing-demand composition'),
                throughput=dict(required='One x beat per enabled engine edge; one row write/read and one SU operand request per hclk as existing contract.',
                    schedule_change=False,repricing=False,latency='Additional pipeline edges must be carried by XVM, VL, rowvalid and hazard/land tracking; no measured new RTL latency.'),
                adoption_gates=['Allocate lane-level obstacle-avoiding corridors and registered seams <=500um, including bypass paths and all tags',
                    'Compose full existing die demand and every new interface at 260um fine windows; target <=0.60',
                    'Synthesize real regional logic; <=15000 sinks per new clock root and measured fit in bays/reserve',
                    'Bring VMT source to isolated candidate from pinned predecessor object; preserve live r6c and old views',
                    'Matched RV for all reads/writes; matched RO per return; preserve old-word 1R1W order and late-write hazards',
                    'Production NB3 exact RTL bench with x/SU/row simultaneous traffic and finite credits; all mutants fail',
                    'New group N-face view TT/FF/DRC/childlint/insertion, then real die netlist/cuts/STA/GRT/IR'])
    Path(a.out).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','regional_area_mm2','exactness','minimum_engine_edges')}))
    print(json.dumps(report['cuts']['coarse_worst']));print(json.dumps(report['cuts']['fine_worst'][0]))
if __name__=='__main__': main()
