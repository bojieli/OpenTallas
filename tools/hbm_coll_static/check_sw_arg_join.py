#!/usr/bin/env python3
"""Fail closed if the selected-mechanism bench diverges from parent wiring.

This is a structural boundary check, not whole-parent elaboration. Nonselected
TKM/reduce/ring/link subtrees are explicitly outside the gate's scope.
"""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'rtl/hbm_accel/generic/collective/p2p'

def norm(s): return re.sub(r'\s+','',s)
def instance(text,name):
    start=re.search(r'\b'+re.escape(name)+r'\s*\(',text)
    if not start: raise AssertionError('Missing real instance '+name)
    begin=start.end();depth=1;i=begin
    while depth:
        if text[i]=='(':depth+=1
        elif text[i]==')':depth-=1
        i+=1
    chunk=text[begin:i-1];ports={};i=0
    while i<len(chunk):
        m=re.search(r'\.([A-Za-z_][A-Za-z_0-9]*)\s*\(',chunk[i:])
        if not m:break
        key=m[1];a=i+m.end();b=a;depth=1
        while depth:
            if chunk[b]=='(':depth+=1
            elif chunk[b]==')':depth-=1
            b+=1
        ports[key]=norm(chunk[a:b-1]);i=b
    return ports

def check():
    parent=(P/'ot_hfd_coll_q_static_v2.sv').read_text();bench=(P/'tb_hgi_coll_sw_arg_join.sv').read_text()
    layout=json.loads((P/'static_uop_layout_v2.json').read_text())
    checked=[]
    # The arithmetic/switch/mode wiring is pinned explicitly to current parent.
    pairs={
     'u_arg':{
      'start':('a_arg_start','ar[48]'),
      'cfg_g':('p_tkm_cfg_g','inst[761+:8]'),
      'cfg_gbase':('p_tkm_cfg_gbase','inst[769+:8]'),
      'cfg_rank':('a_pub_src','ar[23+:8]'),
      'in_slot':('a_arg_in_slot & {4{a_arg_mode}}','ar[51+:4] & {4{arg_mode}}'),
      'in_v':('dest_v[NPT+8+:4] & {4{a_arg_mode}}','actual_arg_v'),
      'in_flit':('dest_d[(NPT+8)*545+:2180]','dd[11*545+:2180]'),
      'flush_slot':('a_arg_flush','ar[49]'),'publish_slot':('a_arg_publish','ar[50]')},
     'u_writer':{'rgx_v':('dest_v[NPT+4+:4]','dv[7+:4]'),
      'rgx_addr':('rgx_addr','rgxaddr'),'rgx_data':('rgx_data','writer_data'),
      'rgx_vm':('p_rgx_vm','inst[584]'),'ingress_slot':('p_vm_ingress_slot','inst[585+:5]'),
      'slot_valid':('p_vm_slot_valid','inst[590+:8]'),'slot_owner':('p_vm_slot_owner','inst[598+:32]')},
     'u_qslots':{'capture_slot':('capture_calendar','{inst[712],inst[9:0]}'),
      'sink_slot':('p_sink_slot[ND-1:0]','inst[10+:16]'),
      'sink_select':('p_sink_select[ND*SELW-1:0]','inst[26+:64]')},
     'u_control':{'inst':('inst','inst'),'iteration':('iteration','iteration'),
      'dest_v':('dest_v','dv'),'vm_rr':('vm_rr','vm_rr'),
      'rgx_addr_pin':('rgx_addr_pin','rgxaddr'),'vm_source_meta':('vm_source_meta','vmmeta'),
      'vm_assembled':('vm_assembled','assembled'),'vm_assembled_v':('vm_assembled_v','assembled_v')},
     'u_issuer':{'cfg':('program_cfg','cfg'),'uop':('uop','uop'),'iteration':('iteration','iteration')}}
    for name,ports in pairs.items():
        pp,bp=instance(parent,name),instance(bench,name)
        for port,(pe,be) in ports.items():
            assert pp[port]==norm(pe),(name,port,'parent changed')
            assert bp[port]==norm(be),(name,port,'bench changed')
            checked.append(name+'.'+port)
    for token in ['assign source_v[NPT+7]=arg_out_v;',
                  'assign source_d[(NPT+7)*545+:545]=arg_out_data;',
                  '.del_valid(dest_v[NPT+8+:4] & {4{!a_arg_mode}})',
                  '.del_slot(p_tkm_del_slot & {4{!a_arg_mode}})']:
        assert norm(token) in norm(parent),token
    for token in ['wire [3:0] actual_arg_v=dv[11+:4] & {4{arg_mode}};',
                  'wire [3:0] excluded_tkm_v=dv[11+:4] & {4{!arg_mode}};',
                  'wire [3:0] excluded_tkm_slots=inst[719+:4] & {4{!arg_mode}};',
                  'assign sv[10]=av;assign sd[10*545+:545]=ad;']:
        assert norm(token) in norm(bench),token
    assert layout['ar_fields']['arg_mode']=={'lsb':47,'width':1}
    assert layout['ar_fields']['arg_in_slot']=={'lsb':51,'width':4}
    for name,lsb,width in [('tkm_cfg_g',761,8),('tkm_cfg_gbase',769,8),('vm_meta',1170,132),('vm_pair_select',1383,24)]:
        assert layout['fields'][name]=={'lsb':lsb,'width':width}
    assert 'for(integer row=0;row<64;row=row+1)' in bench
    return {'status':'PASS','checked_parent_child_ports':checked,'selected_instances':list(pairs),
      'excluded_subtrees':['TKM','reduction','ring','links'],
      'scope':'selected native parent mechanism with checked connection expressions and ISA fields; not fullq3'}
if __name__=='__main__':print(json.dumps(check(),indent=2))
