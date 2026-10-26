#!/usr/bin/env python3
"""Compile the source-bound TP8 full-context six-root AHUB schedule.

All ages are edges after its external start sample; arithmetic is the actual
four ot_nhb_zh trees and ot_qkh_recip_leaf, including their pin stages. This
component profile has no PBST/PVLG and makes no physical clock qualification.
"""
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['rtl/hdc/nearhbm/ot_qkd_ahub_static.sv','rtl/hdc/nearhbm/ot_qkd_ahub_core.sv','rtl/hdc/nearhbm/ot_nhb_tiles.sv','rtl/hdc/nearhbm/ot_qkh_recip_leaf.sv','rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv','rtl/hdc/ot_hdc_fp32_add_lat_nr.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv']
def compile_calendar(lmax_in,z_in,stride,lmax_issue,z_start,recip_issue,zw=0,zr=0,rx=1,ry=1,publish=None):
 if len(lmax_in)!=4 or len(z_in)!=4 or stride<4 or min(*lmax_in,*z_in,lmax_issue,z_start,recip_issue)<1:
  raise ValueError('unsealed/invalid calendar')
 if lmax_issue<=max(lmax_in)+4:raise ValueError('lmax read precedes final input commit')
 if z_start<=max(z_in)+16*stride+2+zw:raise ValueError('Z issue precedes declared done/final write')
 gap=10+zw+zr
 levels=[];base=z_start
 for level in range(1,7):
  pairs=64>>level;bursts=(pairs+3)//4
  levels.append({'level':level,'pairs':pairs,'issues':[{'edge':base+b,'pair_base':4*b,'lane_mask':(1<<min(4,pairs-4*b))-1} for b in range(bursts)]})
  base+=bursts+gap
 last=levels[-1]['issues'][-1]['edge']
 # Measured actual leaf root appears post last_issue+13 with no relays.
 # Core captures root one edge later; reciprocal rc_x output samples that copy.
 if recip_issue<last+15+zw+zr:raise ValueError('reciprocal read precedes real Z root visibility')
 # rc_v output pin, RX relays, recip input pin,64 arithmetic edges, output
 # pin, RY relays; consumer captures on the following edge.
 recip_return=recip_issue+67+rx+ry
 if publish is None:publish=recip_return+4
 if publish<recip_return+4:raise ValueError('publication precedes final reciprocal commit')
 inputs=[]
 for stack in range(4):
  words=[{'edge':lmax_in[stack]+h,'type':0,'head':h,'block':0}for h in range(4)]
  words += [{'edge':z_in[stack]+k*stride+h,'type':1,'head':h,'block':k} for k in range(16)for h in range(4)]
  words += [{'edge':z_in[stack]+16*stride,'type':2,'head':0,'block':0}]
  if len({w['edge']for w in words})!=len(words):raise ValueError('sideband input port conflict')
  inputs.append({'stack':stack,'words':words})
 return dict(schema='qwen-tp8-static-ahub-v1',scope='actual six-root component, T8192 HEADS1; native producer and phi-R integration pending',
  roots={'core':1,'ZH':4,'reciprocal':1},removed_legacy_roots={'PBST':4,'PVLG':4},
  source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in SOURCES},
  parameters=dict(LMAX_IN_AGE=lmax_in,Z_IN_AGE=z_in,Z_IN_STRIDE=stride,LMAX_ISSUE_AGE=lmax_issue,Z_START_AGE=z_start,Z_LEVEL_GAP=gap,
   RECIP_ISSUE_AGE=recip_issue,RECIP_RETURN_AGE=recip_return,RZ_PUBLISH_AGE=publish,ZW_RLY=zw,ZR_RLY=zr,RX_RLY=rx,RY_RLY=ry),
  inputs=inputs,lmax_outputs=list(range(lmax_issue+3,lmax_issue+7)),tree_levels=levels,
  reciprocal_outputs=list(range(recip_return,recip_return+4)),publication=publish,
  arithmetic={'ZH_fp32_adders':16,'ZH_add_latency':7,'ZH_reduction_terms_per_head':64,'reciprocal_core_depth':64,'reciprocal_leaf_pin_stages':2,'reciprocal_NR_iterations':3,'rounding':'actual source FP32 at every multiply/add'})
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args()
 c=compile_calendar([100]*4,[200]*4,16,110,470,555,publish=630)
 text=json.dumps(c,indent=2)+'\n'
 if a.output:a.output.write_text(text)
 else:print(text,end='')
if __name__=='__main__':main()
