#!/usr/bin/env python3
"""Audit actual consumed abstract arcs separately from current regional source."""
import argparse,hashlib,json,re
from pathlib import Path
PORTS=[('cmd_wo','cmd_ei',116),('hr_wo','hr_ei',453),('st_wo','st_ei',1088),('sc_wo','sc_ei',48),('rv_wo','rv_ei',1),('re_wo','re_ei',1),('rr_wo','rr_ei',3),('rl_wo','rl_ei',1),('rd_wo','rd_ei',512),('dr_wo','dr_ei',520)]
def block(text,pattern):
 m=re.search(pattern,text)
 if not m: raise ValueError('missing block '+pattern)
 start=m.end();depth=1;i=start
 while depth:
  if text[i]=='{':depth+=1
  elif text[i]=='}':depth-=1
  i+=1
 return text[start:i-1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--libs',type=Path,required=True);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--spec',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 v=json.loads((a.libs/'views.json').read_text());assumed=v.get('assumed_clock_insertion',{}).get('qfd_dv_slice2_e')
 if not assumed:raise ValueError('expected actual g5 ASSUMED parent classification')
 spec=json.loads(a.spec.read_text());src=a.source.read_text()
 tw=re.search(r'qfd_dv_slice2_e_tw\s+u_tw\s*\((.*?)\);',src,re.S)
 if not tw or '.ck(ck_wf)' not in tw[1]:raise ValueError('source u_tw not on ck_wf')
 rows=[];shas={}
 for c in ['tt','ff']:
  p=a.libs/f'qfd_elements_{c}.lib';t=p.read_text();shas[c]=hashlib.sha256(p.read_bytes()).hexdigest();cell=block(t,r'cell\s*\(qfd_dv_slice2_e\)\s*{')
  for sp,rp,w in PORTS:
   arcs={}
   for port in [sp,rp]:
    b=block(cell,r'bus\s*\('+port+r'\)\s*{');arcs[port]=sorted(set(re.findall(r'related_pin\s*:\s*"([^"]+)"',b)))
   if '.'+sp+'('+sp+')' not in tw[1] or spec['port_regions'].get(rp)!='ef':raise ValueError('source ownership mismatch '+rp)
   rows.append(dict(corner=c,src_port=sp,dst_port=rp,bits=w,consumed_abstract_related_pin=arcs,
    consumed_owner_qualified=False,source_candidate_tx='u_tw/ck_wf',source_candidate_rx='ck_ef',
    source_candidate_native_bound=False,physical_phase_qualified=False,requested_added_edges=5))
 rec=dict(schema='opentallas.qwen.slice_face_clock_ownership.v1',consumed_view='ASSUMED',reason=assumed,
  actual_lib_sha256=shas,source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),spec_sha256=hashlib.sha256(a.spec.read_bytes()).hexdigest(),
  rows=rows,summary=dict(per_corner_ports=10,rows=20,bits_per_corner=2743,native_owned_rows=0,physical_qualification_eligible=False))
 a.out.write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec['summary']))
if __name__=='__main__':main()
