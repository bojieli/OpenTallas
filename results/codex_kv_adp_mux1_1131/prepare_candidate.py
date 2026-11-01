from pathlib import Path
import json,re
r=Path('/srv/opentallas-scratch2/claude/codex-kv-adp-mux1-1131')
old='ot_sram_1r1w_512x128_m4_r2c2';new='ot_sram_1r1w_512x128_m1_r2c2'
s=(r/'face_core.v').read_text();rx=re.compile(r'(^\s*)'+old+r'(\s+\\?\S+\s*\(.*?\);)',re.M|re.S)
assert len(rx.findall(s))==1,'exactly one native SRAM instance required'
s=rx.sub(lambda m:m[1]+new+re.sub(r'\.rr_addr\([^)]*\)',".rr_addr(18'h00000)",m[2]),s)
assert s.count(new)==1
(r/'qkd_hr_phy_adp_mux1.v').write_text(s)
c=json.loads((r/'core_base.json').read_text());c['files']=[str(r/'qkd_hr_phy_adp_mux1.v'),str(r/'views'/new/(new+'_bb.v'))]
c['candidate_profile']=dict(enabled=False,origin='native qualified compiler mux1 replacement + validated face recut',cycles_added=0,source_face='qkd_hr_phy_adp exactkeep+credit retime post0/mut1/emitted0',memory_exactness='native M4/M1 model+independent shadow3584 checks, address-bit mutant caught, exhaustive65536-bit wordmap bijection',held='Canonical adoption requires actual timing/geometry/signoff gates; no old-master proof receipt is relabeled as a new-master proof.')
(r/'core_mux1.json').write_text(json.dumps(c,indent=1)+'\n')
for label,x in [('A',25.92),('B',17.28)]:
 p=dict(module='qkd_hr_phy_adp',outline_um=[103.68,95.04],halo_um=4.32,cycles_added=0,pg_pin_layer='M4',static_rows=True,grid_um=8.64,track_offset_um=[0,0],children={new:str(r/'views'/new)},blocks=[dict(inst='u_slice.u_body.g_grp[0].u_rb.g_sram.g_t[0].u_m',master=new,x=x,y=8.64,orient='R0')])
 (r/f'plan_{label}.json').write_text(json.dumps(p,indent=1)+'\n')
