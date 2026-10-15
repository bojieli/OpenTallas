#!/usr/bin/env python3
"""Build a wires-only join of real native controller/compute/memory/IO RTL.

No missing producer is tied off. Every unjoined child input is an explicit top
input. Physical roots remain individual pins; unknown route ages fail closed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from die_port_bind import parse_modules

NODES={
 'tt':('qfd_tt_ctlm_static_s','rtl/qwen_sys/static_schedule_20261014/qfd_tt_ctlm_static_s.sv','a7e79de10'),
 'seq':('qfd_seq_su_static','rtl/qwen_split/qfd_seq_su_static.sv','96f30a6a0'),
 'su':('qfd_sp_su64_sfu','rtl/qwen_split/qfd_sp_su64_sfu.sv','96f30a6a0'),
 'vm':('qfd_sp_vector_memory','rtl/qwen_sys/vm_nox_20261014/qfd_sp_vector_memory.sv','96f30a6a0'),
 'native':('qfd_native59_compute_service','rtl/qwen_split/qfd_native59_compute_service.sv','575a85850'),
 'io':('qfd_collective_static_io','rtl/physical/ot_qfd_collective_static_io.sv','8d92a8870'),
 'embed':('qkd_embedding_static_core_provider','rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_provider.sv','96f30a6a0')}


def load_nodes():
    nodes={}
    for name,(top,path,ref)in NODES.items():
        text=subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT,text=True)
        mods=[m for m in parse_modules(text,path)if m.name==top]
        if len(mods)!=1 or mods[0].port_parse_errors:raise ValueError(f'{name}: incomplete actual source ABI')
        mod=mods[0];ports={p:dict(direction=mod.ports[p][0],bits=mod.width(p,mod.env()))for p in mod.order}
        if name=='io' and ports['relay_ck']['bits']is None:
            # Exact selected source uses a Verilog ternary for the zero-relay
            # case, unsupported by the generic header arithmetic evaluator.
            width_expr=str(mod.ports['relay_ck'][1])
            if '2*(2*RU+RS0+RS1+RS2)'not in width_expr:raise ValueError('changed actual relay-root width expression')
            env=mod.env();ports['relay_ck']['bits']=max(1,2*(2*int(env['RU'])+int(env['RS0'])+int(env['RS1'])+int(env['RS2'])))
        if any(s['bits']is None or s['direction']not in('input','output')for s in ports.values()):raise ValueError(name)
        nodes[name]=dict(top=top,source=path,source_ref=ref,source_sha256=hashlib.sha256(text.encode()).hexdigest(),ports=ports)
    return nodes


def build(nodes):
    # Each expression is checked against its real source ports. Ordered slices
    # are explicit wire connections, never inferred arithmetic or status.
    joins=[];assigned={};used_outputs=set()
    def wire(label,source,sinks,select=None):
        n,p=source;s=nodes[n]['ports'][p]
        if s['direction']!='output':raise ValueError(f'{source}: producer is not real output')
        width=s['bits']if select is None else select[0]-select[1]+1
        if select is not None and not(0<=select[1]<=select[0]<s['bits']):raise ValueError('invalid source bit selection')
        for a,b in sinks:
            sink=nodes[a]['ports'][b]
            if sink!=dict(direction='input',bits=width):raise ValueError(f'{label}: actual width/direction mismatch {a}.{b}: {sink} vs {width}')
            if(a,b)in assigned:raise ValueError('multiply-driven actual input')
            assigned[(a,b)]=label
        used_outputs.add(source)
        joins.append(dict(name=label,source=list(source),select=select,bits=width,sinks=[list(q)for q in sinks]))
    def w(label,src,dst,sel=None):wire(label,tuple(src.split('.')),[tuple(p.split('.'))for p in dst.split()],sel)
    w('copy_active','su.cp_active','tt.cp_active')
    w('copy_command','tt.cp','su.cp')
    w('su_image_ready','seq.cfg_image_ready','tt.su_image_ready')
    w('su_issue_observer','seq.su_observe','tt.su_observe')
    w('me_status','tt.xm','seq.xm');w('su_status','seq.xs','tt.xs');w('me_start','seq.st','tt.st')
    w('su_command','seq.su','su.si');w('su_result_status','su.sd','seq.sd');w('su_accepted','su.acc','seq.acc')
    w('su_a_request','su.external_a_re','seq.su_va_re');w('su_a_address','su.external_a_addr','seq.su_va_addr')
    w('su_a_value','seq.su_va_q','su.external_a_q');w('su_vm_a_request','seq.su_vm_va_re','su.external_vm_a_re')
    w('su_vm_a_address','seq.su_vm_va_addr','su.external_vm_a_addr')
    w('su_vm_request','su.va','vm.sa');w('su_vm_values','vm.sq','su.vq');w('su_vm_a_values','vm.sq','seq.su_vm_va_q',(2047,0))
    w('me_vm_write','tt.mx','vm.mx');w('me_land_count','vm.ld','tt.ld');w('me_memory_ready','vm.mo','tt.meok')
    w('me_vm_enable','tt.mee','vm.mee',(0,0))
    w('seq_vm_read','seq.vrd','vm.svr');w('seq_vm_value','vm.svq','seq.vrq');w('seq_vm_read_valid','vm.svq_v','seq.svq_v')
    w('seq_vm_write','seq.vwr','vm.svw')
    for a,b in [('native_cmd','native_cmd'),('native_tok','native_token'),('native_pos','native_position'),('layer_context_v','layer_context_v'),('command_stage','command_stage')]:w('native_'+a,'tt.'+a,'native.'+b)
    w('native_return','native.native_ret','tt.native_ret')
    for p in('native_issue','kv_we','kv_waddr','kv_wdata'):w('native_'+p,'su.'+p,'native.'+p)
    w('native_vm_write','native.vm_ar','vm.ar');w('native_q_epoch','native.vm_q_epoch','vm.q_epoch');w('native_q_start','native.vm_q_start','vm.q_start')
    for a,b in [('q_committed','q_committed'),('q','q'),('write_commit_v','write_commit_v'),('write_commit_line','write_commit_line'),('write_commit_mask','write_commit_mask'),('fault','q_fault')]:w('vm_native_'+a,'vm.'+a,'native.'+b)
    for p in('embed_code_re','embed_code_addr','embed_scale_re','embed_scale_addr'):w(p,'seq.'+p,'embed.'+p)
    for p in('embed_code_q','embed_scale_q'):w(p,'embed.'+p,'seq.'+p)
    w('embed_start','seq.embed_scale_re','embed.core_start');w('embed_token','seq.embed_scale_addr','embed.core_token')
    w('embed_fault','embed.fault','su.external_embed_fault')
    # Actual cd547 and command50 field layout, preserving every payload bit.
    for label,p,hi,lo in [('payload','in_data',511,0),('last','in_last',512,512),('mode','in_mode',513,513),('tag','in_tag',545,514),('valid','in_valid',546,546)]:w('coll_'+label,'seq.cd_d','io.'+p,(hi,lo))
    for label,p,hi,lo in [('v','cmd_v',49,49),('mode','cmd_mode',16,16),('words','cmd_words',15,0),('tag','cmd_tag',48,17)]:w('coll_cmd_'+label,'seq.coll_cmd','io.'+p,(hi,lo))
    w('coll_cmd_observed_free','io.cmd_free','seq.coll_cmd_free')
    # The return word is concatenated once from actual source outputs below.
    assigned[('seq','cc')]='coll_return'
    ret=[('out_valid',1),('out_err',1),('out_rank',3),('out_last',1),('out_data',512)]
    for p,n in ret:
        if nodes['io']['ports'][p]!=dict(direction='output',bits=n):raise ValueError('wrong collective return ABI')
        used_outputs.add(('io',p))
    return dict(nodes=nodes,joins=joins,assigned=assigned,used_outputs=used_outputs,return_parts=ret)


def render(model):
    nodes=model['nodes'];assigned=model['assigned'];used=model['used_outputs']
    lines=['`timescale 1ns/1ps','// Real wires-only native compute/control join; external ports are unresolved REAL hardware boundaries.',
      '// Individual clocks require actual physical phi-R delivery; defaults refuse unassigned production route ages.',
      'module qfd_native_compute_join #(parameter integer XPF_TRANSPORT_EDGES=-1,NATIVE_PROFILE=1,',
      ' parameter integer VM_ROUTE_QUALIFIED=0,VM_FORWARD_EDGES=-1,VM_RETURN_EDGES=-1,VM_PHASE_EDGES=-1) (']
    ext=[]
    for name,node in nodes.items():
        for p,s in node['ports'].items():
            if s['direction']=='input'and(name,p)in assigned:continue
            if s['direction']=='output'and(name,p)in used:continue
            ext.append((name,p,s))
    for k,(n,p,s)in enumerate(ext):lines.append(' '+s['direction']+' wire '+(f"[{s['bits']-1}:0] "if s['bits']>1 else'')+n+'_'+p+(','if k<len(ext)-1 else''))
    lines+=[');']
    for n,p in sorted(used):
        width=nodes[n]['ports'][p]['bits'];lines.append(' wire '+(f'[{width-1}:0] 'if width>1 else'')+f'w_{n}_{p};')
    expr={}
    for j in model['joins']:
        n,p=j['source'];e=f'w_{n}_{p}'
        if j['select']is not None:
            h,l=j['select'];e+=f'[{h}:{l}]'
        for n,p in j['sinks']:expr[(n,p)]=e
    expr[('seq','cc')]='{'+','.join('w_io_'+p for p,n in model['return_parts'])+'}'
    params={'tt':'#(.XPF_TRANSPORT_EDGES(XPF_TRANSPORT_EDGES))','su':'#(.EXTERNAL_EMBED(1))',
        'vm':'#(.USE_MACRO(1),.USE_LEAF_CLOCKS(1))',
        'native':'#(.NATIVE_PROFILE(NATIVE_PROFILE),.VM_ROUTE_QUALIFIED(VM_ROUTE_QUALIFIED),.VM_FORWARD_EDGES(VM_FORWARD_EDGES),.VM_RETURN_EDGES(VM_RETURN_EDGES),.VM_PHASE_EDGES(VM_PHASE_EDGES))'}
    for n,node in nodes.items():
        lines.append(' '+node['top']+' '+params.get(n,'')+' u_'+n+' (')
        for k,(p,s)in enumerate(node['ports'].items()):
            e=expr.get((n,p),('w_'+n+'_'+p)if(n,p)in used else n+'_'+p)
            lines.append(f'  .{p}({e})'+(','if k<len(node['ports'])-1 else''))
        lines.append(' );')
    lines+=['endmodule','']
    return '\n'.join(lines),ext


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--rtl',type=Path,default=ROOT/'rtl/qwen_split/qfd_native_compute_join.sv');a=p.parse_args()
    m=build(load_nodes());rtl,ext=render(m);a.out.mkdir(parents=True,exist_ok=True)
    a.rtl.parent.mkdir(parents=True,exist_ok=True);a.rtl.write_text(rtl)
    manifest=dict(schema='opentallas.qwen.actual-native-compute-join.v1',qualified=False,
      scope='real source-output to source-input wires; no physical roots/homes/route ages or whole-die workload qualification',
      nodes=m['nodes'],joins=m['joins'],actual_clock_roots={n:sum(s['bits']for p,s in node['ports'].items()if s['direction']=='input'and(p in('ck','clk','face_ck','relay_ck')or p.startswith(('ck_','clk_'))))for n,node in m['nodes'].items()},external_ports=[dict(node=n,port=p,**s)for n,p,s in ext],
      source_register_edges=dict(copy_active=1,su_image_ready=1,su_issue_observer=1,native_return=1),
      clock_binding='all real roots exposed independently; no common phase or physical insertion invented',
      default_profile='production1, unknown routes refuse; diagnostic0 requires explicit nonnegative component ages and remains unqualified',
      critical_unassigned=['TT kok/kwd current KV visibility and fabric fault aggregation','all per-face licensed PHY capacities and external native59 transport','actual HOST/store/reservation/calendar sources','all real pin/child placements and timing/source-equivalent physical views'],
      rtl_sha256=hashlib.sha256(rtl.encode()).hexdigest())
    (a.out/'actual_join.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(nodes=len(m['nodes']),joins=len(m['joins']),external_ports=len(ext),qualified=False)))
if __name__=='__main__':main()
