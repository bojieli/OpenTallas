"""Pinned source/header identity audit; no syntax or runtime qualification."""
import re,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w17_window_core_cancel_source_ports_repair as source
ADDITIONAL={
 'coll_dst':('output','[AW-1:0]'),'coll_ibase':('output','[AW-1:0]'),
 'coll_fault':('input',''),'m0d_tiles':('output','[NW-1:0]'),'m0d_k':('output','[NW-1:0]'),
 'kvd_ts':('output','[AW-1:0]'),'kvd_ks':('output','[AW-1:0]'),'kvd_js':('output','[AW-1:0]'),
 'kvd_k':('output','[NW-1:0]'),'kvd_nout':('output','[NW-1:0]'),'kvd_pos':('output','[NW-1:0]')}

def actual():
 r,t,o,e=source.generate('fastpp');h=o[:source.header_end(o)]
 return r,t,h,e

def test_old_firstname_regex_exposes_exact_eleven_omissions():
 r,t,h,e=actual();full={name for _,_,name in source.parse_ports(h)}
 old=set(re.findall(r'^\s*(?:input|output)\s+(?:wire|reg)\s*(?:\[[^\]]+\])?\s*(\w+)',h,re.M))
 assert len(old)==228 and len(full)==239 and full-old==set(ADDITIONAL)

@pytest.mark.parametrize('name',ADDITIONAL)
def test_every_added_name_has_inherited_width_two_forwardings_and_bench_connection(name):
 r,text,h,e=actual();ports={n:(d,w) for d,w,n in source.parse_ports(h)}
 assert ports[name]==ADDITIONAL[name]
 wrapper=text[:text.index('module '+r['module']+'_legacy #(')]
 assert wrapper.count('.'+name+'('+name+')')==2 # default and enabled branches
 tb=(ROOT/'rtl/test/w17_window_core_cancel_join_r7/tb.sv').read_text()
 assert tb.count('.'+name+'(core_'+name+')')==1
 declaration=re.search(r'^(?:logic|wire)\s*(\[[^\]]+\])?\s*core_'+name+r'(?:=0)?;',tb,re.M)
 assert declaration and (declaration.group(1) or '')==ADDITIONAL[name][1]

def test_complete_wrapper_and_bench_named_port_sets_equal():
 r,text,h,e=actual();original=source.parse_ports(h)
 wrapper=text[:text.index('module '+r['module']+'_legacy #(')]
 start=wrapper.index('module '+r['module']+' #(');end=source.header_end(wrapper[start:])
 header=wrapper[start:start+end];all_ports=source.parse_ports(header)
 assert len(original)==239 and len(all_ports)==252
 tb=(ROOT/'rtl/test/w17_window_core_cancel_join_r7/tb.sv').read_text()
 connections=re.findall(r'^\.(\w+)\(core_(\w+)\)',tb,re.M)
 assert len(connections)==252 and len(set(connections))==252
 assert all(a==b for a,b in connections)
 assert {a for a,b in connections}=={n for _,_,n in all_ports}

def test_coll_fault_remains_material_source_fault_input():
 r,text,h,e=actual()
 assert '(FULL_SHAPE && (coll_fault || rope_pf_fault))' in e
 wrapper=text[:text.index('module '+r['module']+'_legacy #(')]
 assert wrapper.count('.coll_fault(coll_fault)')==2
 tb=(ROOT/'rtl/test/w17_window_core_cancel_join_r7/tb.sv').read_text()
 assert 'logic  core_coll_fault=0;' in tb and 'core_coll_fault=0;' in tb
 assert '.coll_fault(core_coll_fault)' in tb

def test_inheritance_parser_control_does_not_silently_drop_second_name():
 ports=source.parse_ports('module m #(parameter integer W=3) (input wire [W-1:0] a,b, output reg q,r);')
 assert ports==[('input','[W-1:0]','a'),('input','[W-1:0]','b'),('output','','q'),('output','','r')]
