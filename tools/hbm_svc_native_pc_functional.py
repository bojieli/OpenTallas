#!/usr/bin/env python3
"""Run canonical native command/data tests using the actual physical PC leaf.

This is a functional composition gate, not a performance waiver. The unchanged
77/122-cycle baselines and actual 640-sector failure remain in every output.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BASE=Path('rtl/hbm_accel/loader/service_native')
PHYS=Path('physical/hbm_accel_die_views/svc/native_pc_340cfd747/rtl/native_pc.sv')
CENSUS=Path('results/arch/hbm_die_v15/native_pc_clock_census')
STACK=BASE/'ot_hbm_svc_native_sector_prefetch_stack.sv'
LEAF=BASE/'ot_hbm_svc_native_stream_pc_lease.sv'
MEM=Path('physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v')
TOP='ot_hbm_svc_native_sector_prefetch_stack'
TB='tb_hbm_svc_prefetch_fast_original'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(c,m):
    if not c:raise ValueError(m)


def compose(out,mutant):
    m=json.loads((ROOT/CENSUS/'method.json').read_text());original=(ROOT/STACK).read_text()
    for p,want in m['source_sha256'].items():need(sha(ROOT/p)==want,'profile source drift: '+p)
    need(sha(ROOT/PHYS)==m['extracted_source_sha256'],'physical extraction body differs')
    start='    for(genvar p=0;p<32;p=p+1)begin:g_pc\n'
    need(original.count(start)==1,'unknown source framing')
    head=original.split(start,1)[0]
    head=head.replace('output reg[31:0]k_wr_done','output wire[31:0]k_wr_done')
    # Source boundary change only: each original exact g_pc body now instantiates
    # the byte-identical physical extraction, with identical p and PHASE.
    head+='    initial if(FAST_IDLE_DESC!=1||AQ_ROW_LEASE!=1||COLUMN_CLOSE_GUARD!=1)$error("wrong native PC composition profile");\n'
    ports=m['actual_top_port_table'];joins=[]
    for name,v in ports.items():
        width=v['bits']
        if name=='clk':expr='pc_clk[p]'
        elif name=='rst_n':expr='rst_n'
        elif name=='fault':expr='owner_fault[p]'
        else:expr=f'{name}[p]' if width==1 else f'{name}[p*{width}+:{width}]'
        joins.append(f'.{name}({expr})')
    head+='    for(genvar p=0;p<32;p=p+1)begin:g_pc\nassign pc_fault[p]=1\'b0;\n'
    head+='ot_hbm_svc_native_pc_census #(.PC(p),.PHASE(PHASE)) u_physical('+','.join(joins)+');\nend\nendmodule\n'
    stack=out/'composition_stack.sv';stack.write_text(head)
    body=(ROOT/PHYS).read_text()
    if mutant:
        token='.r_addr_in({2\'b0,response_read_address})';need(body.count(token)==1,'mutant token changed')
        body=body.replace(token,'.r_addr_in({2\'b0,response_read_address ^ 5\'d1})')
    physical=out/'physical_leaf.sv';physical.write_text(body)
    sources=[Path('rtl/lib/ot_reset_sync.sv'),Path('rtl/lib/ot_async_fifo.sv'),BASE/'ot_hbm_svc_async_fifo.sv',BASE/'ot_hbm_svc_prefetch_burst_bank.sv',MEM,LEAF,BASE/'tb_hbm_svc_command_dram_pipeline_fixture.sv',BASE/'ot_hbm_svc_prefetch_burst_owner.sv',BASE/'ot_hbm_svc_prefetch_burst_cdc.sv',BASE/(TB+'.sv')]
    evidence=json.loads((ROOT/BASE/'prefetch_fast_original_evidence.json').read_text())
    for p,want in evidence['source_sha256'].items():
        need(sha(ROOT/p)==want,'canonical functional profile drift: '+p)
    witness=dict(schema='opentallas.native_PC_physical_composition_witness.v1',profile='340cfd747',physical_source_sha256=sha(ROOT/PHYS),production_generate_body_sha256=m['original_generate_body_sha256'],composition_source_sha256=sha(stack),PC_instances=32,all_parameters=dict(FAST_IDLE_DESC=1,AQ_ROW_LEASE=1,COLUMN_CLOSE_GUARD=1,PHASE=0,PC='0..31'),source_sha256={str(p):sha(ROOT/p) for p in sources},mutant=mutant,mutant_scope='physical response SRAM registered read address XOR1' if mutant else None,functional_evidence_scope='exact original command fixture and golden payload; no model timing changes or performance gate waiver',parent_performance_status=evidence['status'])
    (out/'witness.json').write_text(json.dumps(witness,indent=2,sort_keys=True)+'\n')
    return [str(ROOT/p) for p in sources]+[str(stack),str(physical)]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['exact','mutant']);p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    sources=compose(out,a.mode=='mutant');exe=out/'composition.vvp'
    with (out/'build.log').open('w') as log:r=subprocess.run(['iverilog','-g2012','-s',TB,'-o',str(exe),*sources],stdout=log,stderr=subprocess.STDOUT)
    need(r.returncode==0,'composition compile failed; inspect build.log')
    if a.mode=='mutant':
        with (out/'mutant.log').open('w') as log:r=subprocess.run(['vvp',str(exe),'+PHASE=137','+CASE=1','+ALLOW_PERF_FAIL'],stdout=log,stderr=subprocess.STDOUT)
        text=(out/'mutant.log').read_text();print(text,end='')
        need(r.returncode!=0 and 'SRAM exact payload' in text,'physical SRAM mutant did not fail exact payload')
        print('NATIVE_PC_PHYSICAL_MUTANT expected failure: actual SRAM read address broke exact composition')
        return r.returncode
    perf_fail=[]
    for phase in (137,773):
        for case in (1,2):
            dest=out/f'phase_{phase}_case_{case}.log'
            with dest.open('w') as log:r=subprocess.run(['vvp',str(exe),f'+PHASE={phase}',f'+CASE={case}','+ALLOW_PERF_FAIL'],stdout=log,stderr=subprocess.STDOUT)
            text=dest.read_text();need(r.returncode==0 and 'PASS PREFETCH_FAST_ORIGINAL native_command_only_DRAM' in text,'physical composition functional failure')
            need(f'exact_vectors={640 if case==1 else 2048}' in text,'missing full production vectors')
            if 'PREFETCH_BURST_CDC_PERFORMANCE FAIL' in text:perf_fail.append(dict(phase=phase,total=640 if case==1 else 2048))
            print(text,end='')
    print('NATIVE_PC_PHYSICAL_FUNCTIONAL PASS all4 strict command/data cases; performance status remains separate '+json.dumps(perf_fail))
    return 0

if __name__=='__main__':sys.exit(main())
