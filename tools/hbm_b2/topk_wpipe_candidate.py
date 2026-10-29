#!/usr/bin/env python3
"""Emit an explicit TOPK WRITE_PIPE_STAGES=2 native caller, never a default.

The approved e1c9d6e0d source and compact-tree dependency are copied by hash.
This candidate adds two internal SRAM write-visibility edges; outer ports and
calendar edges are unchanged. Current native proof and physical gates remain.
"""
import argparse,copy,hashlib,json,re,subprocess,sys
from pathlib import Path

SOURCES={
 'rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv':'a95d85e5a5f9822f2e7063b3c34b4c65312810a0a433c5527231da6a56703e97',
 'rtl/hbm_accel/index/ot_hbm_idx_compact_tree.sv':'2b0367e7da1118f5441caac4cb8d2b976ea4389256d3b8f2aa87450241317b92'}
REV='e1c9d6e0d'

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('top',type=Path);p.add_argument('manifest',type=Path)
 p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
 p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 sys.path.insert(0,str(a.repo/'tools/hbm_b2'))
 from b2_top import Die,parse_expr
 if a.out.exists():p.error('use a fresh candidate directory')
 original=Die(a.top,{})
 name='hb_idx__link';obj=original.insts[name]
 if obj['master']!='ot_hbm_idx_topk_link_static' or 'WRITE_PIPE_STAGES' in obj['params']:
  p.error('actual native TOPK source identity or unselected parameter contract differs')
 cp=parse_expr(obj['conns']['clk'],original.widths)
 cm=parse_expr(obj['conns']['clk_mem'],original.widths)
 if len(cp)!=1 or cp[0][0]!='n' or cp[0][2]!=cp[0][3] or cm!=cp*8:
  p.error('all eight native SRAM clocks must be the exact same source bit as clk')
 source=a.top.read_text()
 rx=re.compile(r'^(\s+ot_hbm_idx_topk_link_static)(?:\s*#\(([^\n]*)\))?\s+hb_idx__link\s*\(',re.M)
 def patch(m):
  prior=(m[2] or '').strip()
  return m[1]+' #('+(prior+', ' if prior else '')+'.WRITE_PIPE_STAGES(2)) hb_idx__link ('
 candidate,n=rx.subn(patch,source)
 if n!=1:p.error('exactly one native TOPK caller is required')
 a.out.mkdir(parents=True);newtop=a.out/'top.sv';newtop.write_text(candidate)
 changed=Die(newtop,{})
 assert set(changed.insts)==set(original.insts)
 for key,spec in original.insts.items():
  got=changed.insts[key]
  assert spec['master']==got['master'] and spec['conns']==got['conns'],key
  if key!=name:assert spec['params']==got['params'],key
 manifest=copy.deepcopy(json.loads(a.manifest.read_text()))
 pinned=[]
 for path,digest in SOURCES.items():
  payload=subprocess.check_output(['git','-C',str(a.repo),'show',REV+':'+path])
  if hashlib.sha256(payload).hexdigest()!=digest:raise ValueError('approved source bytes changed: '+path)
  dst=a.out/'source'/Path(path).name;dst.parent.mkdir(exist_ok=True);dst.write_bytes(payload);pinned.append(str(dst.resolve()))
 manifest['netlist']=[str(newtop.resolve())]
 manifest['files']=list(dict.fromkeys(manifest.get('files',[])+pinned))
 manifest['prefer']=[s for s in manifest.get('prefer',[]) if s not in pinned]+pinned
 mf=a.out/'asbuilt.json';mf.write_text(json.dumps(manifest,indent=1)+'\n')
 receipt=dict(schema='opentallas.hbm.topk_wpipe_native_caller.v1',instance=name,
              source_sha256=hashlib.sha256(source.encode()).hexdigest(),
              candidate_sha256=hashlib.sha256(candidate.encode()).hexdigest(),
              native_clock_expression=obj['conns']['clk'],native_clock_mem_expression=obj['conns']['clk_mem'],
              exact_clock_bit_equality=True,other_callers_unchanged=True,all_port_expressions_unchanged=True,
              parameter=dict(WRITE_PIPE_STAGES=2),approved_source_revision=REV,source_files=SOURCES,
              added_internal_write_visibility_cycles=2,added_outer_input_output_cycles=0,
              status='CANDIDATE_ONLY_PRODUCTION_ENABLE_HELD',
              obligations=['actual native caller bit proof','two SRAM visibility edges in model/compiler',
                           'current source bind','new physical profile and review before placement',
                           'TT setup FF hold signoff'])
 (a.out/'caller.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('TOPK native candidate WPIPE2; exact eight SRAM clock aliases; ports unchanged; +2 internal write edges')

if __name__=='__main__':main()
