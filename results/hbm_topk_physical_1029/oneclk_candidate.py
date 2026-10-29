#!/usr/bin/env python3
"""Emit ONE-CLK physical RTL and plan delta from the current source-alias contract.
Candidate only, default logical master unchanged; no P&R launched.
"""
import argparse,json,re,hashlib,shutil,copy
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('plan',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();repo=Path(__file__).resolve().parents[2]
q=Path(__file__).parent;r=json.load(open(q/'current_native_caller.json'));assert r['exact_clock_bit_equality'] and r['all_port_expressions_unchanged']
file=repo/'rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv';raw=file.read_text();assert hashlib.sha256(file.read_bytes()).hexdigest()==r['source_files']['rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv']
pos=raw.index('module ot_hbm_idx_topk_link_static #(');prefix=raw[:pos];public=raw[pos:]
old='input wire clk,input wire[7:0]clk_mem,input wire rst_n,';assert public.count(old)==1
newpublic=public.replace(old,'input wire clk,input wire rst_n,',1);end=newpublic.index('\n);')+4
newpublic=newpublic[:end]+'\n wire[7:0]clk_mem={8{clk}}; // exact current native source aliases; no new clock edge\n'+newpublic[end:]
assert newpublic.replace('input wire clk,input wire rst_n,',old,1).replace('\n wire[7:0]clk_mem={8{clk}}; // exact current native source aliases; no new clock edge\n','',1)==public
assert not a.out.exists();shutil.copytree(a.plan,a.out);(a.out/'source').mkdir()
phy=a.out/'source/ot_hbm_idx_topk_link_static.sv';phy.write_text(prefix+newpublic)
# Proof file shares the exact unchanged arithmetic core definition from the gold source.
(a.out/'source/physical_public_only.sv').write_text(newpublic.replace('module ot_hbm_idx_topk_link_static #(','module ot_hbm_idx_topk_link_static_physical_oneclk #(',1))
d=json.load(open(a.out/'die_plan.json'));ce=json.load(open(a.out/'clock_entries.json'));con=json.load(open(a.out/'core_conns.json'));cm=json.load(open(a.out/'core_macros.json'));rows=[]
for tn,t in d['partition_types'].items():
 for h in t.get('hard_cores',[]):
  if h['module']!='ot_hbm_idx_topk_link_static':continue
  oldfile=h['pins_file'];pins=json.load(open(a.plan/oldfile));gone=[x for x in pins if x['name'].startswith('clk_mem[')];assert len(gone)==8
  newpins=[x for x in pins if x not in gone];assert len(pins)==4597 and len(newpins)==4589
  newfile='cores/ot_hbm_idx_topk_link_static__oneclk_650p16x500p04.json';(a.out/newfile).write_text(json.dumps(newpins,indent=1)+'\n');h['pins_file']=newfile
  for key in ('lib','lef'):h.pop(key,None)
  ce[tn][h['inst']].update(port='clk',merged_clock_ports=[],source='CANDIDATE exact native scalar-clock physical wrapper; main root unchanged, fresh native sink tree required')
  assert con[tn][h['inst']]['clk']==con[tn][h['inst']]['clk_mem'];con[tn][h['inst']].pop('clk_mem')
  rows.append(dict(type=tn,inst=h['inst'],pins_before=len(pins),pins_after=len(newpins),removed_clock_pins=gone,main_clock_pin=next(x for x in newpins if x['name']=='clk'),actual_clock_entry=ce[tn][h['inst']],geometry_unchanged=dict(origin_um=h['origin_um'],outline_um=h['outline_um'],orient=h.get('orient','R0')),source_cycles_added=0,macro_instance_paths_unchanged=True))
assert len(rows)==1,'current die has one root TOPK link, not four copies'
cm['cores']['ot_hbm_idx_topk_link_static']['oneclk_candidate']='Only eight redundant native clock inputs removed; macro outlines/names/positions and all data/reset pins unchanged. New SIGNED view pending.'
for f,v in [('die_plan.json',d),('clock_entries.json',ce),('core_conns.json',con),('core_macros.json',cm)]: (a.out/f).write_text(json.dumps(v,indent=1)+'\n')
report=dict(schema='opentallas.hbm.topk_oneclk_candidate.v1',status='CANDIDATE_SOURCE_ONLY_ENABLE_HELD',source_plan_sha256=hashlib.sha256((a.plan/'die_plan.json').read_bytes()).hexdigest(),native_caller_sha256=r['candidate_sha256'],native_alias_expression=r['native_clock_expression'],physical_source_sha256=hashlib.sha256(phy.read_bytes()).hexdigest(),unchanged_core_definition_sha256=hashlib.sha256(prefix.encode()).hexdigest(),instances=rows,parameters={'WRITE_PIPE_STAGES':2},extra_oneclk_data_or_control_cycles=0,existing_write_visibility_cycles=2,main_pin_tap_unchanged=True,production_default_unchanged=True,build_hold='No CTS/GRT/STA until current bind plus reviewed new single-root FF+SRAM clock model/sink islands.')
(a.out/'oneclk_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'instances':1,'pins':4589,'extra_cycles':0,'physical_source_sha256':report['physical_source_sha256']}))
