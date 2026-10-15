#!/usr/bin/env python3
"""Emit the unadopted six-root bank ABI and exact bank/LG slot requests.

Frozen candidate pin windows are preserved for every surviving non-LG client.
Requested geometry is not actual ODB evidence or permission to alias a view.
"""
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import hbm_die_views as V
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'rtl/hbm_accel/generic/vm/static'
OUT=ROOT/'results/arch/hbm_vm_stageclocks_1103'
CLOCKS=['clk_pin','clk_s1','clk_mem','clk_capture','clk_return','clk_status']
CORE='rtl/hbm_accel/generic/vm/static/ot_vms_bank_static_wdecode_ft_stageclocks.sv'
MACRO='physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2'
FROZEN='c1e17f31d'
def old(path):return subprocess.check_output(['git','-C',str(ROOT),'show',FROZEN+':'+path])
def shape(q,rg,wg):
    top='hfd_vms_bank_stage6_'+q
    parsed=V.L.parse_module(CORE,'ot_vms_bank_static_wdecode_ft_stageclocks',dict(RG=rg,WG=wg))['ports']
    ports={}; wiring={}; assigns=[]; wires=[]
    for n,(d,b) in parsed.items():
        if n in ('rq','rr','wq','wq_done'):
            count=rg if n in ('rq','rr') else wg
            width={'rq':17,'rr':257,'wq':281,'wq_done':1}[n]
            for g in range(count):ports[n+str(g)]=(d,width)
            if d=='input':wiring[n]='{'+','.join(n+str(g) for g in reversed(range(count)))+'}'
            else:
                wires.append(f'    wire [{b-1}:0] {n};');wiring[n]=n
                for g in range(count):assigns.append(f'    assign {n}{g}={n}[{g*width}+:{width}];')
        else:ports[n]=(d,b);wiring[n]=n
    decl=['    '+d+' wire '+(f'[{b-1}:0] ' if b>1 else '')+n for n,(d,b) in ports.items()]
    text=['`timescale 1ns/1ps','`default_nettype none',f'module {top} (',',\n'.join(decl),');',*wires,*assigns,
          f'    ot_vms_bank_static_wdecode_ft_stageclocks #(.RG({rg}),.WG({wg})) bank (',
          ',\n'.join(f'        .{n}({a})' for n,a in wiring.items()),'    );','endmodule','`default_nettype wire']
    path='rtl/hbm_accel/generic/vm/static/physical/'+top+'.sv'
    (ROOT/path).parent.mkdir(parents=True,exist_ok=True);(ROOT/path).write_text('\n'.join(text)+'\n')
    baseline='6wg3' if q in ('NW','NE') else ('5wg1' if q=='SW' else '4wg1')
    s=json.loads(old(f'physical/ref_tile/vms_bank_ft_rg{baseline}_1015/spec.json'))
    # For NE remove old ATT read3/write1 and rename surviving HC/COLL ports, preserving semantic windows.
    rename={}
    if q=='NE':rename={'rq3':None,'rr3':None,'wq1':None,'wq_done1':None,'rq4':'rq3','rr4':'rr3','rq5':'rq4','rr5':'rr4','wq2':'wq1','wq_done2':'wq_done1'}
    faces={};ranges={}
    for face,ns in s['pins'].items():
        faces[face]=[]
        for n in ns:
            if n=='clk':continue
            nn=rename.get(n,n)
            if nn is not None:faces[face].append(nn);ranges[nn]=s['pin_ranges'][n]
    lg=['rq0','rr0','wq0','wq_done0']
    for face in faces:faces[face]=[n for n in faces[face] if n not in lg]
    start=max(ranges[n][1] for n in faces['W'])+20.0
    for n in lg:
        width=ports[n][1];ranges[n]=[round(start,3),round(start+width*.288,3)];start+=width*.288
    faces['W']+=lg
    # Six real independent physical roots occupy freed former group0 N windows.
    for i,n in enumerate(CLOCKS):faces['N'].append(n);ranges[n]=[5.4+i*.288,5.4+(i+1)*.288]
    h=math.ceil((start+20)/2.16)*2.16
    s.update(name='hvm_stage6_'+q.lower(),top=top,sources=[path,CORE,MACRO+'/'+MACRO.split('/')[-1]+'_bb.v'],
             clock='multiple_cts_roots',clock_port=CLOCKS[0],clock_ports=CLOCKS,clock_data_paths='related_same_frequency',
             clock_relationship=dict(kind='same_pll_fixed_phase',ratio=[1,1],phase_ps=0),pins=faces,pin_ranges=ranges,
             outline=dict(w=s['outline']['w'],h=round(h,3),exact=True))
    domains={('core' if i==0 else n.removeprefix('clk_')):dict(ratio=[1,1],ports=[n],inputs=[],outputs=[]) for i,n in enumerate(CLOCKS)}
    domains['core']['inputs']=[n for n,(d,b) in ports.items() if d=='input' and n not in CLOCKS]
    for n,(d,b) in ports.items():
        if d!='output':continue
        owner='s1' if n=='eg' else 'status' if n=='status' else 'capture' if n.endswith('done') or n.startswith('wq_done') else 'return'
        domains[owner]['outputs'].append(n)
    s['clock_entry_domains']=domains
    s.pop('pre_cts_extra',None)
    s['route'].update(signoff_period_ps=833.333,period_ps=833.333)
    s['job'].update(owner='Codex H-VM physical',branch='codex/hbm-vm-physical-1103',tag='stage6',record_to='results/rtl/ref_tile/'+s['name'],views_to='physical/ref_tile/'+s['name']+'/views',purpose='Six same-phase real bank roots; group0 W faces exact closed LG nearE. Unadopted source/slot successor; actual clocks, source SRAM, TT/FF/DRC and every incident pin required.',benches=[])
    s['job']['structural_change']=s['job']['purpose'];s['job']['reroute_reason']='rtl_change and slot_change; unclosed bank candidate'
    specs=ROOT/'tools/ref_tile/specs_hbm_vm_stage6_1103';specs.mkdir(parents=True,exist_ok=True)
    (specs/(s['name']+'.json')).write_text(json.dumps(s,indent=2)+'\n')
    return s,ports,lg

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    lefpath='physical/ref_tile/vm_lg_bank_hc_static_1015/views/ot_hbm_vm_lg_static_bank/ot_hbm_vm_lg_static_bank.lef'
    lef=subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+lefpath])
    lgidentity=dict(path=lefpath,sha256=hashlib.sha256(lef).hexdigest(),master='ot_hbm_vm_lg_static_bank',outline_um=[150.336,151.2],orient='R0',near='E',far='W',local='S',scope='Actual closed HC18/15 prototype. Source/params exact SU10/7 and SFU14/11 views must bind separately; no 96composition claim.')
    fp=json.loads(subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:results/arch/hbm_globalfp_1015/noatt/pins/T_band2__npg4_s5.pins.json']))
    req=[];placements=[]
    for q,rg,wg in [('SW',5,1),('SE',4,1),('NW',6,3),('NE',5,2)]:
        s,p,lg=shape(q,rg,wg)
        low=min(s['pin_ranges'][n][0] for n in lg); high=max(s['pin_ranges'][n][1] for n in lg)
        rel_y=(low+high)/2-151.2/2
        for b in range(8):
            name=f'vmb_{q}{b}';oldbox=fp['blocks'][name];x=oldbox['x'];y=oldbox['y'];bank_x=x+3*(150.336+20)
            placement=dict(instance=name,adopted_old_box={k:oldbox[k] for k in ('x','y','w','h')},proposed_bank=dict(x=bank_x,y=y,**s['outline']),local_channel_um=20,LG=[])
            for stage in range(3):placement['LG'].append(dict(instance=f'lg_{q}_{stage}.g_bank[{b}].leaf',x=bank_x-(stage+1)*(150.336+20),y=y+rel_y,w=150.336,h=151.2,orient='R0',READ_RETURN=10+4*stage,WRITE_RETURN=7+4*stage,near_peer='bank' if stage==0 else f'lg_{q}_{stage-1}.g_bank[{b}].leaf',same_edge_phase=True))
            placements.append(placement)
        req.append(dict(quadrant=q,replicas=8,master=s['top'],source=s['sources'][0],core=CORE,params=dict(RG=rg,WG=wg),kind='tile',outline=s['outline'],clock_ports=CLOCKS,pins=s['pins'],pin_windows_um=s['pin_ranges'],pin_widths={n:b for n,(d,b) in p.items()},LG0_W_window_um=[low,high],nonLG='Exact surviving baseline semantic pin windows retained; NE HC/COLL renames tracked, ATT only removed.',state='REQUESTED, NOT actual ODB/pin/PG/CTS evidence',home='Root must legalize complete functional groups against all other adopted blocks; origin expansion is not accepted geometry.'))
    # Full-box conflicts at proposed unshifted origins are evidence, not hidden by a new local origin.
    conflicts=[]
    for p in placements:
        z=p['proposed_bank'];a=(p['adopted_old_box']['x'],z['y'],z['x']+z['w'],z['y']+z['h'])
        for n,v in fp['blocks'].items():
            if n==p['instance']:continue
            b=(v['x'],v['y'],v['x']+v['w'],v['y']+v['h'])
            dx=min(a[2],b[2])-max(a[0],b[0]);dy=min(a[3],b[3])-max(a[1],b[1])
            if dx>0 and dy>0:conflicts.append(dict(candidate=p['instance'],peer=n,overlap_um2=round(dx*dy,3)))
    r=dict(schema='opentallas.hbm.stage6-native-bank-slot-request.v1',candidate='UNADOPTED. Exact typed grants required before gate/job; closed LG source/view stands.',LG_LEF=lgidentity,bank_requests=req,global_adjacent_proposals=placements,unshifted_expansion_conflicts=conflicts,requirements=['all six per-stage clocks exposed independently at production parent; never tied in the wrapper','actual per-root insertion<=300ps/spread<=80ps and ordinary related-root setup/hold','real ODB signal/PG pin access and <=500um registered hops; real routing cut<=0.60','hub>=1100um or physically qualified eight-lane delivery split remains a separate source/slot obligation'])
    (OUT/'slot_request.json').write_text(json.dumps(r,indent=2)+'\n')
    print('GENERATED four sixclock bank wrappers/specs and96actualLG-neighbor proposed homes; unshifted expansion conflicts',len(conflicts))
if __name__=='__main__':main()
