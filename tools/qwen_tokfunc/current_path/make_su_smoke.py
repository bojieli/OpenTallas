#!/usr/bin/env python3
"""Build a diagnostic programme-fetch/retirement bench on three literal bound SU partitions.

The bench drives only omitted-controller lane ends. Kept instances, internal lanes, reset and START depths
come from the bind. Numeric token qualification remains a separate step.
"""
import argparse, importlib.util, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import bind_smoke as B
spec=importlib.util.spec_from_file_location('bound_carve',ROOT/'tools/qwen_tokfunc/xdie_bound/bound_carve.py')
BC=importlib.util.module_from_spec(spec);spec.loader.exec_module(BC)

def make(bound,out,slice_name):
    top=bound/'rtl/qwen_compute_bound_top.sv';seeds=[slice_name+'_'+x for x in ('su_c','su_l0','su_l1')]
    _,_,allinsts=BC.parse_top(top);keep=[x for x in allinsts if x['name'] in seeds]
    if len(keep)!=3:raise ValueError('three native SU partitions required')
    for part in keep:
        if part['name'].endswith(('su_l0','su_l1')):
            text=(bound/'rtl'/(part['module']+'.sv')).read_text()
            params=re.findall(r'qfd_dv_lane_h_safe2\s*#\((.*?)\)\s+\w+\s*\(',text,re.S)
            if len(params)!=4 or any('.MEMORY_ALIGNMENT(3)' not in x or '.MEMORY_READ_EXTRA(0)' not in x for x in params):
                raise ValueError(f'{part["name"]}: require four evaluated alignment3/MIF0 heads; regenerate the source bind')
    meta=B.qc_reset_contract(top,keep);rep=BC.carve(top,seeds,'qc_su_native',out)
    if not meta.get('start'):raise ValueError('native START metadata required')
    reset_inputs=meta['boundary_prefixes'];start_inputs=meta['start']['boundary_prefixes']
    lines=['`timescale 1ns/1ps','module tb_qc_su_native;','reg ck=0;always #0.4165 ck=~ck;','reg rst_n=0,start=0,epoch=0;','integer cycle,programs=0,rows=0,writes=0,faults=0;','reg[551:0] ctl0=0,ctl1=0;reg[550:0]ctl2=0;reg[1023:0]program_word=0;','always @(posedge ck) epoch<=rst_n&&start;']
    connections=[];driven=set();status_net=None
    for name,item in rep['inputs'].items():
        width=item['width']; readers=item['readers']
        if name.startswith('clk_'):value='ck'
        elif name=='rst_n':value='rst_n'
        elif name=='start':value='start'
        elif name in reset_inputs or name in start_inputs:
            table,src=(reset_inputs,'rst_n') if name in reset_inputs else (start_inputs,'start')
            age=table[name]
            if age:
                lines.extend([f'reg[{age-1}:0]prefix_{name}=0;',f'always @(posedge ck)prefix_{name}<={{prefix_{name},{src}}};'])
                value=f'prefix_{name}[{age-1}]'
            else:value=src
        elif name.startswith(('rstw_','stw_')):raise ValueError(f'missing published prefix {name}')
        elif readers==[slice_name+'_su_c.x_ctl_i'] and width==553:value='{epoch,ctl0}';driven.add('ctl0')
        elif readers==[slice_name+'_su_c.x_ctl_p1_i'] and width==553:value='{epoch,ctl1}';driven.add('ctl1')
        elif readers==[slice_name+'_su_c.x_ctl_p2_i'] and width==552:value='{epoch,ctl2}';driven.add('ctl2')
        else:
            value=f"{width}'d0" # Omitted-controller inactive lane; named in the diagnostic scope below.
        connections.append(f'.{name}({value})')
    if driven!={'ctl0','ctl1','ctl2'}:raise ValueError(f'unknown controller payload ABI {driven}')
    for name,item in rep['outputs'].items():
        if item['drivers']==[slice_name+'_su_c.x_ctl_o']:
            if item['width']!=94:raise ValueError('unknown native SU status ABI')
            status_net=name;lines.append(f'wire[93:0]{name};');connections.append(f'.{name}({name})')
        else:connections.append(f'.{name}()')
    if status_net is None:raise ValueError('native SU status output absent')
    lines.append('qc_su_native u_d('+','.join(connections)+');')
    lines.extend(['initial begin','program_word[18:1]=1;program_word[36:19]=8;program_word[530:513]=2;program_word[548:531]=16;','for(cycle=0;cycle<2000;cycle=cycle+1)begin','@(negedge ck);rst_n=(cycle>15);start=(cycle>=200);ctl0=0;ctl1=0;ctl2=0;','if(cycle>=400&&cycle<416)begin ctl1[75:52]=cycle-400;ctl1[551:76]=program_word[475:0];ctl2[547:0]=program_word[1023:476];ctl2[550:548]=3\'b111;end','if(cycle>=480&&cycle%128==96)ctl0[9:0]={1\'b1,9\'(2*((cycle/128)%8))};','@(posedge ck);#0.001;',f'if(cycle>450)begin programs={status_net}[76:61];rows={status_net}[92:77];if({status_net}[58]===1\'b1)faults=faults+1;end','end','$display("QC_SU_NATIVE_DIAGNOSTIC programs=%0d rows=%0d fault_cycles=%0d",programs,rows,faults);','$finish;end endmodule'])
    (out/'tb_qc_su_native.sv').write_text('\n'.join(lines)+'\n')
    (out/'scope.json').write_text(json.dumps(dict(scope='Diagnostic native SU programme fetch/retirement only; no numeric or G5 claim. Other omitted-controller lanes inactive.',source_top_sha256=BC.sha256(top),seeds=seeds,expected_head_profile=dict(memory_alignment=3,memory_read_extra=0),reset=meta),indent=1)+'\n')
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--bound',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--slice',default='sl_W5');a=ap.parse_args();make(a.bound.resolve(),a.out.resolve(),a.slice)
