#!/usr/bin/env python3
"""Generate an actual static SU source successor with SW/MOE clock entries.

The immutable SW576 source remains the datapath definition. Only module names,
clock ports and their two existing connections change. Exact inverse patches
check that arithmetic, calendar, SRAM storage and data/control wiring stand.
The generated hierarchy is source hardware, not placement or programme proof.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import subprocess
from source_locality_assignment import read

SOURCE_COMMIT='05a25d699'
HIER='rtl/dsrom_sys/s81_suhc/hier/'
OLD='dsfd_sp_su_static'
NEW='dsfd_sp_su_static_split_clocks'
OLD_PROGRAM='dsfd_sp_su_static_programmed'
NEW_PROGRAM='dsfd_sp_su_static_programmed_split_clocks'
ROOT=Path(__file__).resolve().parents[2]

def git_source(path,commit=SOURCE_COMMIT):
    return subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT).decode()

def once(text,old,new):
    if text.count(old)!=1:raise ValueError('expected one exact source connection '+old)
    return text.replace(old,new,1)

PATCHES=[('module '+OLD+' #(', 'module '+NEW+' #('),
 ('    input wire sk, srs,','    input wire sk, srs,\n    input wire [151:0] sw_ck,\n    input wire [5:0] moe_ck,'),
 ('u_sw576(.ck({152{sk}})', 'u_sw576(.ck(sw_ck)'),
 ('u_moe(.ck({6{sk}})', 'u_moe(.ck(moe_ck)')]
PROGRAM_PATCHES=[('module '+OLD_PROGRAM+' #(', 'module '+NEW_PROGRAM+' #('),
 ('    input wire sk,srs,arm,','    input wire sk,srs,arm,\n    input wire [151:0] sw_ck,\n    input wire [5:0] moe_ck,'),
 ('    dsfd_sp_su_static u_su(.sk(sk),.srs(srs),.arm(arm),',
  '    dsfd_sp_su_static_split_clocks u_su(.sk(sk),.srs(srs),.arm(arm),.sw_ck(sw_ck),.moe_ck(moe_ck),')]

def transform(text,patches):
    for old,new in patches:text=once(text,old,new)
    return text

def verify_identity(old,new,patches):
    restored=new
    for a,b in reversed(patches):restored=once(restored,b,a)
    if restored!=old:raise ValueError('datapath/calendar/storage source changed outside clock interface')

WRAPPER='''`timescale 1ns/1ps
// Actual mapped calendar plus unchanged native arithmetic. Source-only successor:
// SW152+MOE6 entries are explicit; residual ck[0] still needs partition/CTS proof.
// No programme/core epoch, physical slot or native VM phase is implied.
module ot_s81_su_canonical_candidate #(
    parameter integer PROGRAM_DEPTH=4096,
    parameter integer AW=(PROGRAM_DEPTH>64)?$clog2(PROGRAM_DEPTH):6
)(
    input wire [158:0] ck,
    input wire rst_n,arm,boot_we,boot_commit,
    input wire [AW-1:0] boot_addr,
    input wire [3:0] boot_lane,
    input wire [63:0] boot_data,
    output wire [31:0] cycle,
    output wire done,
    output wire [7:0] done_tag,
    output wire [15:0] rq_v,
    output wire [223:0] rq_row,
    input wire [15:0] rs_v,
    input wire [8191:0] rs_d,
    output wire [15:0] wq_v,
    output wire [223:0] wq_row,
    output wire [255:0] wq_mask,
    output wire [8191:0] wq_d,
    output wire flt,online,
    output wire [3:0] fcode
);
    dsfd_sp_su_static_programmed_split_clocks #(.PROGRAM_DEPTH(PROGRAM_DEPTH),.AW(AW)) u_native(
        .sk(ck[0]),.sw_ck(ck[152:1]),.moe_ck(ck[158:153]),.srs(rst_n),.arm(arm),
        .boot_we(boot_we),.boot_commit(boot_commit),.boot_addr(boot_addr),.boot_lane(boot_lane),.boot_data(boot_data),
        .cycle(cycle),.done(done),.done_tag(done_tag),.rq_v(rq_v),.rq_row(rq_row),.rs_v(rs_v),.rs_d(rs_d),
        .wq_v(wq_v),.wq_row(wq_row),.wq_mask(wq_mask),.wq_d(wq_d),.flt(flt),.online(online),.fcode(fcode));
endmodule
'''

def requirements(demand,candidate):
    nodes={n['id']:n for n in demand['nodes'] if n.get('kind')=='instruction'}
    assignments={r['node']:r for r in candidate['source_operation_homes'] if r['rank']==0 and r['unit']==2}
    if set(assignments)!={n for n,x in nodes.items() if x['instruction']['unit']==2}:raise ValueError('literal SU source coverage')
    for node,a in assignments.items():
        if a['template_sha256']!=nodes[node]['template_word_sha256']:raise ValueError('stale literal source template')
        if type(a['stage'])!=int or not 0<=a['stage']<81:raise ValueError('unbound/invalid candidate stage')
        if a.get('physical_instance') is not None:raise ValueError('source candidate cannot establish an actual physical instance')
    groups=candidate['source_private_SU_colocation_groups']
    grouped={n for g in groups for n in g};groups=groups+[[n] for n in assignments if n not in grouped]
    rows=[]
    for ids in groups:
        ins=[nodes[n]['instruction'] for n in ids]
        reads={x for i in ins for x in i.get('_reads',[])};writes={x for i in ins for x in i.get('_writes',[])}
        tags={i.get('_tag','') for i in ins};kinds=[];other=[]
        if any(x.startswith('GU') and x[2:].isdigit() for x in reads) and any(x.startswith('ACT') for x in writes):kinds=['SW']
        elif any(t.endswith('.moe_sum') for t in tags) and 'Y' in writes:kinds=['MOE']
        elif 'QA' in reads and 'QR' in writes:kinds=['QN']
        elif 'KVA' in reads and 'KVN' in writes:kinds=['KV']
        elif reads & {'G12'} and 'SCL' in writes:kinds=['RA']
        elif 'SC' in reads and 'BI' in writes:kinds=['RB']
        elif 'WGT' in writes and 'SC' in reads:kinds=['RW']
        elif 'Q' in reads and 'Q' in writes:kinds=['QR']
        elif 'ZA' in reads and 'ZA' in writes:kinds=['QB']
        elif any(t.endswith('.softmax') for t in tags):kinds=['SE','SO']
        elif any(any(t.endswith(s) for s in ('.hc_attn','.hc_ffn','.attn_norm','.ffn_norm','.hc_post')) or t=='head' for t in tags):
            other=['HC/HCP/HCT_SOURCE_LOWERING_REQUIRED']
        else:other=['UNIMPLEMENTED_EXACT_NATIVE_GROUP_LOWERING']
        stages={assignments[n]['stage'] for n in ids}
        if len(stages)!=1:raise ValueError('source colocation requirement split')
        rows.append(dict(source_nodes=ids,template_sha256={n:nodes[n]['template_word_sha256'] for n in ids},
            candidate_stage=next(iter(stages)),required_native_SU_kinds=kinds,other_native_requirements=other,
            exact_kernel_equivalence=False,native_job_ids=None,operand_storage_binding=None,calendar=None,
            note='Kinds are symbolic ABI requirements, not admitted native opcode bindings or fusion proofs.'))
    return rows


def generate(source,program,demand,candidate,out):
    out.mkdir(parents=True,exist_ok=True)
    new=transform(source,PATCHES);newp=transform(program,PROGRAM_PATCHES)
    verify_identity(source,new,PATCHES);verify_identity(program,newp,PROGRAM_PATCHES)
    outputs={NEW+'.sv':new,NEW_PROGRAM+'.sv':newp,'ot_s81_su_canonical_candidate.sv':WRAPPER}
    for name,text in outputs.items():(out/name).write_text(text)
    req=requirements(demand,candidate)
    stages=sorted({r['candidate_stage'] for r in req})
    instances=[]
    for stage in stages:
        for rank in range(4):
            instances.append(dict(stage=stage,rank=rank,die_id=4*stage+rank,source_module='ot_s81_su_canonical_candidate',
                proposed_source_instance='u_native',actual_GEN_instance=None,physical_instance=None,
                role='su',programme_id=None,core_epoch=None,physical_slot=None,source_clock_entries=159,
                source_clock_qualification=False,calendar_storage=dict(depth=4096,bits=4194304,
                    actual_64x512_macros=128,actual_capacity_sufficient=None)))
    report=dict(schema='opentallas.s81.native-source-generation.v1',native_qualified=False,dispatch_eligible=False,
        actual_elaborated_leaf_inventory=False,source_commit=SOURCE_COMMIT,
        source_parent_sha256=hashlib.sha256(source.encode()).hexdigest(),source_programmed_parent_sha256=hashlib.sha256(program.encode()).hexdigest(),
        generated_sha256={name:hashlib.sha256(text.encode()).hexdigest() for name,text in outputs.items()},
        source_clock_entries=dict(residual_parent=1,SW576=152,MOE=6,total=159,physical_qualified=False,
                                  caveat='Residual source clock remains shared; all sink/insertion/spread and physical clock proof open.'),
        SW576_source_children=dict(SWE=144,SWE_lanes=4,QBE=6,QBE_blocks=18,tap_clock_entries=2),
        source_deployment_requirements=instances,source_group_requirements=req,
        source_SU_operations=sum(len(r['source_nodes']) for r in req),source_group_count=len(req),
        grouped_chains=len(candidate['source_private_SU_colocation_groups']),
        unresolved=['Actual source kernel equivalence/opcode/operand-memory lowering for every group, including HC/HCP/HCT.',
                    'Real GEN native instances/leaf slots and independent native VM composition.',
                    'Residual parent clock partition, every clock physical gate, TT/FF/DRC.',
                    'Fixed programmes/coreepochs/calendars, exact SRAM capacity and global producer-consumer transfers.',
                    'MTP auxiliary operations/programmes outside this canonical catalogue.'])
    (out/'native_source_inventory.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ('demand','candidate','out'):ap.add_argument('--'+n,type=Path,required=True)
    ap.add_argument('--source-root',type=Path)
    a=ap.parse_args()
    def src(name):return (a.source_root/HIER/name).read_text() if a.source_root else git_source(HIER+name)
    r=generate(src(OLD+'.sv'),src(OLD_PROGRAM+'.sv'),read(a.demand),read(a.candidate),a.out)
    print(json.dumps({k:v for k,v in r.items() if k not in ('source_deployment_requirements','source_group_requirements')}))
if __name__=='__main__':main()
