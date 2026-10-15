#!/usr/bin/env python3
"""Exact proposed source-instance/native-profile binding from q8 pin geometry.
No production RTL is changed and no view is adopted by this manifest.
"""
import hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]

def main():
 raw=subprocess.check_output(['git','show','eaca93a88:results/arch/s81_vm_direct_q8_1015/report.json'],cwd=R);geo=json.loads(raw)
 faces={r['bank']:r['output_face'] for r in geo['captures']};assert faces==dict(enumerate(['W']*4+['E']*4))
 entries=[]
 def profile(tag):
  p=R/f'physical/ref_tile/dsfd_vm_direct_{tag}_native/spec.json';d=json.loads(p.read_text());j=json.loads((p.parent/'job.json').read_text())
  return dict(master=d['top'],kit=str(p.parent.relative_to(R)),job=j['name'],source_commit=j['source']['commit'],source_files=d['sources'],assigned_pins=d['io_tcl'],assigned_pins_sha256=hashlib.sha256((R/d['io_tcl']).read_bytes()).hexdigest(),status='ACTUAL_PROFILE_GATE_PASSED; routedviews/adoptionmustbeverifiedseparately')
 pp={tag:profile(tag) for tag in ['capture_e','capture_w','scatter_b0','scatter_b8','scatter_b16','scatter_b24']}
 for s in range(4):
  for q in range(4):
   for b in range(8):
    p=pp['capture_'+faces[b].lower()];entries.append(dict(source_instance=f'dsfd_sp_vm.u_core.u_mem.slice[{s}].u_slice.write_group[{q}].capture[{b}].u_capture',source_bank=8*q+b,source_slice=s,prototype_geometry_bank=b,required_output_face=faces[b],required_native_master=p['master'],required_kit=p['kit'],clock_category_bit=f'ck_wcapture[{32*s+8*q+b}]',source_protocol='OneexistingcaptureFFstage, namedpins1:1, inputslotJ=8*(BANK%4)+BANK/4; no addedcycle',adoption_status='REQUIRED_NOT_IMPLEMENTED_BY_THIS_MANIFEST'))
   p=pp[f'scatter_b{8*q}'];entries.append(dict(source_instance=f'dsfd_sp_vm.u_core.u_mem.slice[{s}].u_slice.write_group[{q}].u_w',source_slice=s,source_bank_base=8*q,required_native_master=p['master'],required_kit=p['kit'],clock_category_bit=f'ck_wscatter[{4*s+q}]',source_protocol='OneexistingoutputFFstage, eightrecords, BANK_BASEcompileconstant, no addedcycle',adoption_status='REQUIRED_NOT_IMPLEMENTED_BY_THIS_MANIFEST'))
 assert len(entries)==144
 result=dict(schema='opentallas.s81.vm-direct-write-native-profile-binding.v1',status='SOURCE_GEOMETRY_EXACT_BINDING_PROPOSAL_NOT_PARENT_ADOPTION',primitive_source='b5f79878e',geometry_commit='eaca93a88',geometry_report_sha256=hashlib.sha256(raw).hexdigest(),profiles=pp,entries=entries,replicas={p['master']:sum(e['required_native_master']==p['master'] for e in entries) for p in pp.values()},clock_roots=144,registered_stages_along_each_write_path=2,cycles_added=0,required=['Useonlyexactprofileviewsourceandpinfile, noEtoWorB0toB8inheritance','ActualclosednativeTTFFSSLEF/Lib/insertion/childlintrecords perprofile','Productionhardparentmustinstantiatecorrectnativeprofilemasterandconnectitsactualcategoryclock/resetpins','Fullstaticcompiler128SRAMjoinedprogram, nativeparentperbitreach/cuts/PG/IO/TTFFDRC0/throughput'])
 out=R/'physical/s81_vm_direct_write_native_1015/profile_binding.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['replicas'],indent=2))
if __name__=='__main__':main()
