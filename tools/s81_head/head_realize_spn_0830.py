#!/usr/bin/env python3
"""Trial HEAD spine kit with the plan's existing internal stations realized.

Consumes a complete SOURCE7 plan+sidecar; no replacement clock graph or stubs.
Existing plan register counts become RTL and FIRM geometry before synthesis.
"""
import argparse,json,sys
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('repo');ap.add_argument('source');ap.add_argument('out');a=ap.parse_args()
 root=Path(a.repo);src=Path(a.source);out=Path(a.out)
 sys.path[:0]=[str(root/'tools/die_plan'),str(root/'tools/s81_head')]
 import gen_phys,kit_istations
 from head_start_reset_aliases import patch_rtl
 plan_path=src/'source_plan.json';plan=json.load(open(plan_path));side=json.load(open(src/'source_sidecar.json'))
 kits=gen_phys.write_phys(plan,out,root,types=['hd_spn','hd_spn_end'],trial=True,plan_path=plan_path,landing=side)
 reports={}
 for k in kits:
  kit=Path(k);tn=kit.name;t=plan['partition_types'][tn];mod=t['module'];rtl=kit/'rtl';wrapper=rtl/(mod+'.sv')
  wrapper.write_text(patch_rtl(wrapper.read_text(),t.get('reset_start_raw_exports',[])))
  files=[str(wrapper)]+[str(x) for x in sorted(rtl.glob('*.sv')) if x!=wrapper]+[str(x) for x in sorted(rtl.glob('*.v'))]
  (rtl/'kit_rtl.json').write_text(json.dumps(dict(files=files,bound_module=mod)))
  kit_istations.main([str(plan_path),tn,str(rtl),'--apply'])
  (kit/'istations.tcl').write_text((rtl/'istations.tcl').read_text())
  with (kit/'face_flops.tcl').open('a') as f:f.write('\nsource /work/istations.tcl\n')
  reports[tn]=json.load(open(rtl/'kit_rtl.json'))['kit_istations']
 (out/'planned_station_realization.json').write_text(json.dumps(reports,indent=1)+'\n')
 print(json.dumps(reports))
if __name__=='__main__':main()
