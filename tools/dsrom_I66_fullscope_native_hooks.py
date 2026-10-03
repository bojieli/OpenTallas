#!/usr/bin/env python3
"""Additive I66..I105 native emitter; no PC cutoff, no selected-provider emulation.
The predecessor emitter stays pinned. Source extraction includes real W2 phases,
but consumer nin/footprints never determine ROM writer counts. No launch here.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import dsrom_I66_native_observer as N
import dsrom_I66_existing_ready_fences as F
import dsrom_I66_source_interlock as I

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_I66_fullscope_native_hooks_20261003'
NAME='ot_v41_rt_die_i66_fullscope'
PREFIX='I66FULLHOOK'
CAPTURED=[66,67,68,69,72,73,82,83,87,88,92,93]
W2=[79,84,89,94,97,100]


def pincheck():
    for p,h in json.loads((OUT/'source_pins.json').read_text()).items():
        if N.sha((ROOT/p).read_bytes())!=h: raise ValueError('source identity changed: '+p)


def descriptors():
    pincheck(); layout=F.layout()
    demand=json.loads(gzip.decompress((N.D.OUT/'inputs/demand-r5.json.gz').read_bytes()))
    nodes={n['instruction_index']:n for n in demand['nodes']
           if n.get('kind')=='instruction' and n.get('scope')==0 and 66<=n['instruction_index']<=107}
    words={r['node']:r for r in json.loads((OUT/'inputs/all18_QE_words.json').read_text())}
    if set(nodes)!=set(range(66,108)) or len(words)!=18:raise ValueError('full selected source range missing')
    result=[]
    for pc,n in sorted(nodes.items()):
        word=F.encode(layout,n['instruction'])
        if N.sha(word.to_bytes(256,'little'))!=n['template_word_sha256']:raise ValueError('instruction template changed')
        intended=word
        if pc in CAPTURED+W2:
            intended=int(words[n['id']]['word_hex'],16);I.uint(intended,2048)
            allowed=0
            for f in ['qe_wbase','qe_istride']:
                off,width=layout[f];allowed|=((1<<width)-1)<<off
            if (word^intended)&~allowed:raise ValueError('patch changed nonaddress source fields')
        decoded={k:(intended>>off)&((1<<w)-1) for k,(off,w) in layout.items()}
        result.append(dict(pc=pc,node=n['id'],source_instruction=n['instruction'],decoded=decoded,
                           template_sha256=n['template_word_sha256'],intended_sha256=N.sha(intended.to_bytes(256,'little')),
                           intended_word_hex=f'{intended:0512x}',source_patch_is_actual_program_enrollment=False))
    gu0=[r['pc'] for r in result if r['decoded']['unit']==3 and r['decoded']['qe_mode']==0]
    if gu0!=sorted(CAPTURED+W2):raise ValueError('all18 source GU0 phases required')
    if result[0]['intended_sha256']!='7d6b2b75445e34120a69fbe6fad3e6bffc7be53734200f3386f33fbe3c514dc5':
        raise ValueError('current I66 word mismatch')
    return result


def block():
    # Preserve all predecessor observations, with a new namespace/schema.
    b=N.observer_block()
    additions='''        // All PCs and pipeline tails remain observable; never stop at PC105.
        longint unsigned saved_retire_edge;
        reg [7:0] saved_retire_seq;
        always @(posedge clk) begin
'''
    additions+=N.display('clock',dict(rst_n='rst_n',sim_time_ns='$time'))
    additions+=N.display('SU_shape',dict(pc=N.C+'.pc',seq=N.U+'.seq',nin=N.C+'.su_nin',nout=N.C+'.su_nout',
       m=N.C+'.mx_m',asrc=N.C+'.a_src',csrc=N.C+'.c_src',abase=N.C+'.a_base',cbase=N.C+'.c_base',
       aso=N.C+'.a_so',asi=N.C+'.a_si',cso=N.C+'.c_so',csi=N.C+'.c_si',cpair=N.C+'.c_pair'),
       'rst_n && '+N.C+'.su_go && !'+N.U+'.pend')
    additions+=N.display('vector_shape',dict(seq=N.U+'.seq',copy=N.U+'.cp',nin=N.U+'.nin',nout=N.U+'.nout',
       m=N.U+'.m_r',asrc=N.U+'.asrc',csrc=N.U+'.csrc',abase=N.U+'.abase',cbase=N.U+'.cbase',xo=N.U+'.xo'),
       'rst_n && '+N.U+'.v_acc')
    additions+=N.display('vector_retire',dict(seq=N.V+'.ret_p_seq',last=N.V+'.ret_p_last',
       fault=N.C+'.su_fault'), 'rst_n && '+N.V+'.ret_p')
    additions+='''            if (rst_n && dut.u_tile.u_core.g_su_x.u_su.u_vec.ret_p &&
                       dut.u_tile.u_core.g_su_x.u_su.u_vec.ret_p_last) begin
                saved_retire_edge = i66_edge;
                saved_retire_seq = dut.u_tile.u_core.g_su_x.u_su.u_vec.ret_p_seq;
                $strobe("I66HOOK post %0d %0d vector_done seq=%h cr_dseq=%h",
                    saved_retire_edge, RANK, saved_retire_seq, dut.u_tile.u_core.g_su_x.u_su.u_vec.cr_dseq);
            end
        end
        for (genvar s = 0; s < ROM_R; s = s + 1) begin : g_roots
            always @(posedge clk) if (rst_n && dut.u_tile.u_core.g_rom.r_v[s])
                $display("I66HOOK pre %0d %0d root_sample root=%h row=%h pos=%h fp32=%h bf16=%h error=%h",
                    i66_edge, RANK, s, dut.u_tile.u_core.g_rom.r_row[s*16 +: 16],
                    dut.u_tile.u_core.g_rom.r_pos[s*3 +: 3], dut.u_tile.u_core.g_rom.r_fp32[s*32 +: 32],
                    dut.u_tile.u_core.g_rom.r_bf16[s*16 +: 16], dut.u_tile.u_core.g_rom.r_e[s]);
        end
'''
    marker='    end endgenerate\n'
    if b.count(marker)!=1:raise ValueError('predecessor shape changed')
    return b.replace(marker,additions+marker,1).replace('I66HOOK',PREFIX)


def generate():
    pincheck(); source=(N.INPUT/'runtime_wrapper.sv.txt').read_text()
    return source.replace('module ot_v41_rt_die #(',f'module {NAME} #(\n    parameter integer I66_OBSERVE = 0,',1).replace('endmodule',block()+'endmodule',1)


def inverse(text):
    a=text.index(N.BEGIN);b=text.index(N.END)+len(N.END)
    if text[a:b]!=block():raise ValueError('unreviewed observer body')
    raw=(text[:a]+text[b:]).replace(f'module {NAME} #(\n    parameter integer I66_OBSERVE = 0,','module ot_v41_rt_die #(',1)
    if raw!=(N.INPUT/'runtime_wrapper.sv.txt').read_text():raise ValueError('protected inverse changed')
    return N.sha(raw.encode())


def schema():
    # Full packed signal widths bound to FULL_SHAPE/AW30/VM_AW19/SUN256/G4/W16/SW8.
    writer_widths={
       'ww_h':[1,30,32,1024], 'rom':[128,3840,4096], 'vw_me':[4,120,64,2048],
       'vw_su':[8,240,256], 'vw_rd':[8,240,256], 'xs_vm':[256,7680,8192],
       'xs_res':[32,960,1024], 'vw_xe':[1,30,32], 'ww_q':[1,30,32,1024],
       'ww_x':[1,30,32,1024], 'xa':[1,15,512], 'xb':[4,60,2048]}
    events={
     'edge':dict(rst_n=1,pc=14,st=4,unit=3,wait_mask=5,skip=1,waited=1,unit_ready=1,q_gate=1,kv_gate=1,m0_gate=1,idles=5,gos=5,coll_busy=1,faults=24,user10=10,writer_mask=12),
     'issue_sample':dict(pc=14,unit=3,qe_mode=2,word=2048),
     'rom_accept':dict(pc=14,key=30,stride=30,indexed=1,ibase=30,obase=30),
     'adapter':dict(st=3,s_go=1,s_idle=1,s_ready=1,key=30,hit=1,phase=10,vi_re=1,vi_addr=30,vi_q=32,fault=1),
     'SU_front':dict(pc=14,seq=8,abase=30,cbase=30),
     'vector_accept':dict(seq=8,copy=3,abase=30,cbase=30),
     'Xtag':dict(cw=196,cw_width=32),
     'VM':dict(root=32,address=30,value=32),
     'read':dict(port=32,src=2,address=30,value=32),
     'clock':dict(rst_n=1,sim_time_ns=64),
     'SU_shape':dict(pc=14,seq=8,nin=21,nout=21,m=3,asrc=2,csrc=2,abase=30,cbase=30,aso=30,asi=30,cso=30,csi=30,cpair=1),
     'vector_shape':dict(seq=8,copy=3,nin=21,nout=21,m=3,asrc=2,csrc=2,abase=30,cbase=30,xo=30),
     'vector_retire':dict(seq=8,last=1,fault=1),
     'vector_done':dict(seq=8,cr_dseq=8),
     'root_sample':dict(root=32,row=16,pos=3,fp32=32,bf16=16,error=1)}
    for k, signals in N.WRITERS.items():events['writer_'+k]=dict(zip(signals,writer_widths[k]))
    return dict(version='opentallas.PHW10.native-fullscope.raw.v1',prefix=PREFIX,
       grammar='I66FULLHOOK pre|post EDGE_decimal RANK_decimal KIND NAME=HEX ...',
       regions={k:('post' if k in ['VM','vector_done'] else 'pre') for k in events},event_fields=events,
       edge_clock='Per-rank native posedge count includes reset; common origin/domain conversion requires actual driver proof.',
       same_edge_order='Only pre/post regions are causal order. Different active-region always blocks/roots have no promised log order. Join by rank/edge/source port, not lexical event arrival.',
       time_field='$time in pinned 1ns/1ps wrapper: rounded simulator ns, not physical CDC or exact picosecond admission.',
       Xtag_seq=dict(offset=58,width=8,source='WD130 + WR66 AW30; cwx[65:58]',read_to_tag_edges=2),
       writer_mask_order_MSB_first=list(N.WRITERS),
       tail_policy='Emitter has no PC or cycle cutoff. Downstream must observe native last vector retirement/postNBA cr_dseq and all tracked read R+2 tags, plus separate selected packet/address lease retirement. EOF/PC105 is not retirement.',
       source_context='Raw user10/seq8/key30/phase10; full169 provider context must come from actual enrolled provider sidecar, never fabricated from PC/ready.',
       selected_provider_events_emitted=False,physical_calendar_qualified=False)


def parse(lines):
    spec=schema();result=[];last={};seen=set()
    for line in lines:
        if not line.startswith(PREFIX+' '):continue
        tokens=line.split()
        if len(tokens)<6 or tokens[4] not in spec['event_fields'] or tokens[1]!=spec['regions'][tokens[4]]:
            raise ValueError('unknown event or source NBA region')
        if not tokens[2].isdigit() or not tokens[3].isdigit():raise ValueError('decimal edge/rank required')
        edge,rank=int(tokens[2]),int(tokens[3]);I.uint(edge,64);I.uint(rank,2)
        if edge<last.get(rank,0):raise ValueError('backward edge')
        last[rank]=edge;values={}
        for token in tokens[5:]:
            if token.count('=')!=1:raise ValueError('malformed field')
            key,value=token.split('=')
            if key in values or not value or any(c not in '0123456789abcdefABCDEF' for c in value):raise ValueError('invalid hex field')
            values[key]=int(value,16)
        widths=spec['event_fields'][tokens[4]]
        if set(values)!=set(widths):raise ValueError('missing/extraneous raw fields')
        for key,width in widths.items():I.uint(values[key],width)
        kind=tokens[4]
        if kind in ['root_sample','VM'] and values['root']>=128:raise ValueError('root out of range')
        if kind=='read' and (values['port']>=1024 or values['src']!=0):raise ValueError('non-VM native read')
        if kind=='Xtag' and values['cw_width']!=196:raise ValueError('compiled vector controlword mismatch')
        if kind=='vector_done' and values['seq']!=values['cr_dseq']:raise ValueError('postNBA native retirement mismatch')
        port=values.get('root') if kind in ['VM','root_sample'] else values.get('port') if kind=='read' else None
        event_key=(rank,edge,kind,port)
        if event_key in seen:raise ValueError('repeated source event/acceptance in same native edge')
        seen.add(event_key)
        result.append(dict(edge=edge,rank=rank,kind=kind,region=tokens[1],fields=values))
    if not result:raise ValueError('no fullscope native callbacks')
    return result


def model():
    desc=descriptors();by={r['pc']:r for r in desc};w2=[]
    for producer in W2:
        base=by[producer]['decoded']['qe_obase'];uses=[]
        for pc in range(101,106):
            row=by[pc]['decoded']
            for operand in ['a','b','c','d']:
                if row['unit']==2 and row[operand+'_src']==0 and row[operand+'_base']==base:
                    uses.append(dict(pc=pc,operand=operand,read_nin=row['su_nin']))
        if len(uses)!=1 or uses[0]['read_nin']!=1280:raise ValueError('exact W2 source consumer changed')
        w2.append(dict(pc=producer,obase=base,source_qe_nb=by[producer]['decoded']['qe_nb'],
                       source_qe_nout=by[producer]['decoded']['qe_nout'],uses=uses,
                       actual_writer_count=None,writer_count_inferred_from_consumer=False,intercept_576_seats=False))
    text=generate();inverse(text)
    return dict(scope='CURRENT_SOURCE_FULL18_GU0_PASSIVE_HOOKS_AND_FROZEN_RAW_SCHEMA',
       primary_range=[66,105],source_tail_context=[106,107],source_descriptors=desc,
       captured_W1_W3=CAPTURED,native_W2=W2,W2_consumers=w2,
       captured_phase_count=12,native_W2_phase_count=6,total_GU0_phases=18,
       beyond105=dict(pc106_reads_other_VM_base=by[106]['decoded']['c_base'],
                     pc106_owner_not_assigned_to_I100=True,
                     pc107_source_collective_wait=by[107]['decoded']['wait'],
                     collection_stop_PC=None,actual_tail_retirement_required=True),
       raw_schema_version=schema()['version'],generated_sha256=N.sha(text.encode()),inverse_sha256=inverse(text),
       predecessor_immutable='9709cbe00298c34fe7efe828b2ad64407c266788',
       new_observer_state_bits=N.model()['observer_state_bits']+72,new_observer_state_bytes=1521,
       new_hardware_ports=0,new_hardware_state=0,engine_drives=0,default_off=True,
       emitter_owner='Hubble',downstream_lifetime_F_composition_owner='Nash/user',
       elaboration_owner='Hubble; preparation only, no compiler/GO or current matched archive exists',
       native_384_runtime_dispatch_implemented=False,
       current_compiled_binary=None,current_journal=None,trace_handle=None,
       max_live_versions=None,absolute_F=None,absolute_service_deadline=None,
       unknown_rate_terms=['actual fullprogram PHW10 registered acceptance and first/last read endpoints',
          'all18 native publication counts and VM version lease overlap through post105 R+2/retirement',
          'positive captured credit/wire ACK/provider retirement callbacks and finite accepted service',
          'selected VM publication arbitration/exclusion and address lease schedule',
          'actual loaded parent clock/reset phases and streaming/SU CDC accepted cadence',
          'full169 user32 ownership codec, finite C/station control and all384 stage dispatch implementation'],
       compile_admission=False,functional_candidate_selected=False,heavy_job_launched=False,
       fulltoken=False,hardware_admission=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--generate',type=Path);p.add_argument('--model',type=Path)
    p.add_argument('--schema',type=Path);p.add_argument('--parse',type=Path)
    a=p.parse_args()
    for path, value in [(a.model,model if a.model else None),(a.schema,schema if a.schema else None)]:
        if path:path.write_text(json.dumps(value(),sort_keys=True,indent=2)+'\n')
    if a.generate:a.generate.write_text(generate())
    if a.parse:print(json.dumps(parse(a.parse.read_text().splitlines()),sort_keys=True,indent=2))
