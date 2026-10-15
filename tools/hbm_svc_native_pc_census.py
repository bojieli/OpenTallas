#!/usr/bin/env python3
"""Exact bounded single-PC extraction and sequential mapped clock-pin census.

Only the original g_pc generate body is extracted. Port slices are reduced to
one PC; constant p retains PC parity and exact refresh phase. No behavioral
logic is rewritten. Every resulting output stays observable at the top.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
STACK='rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_sector_prefetch_stack.sv'
LEAF='rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_stream_pc_lease.sv'
MACRO='physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v'
EXPECTED={STACK:'fc9556d64d5da9b2da90acb838a880f162f8e8aaae2ffd286f913afc14cf316f',LEAF:'c16adc653eff8bce34ace00d6b4753b6937e758604b8d809183e14e85ea8be4c'}
NAME='ot_hbm_svc_native_pc_census'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(c,m):
    if not c:raise ValueError(m)


def prepare(out):
    sys.path.insert(0,str(ROOT/'tools'))
    import hbm_die_views as V
    for rel,want in EXPECTED.items():need(sha(ROOT/rel)==want,'profile340cfd747 source mismatch: '+rel)
    text=(ROOT/STACK).read_text()
    start='    for(genvar p=0;p<32;p=p+1)begin:g_pc\n'
    tail='    end\nendmodule\n'
    need(text.count(start)==1 and text.endswith(tail),'unrecognized g_pc source framing')
    body=text.split(start,1)[1][:-len(tail)]
    ports=V.L.parse_module(str(ROOT/STACK),'ot_hbm_svc_native_sector_prefetch_stack')['ports']
    need(set(ports)=={'clk','rst_n','pc_clk','k_v','k_rdy','k_we','k_addr','k_len','k_tag','k_wdata','k_wstrb','kr_v','kr_rdy','kr_tag','kr_beat','kr_data','k_wr_done','row_v','row_op','row_bank','row_row','col_v','col_we','col_bank','col_col','col_data','col_strb','dram_rvalid','dram_rdata','fault'},'unexpected stack ABI')
    declarations=[];reduced={}
    for name,(direction,width) in ports.items():
        if name=='pc_clk':continue
        local=width if name in ('clk','rst_n','fault') else width//32
        need(width==local*32 or name in ('clk','rst_n','fault'),'non-PC-scaled port '+name)
        # k_wr_done is assigned inside the original sequential process.
        kind='reg' if name=='k_wr_done' else 'wire'
        declarations.append(f'    {direction} {kind}'+(f' [{local-1}:0]' if local>1 else '')+' '+name)
        reduced[name]=dict(direction=direction,bits=local)
        if name not in ('clk','rst_n','fault'):
            if local==1:
                body=re.sub(r'\b'+re.escape(name)+r'\[p\]',name,body)
            else:
                body=re.sub(r'\b'+re.escape(name)+r'\[p\*'+str(local)+r'\+:'+str(local)+r'\]',name,body)
    body=body.replace('pc_clk[p]','clk').replace('pc_fault[p]','pc_fault').replace('owner_fault[p]','owner_fault')
    need(not re.search(r'\[p\*|\[p\]|pc_clk',body),'unreduced PC endpoint')
    source='`timescale 1ns/1ps\nmodule '+NAME+' #(parameter integer PC=0, PHASE=0)(\n'+',\n'.join(declarations)+'\n);\n'
    source+='    localparam integer p=PC, FAST_IDLE_DESC=1, AQ_ROW_LEASE=1, COLUMN_CLOSE_GUARD=1;\n'
    source+='    wire pc_fault,owner_fault;assign fault=pc_fault||owner_fault;\n'+body+'endmodule\n'
    out.mkdir(parents=True,exist_ok=True);(out/'single_pc.sv').write_text(source)
    sources={rel:sha(ROOT/rel) for rel in [STACK,LEAF,MACRO,'tools/hbm_svc_native_pc_census.py','tools/hbm_die_views.py','tools/die_top_lint.py']}
    method=dict(schema='opentallas.hbm_native_pc_census_method.v1',profile='340cfd747',source_sha256=sources,
        original_generate_body_sha256=hashlib.sha256(text.split(start,1)[1][:-len(tail)].encode()).hexdigest(),
        extracted_source_sha256=sha(out/'single_pc.sv'),actual_top_port_table=reduced,
        extraction='Only g_pc body; replace original bus[p*width+:width] / bus[p] by whole scalar/single-PC port; pc_clk[p] maps clk; p stays constant PC parameter; all outputs retained',
        settings=dict(FAST_IDLE_DESC=1,AQ_ROW_LEASE=1,COLUMN_CLOSE_GUARD=1,PHASE=0,REF_PHASE='(p*118/32)%118',PC_values=list(range(32))),
        mapping='Each PC separately: Yosys synth -flatten -noabc, primitive FF technology mapping, SRAM retained blackbox; not standard-cell area or timing qualification',
        admission=dict(memory_GB=2,threads=1,sequential_jobs=32,calibration_PC=0,full32_simultaneous_mapping=False),
        static_storage_sizing=dict(queue_bits=320*32,pending_identity_bits=21*32,response_identity_bits=21*32,response_head_identity_bits=21,payload_SRAM_macros=1,payload_SRAM_shape=[128,256],top_CA_fault_FF_separate=1),
        proof_limits=['Mapped sequential primitive clock-pin count, not selected standard-cell area','No routed timing, placement or CDC qualification','Every PC parity and refresh phase is mapped separately; no multiplied single-PC estimate'])
    (out/'method.json').write_text(json.dumps(method,indent=2,sort_keys=True)+'\n')
    return method


def inspect(data,pc):
    mod=data['modules'][NAME];ports=mod['ports'];clock=ports['clk']['bits'][0]
    clocks={};seq={};macros=[];bad=[]
    for name,c in mod['cells'].items():
        typ=c['type']
        if 'LATCH' in typ.upper() or typ in ('$dlatch','$adlatch'):bad.append(name+':'+typ)
        if typ.startswith('$_DFF') or typ.startswith('$_SDFF'):
            need('C' in c['connections'] and len(c['connections']['C'])==1,'unknown FF clock ABI '+typ)
            bit=c['connections']['C'][0];root='pc_clk['+str(pc)+']' if bit==clock else 'UNKNOWN:'+str(bit)
            clocks[root]=clocks.get(root,0)+1;seq[typ]=seq.get(typ,0)+1
        elif typ=='ot_sram_1r1w_128x256_m1_r2c2':
            need(c['connections']['clk']==[clock],'SRAM clock is not selected PC root')
            macros.append(dict(instance=name,type=typ,clock_root=f'pc_clk[{pc}]',clock_pins=1,
                port_widths={p:len(bits) for p,bits in c['connections'].items()}))
        elif typ.startswith('$') and any(x in typ.lower() for x in ['dff','mem','ff','latch']):bad.append(name+':'+typ)
    need(not bad,'unmapped storage or latches '+str(bad[:8]))
    need(set(clocks)=={f'pc_clk[{pc}]'},'unknown/missing root '+str(clocks))
    need(len(macros)==1,'expected actual one SRAM macro')
    return dict(pc=pc,refresh_phase=(pc*118//32)%118,clock_root=f'pc_clk[{pc}]',mapped_FF_clock_pins=sum(clocks.values()),
                primitive_sequential_cells=seq,SRAM_clock_pins=1,total_clock_pins=sum(clocks.values())+1,
                SRAM_macros=macros,latches=0,unmapped_storage=0,outputs_observed=len(ports))


def run(out,pcs):
    method=json.loads((out/'method.json').read_text());need(sha(out/'single_pc.sv')==method['extracted_source_sha256'],'extracted source changed')
    for rel,want in method['source_sha256'].items():need(sha(ROOT/rel)==want,'source changed before census: '+rel)
    for pc in pcs:
        case=out/f'pc{pc:02}';case.mkdir(exist_ok=True)
        script=f'read_verilog -sv {ROOT/LEAF} {ROOT/MACRO} {out/"single_pc.sv"}\nchparam -set PC {pc} -set PHASE 0 {NAME}\nhierarchy -check -top {NAME}\nsynth -top {NAME} -flatten -noabc\ncheck\nwrite_json {case/"mapped.json"}\nstat\n'
        (case/'map.ys').write_text(script)
        t=time.monotonic()
        with (case/'map.log').open('w') as f:
            result=subprocess.run(['/usr/bin/time','-v','yosys','-Q','-T','-s',str(case/'map.ys')],stdout=f,stderr=subprocess.STDOUT)
        need(result.returncode==0,f'PC{pc} mapping failed exit {result.returncode}')
        receipt=inspect(json.loads((case/'mapped.json').read_text()),pc)
        receipt.update(wall_seconds=time.monotonic()-t,source_manifest_sha256=sha(out/'method.json'),mapped_json_sha256=sha(case/'mapped.json'),log_sha256=sha(case/'map.log'))
        (case/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        print(json.dumps(receipt),flush=True)
    receipts=[]
    for pc in range(32):
        path=out/f'pc{pc:02}'/'receipt.json'
        if path.is_file():
            r=json.loads(path.read_text());need(r['source_manifest_sha256']==sha(out/'method.json'),'mixed source census');receipts.append(r)
    summary=dict(schema='opentallas.hbm_native_pc_clock_census.v1',status='complete' if len(receipts)==32 else 'partial',
       physical_qualification=False,mapping='Yosys technology-mapped primitive DFF cells; no ABC needed for clock-pin census',
       method_sha256=sha(out/'method.json'),PC_count=len(receipts),PC_roots=receipts,
       separate_top_CA_clock_root=dict(root='clk',FF_clock_pins=1,source='ca_fault single scalar resettable reg updated only at clk'),
       total_PC_FF_clock_pins=sum(r['mapped_FF_clock_pins'] for r in receipts),total_PC_SRAM_clock_pins=len(receipts),
       all_PC_roots_under_15000=all(r['total_clock_pins']<15000 for r in receipts))
    (out/'receipt.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','run']);p.add_argument('--out',required=True);p.add_argument('--pcs',default='0:32');a=p.parse_args();out=Path(a.out).resolve()
    if a.mode=='prepare':print(json.dumps(prepare(out),indent=2))
    else:
        lo,hi=map(int,a.pcs.split(':'));need(0<=lo<hi<=32,'PC range');run(out,range(lo,hi))

if __name__=='__main__':main()
