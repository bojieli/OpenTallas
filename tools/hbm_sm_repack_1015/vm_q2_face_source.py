#!/usr/bin/env python3
"""q2 RG5/WG3 derivative of the source-proved q0 face-clock candidate."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[2]
CAP=ROOT/'results/physical/hsm_takeover_0825/nat2_exact'
Q0=ROOT/'rtl/hbm_accel/generic/vm/static/faces_q0'
OUT=Q0.parent/'faces_q2';OUT.mkdir(exist_ok=True)
s=(Q0/'ot_vms_bank_q0_faces_body.sv').read_text().replace('ot_vms_bank_q0_faces_body','ot_vms_bank_q2_faces_body').replace('RG != 5 || WG != 2','RG != 5 || WG != 3')
a="    always @(posedge clk_n or negedge rn)\n        if (!rn) kq_done <= 0; else kq_done <= s2w_v && s2w_p == 4'(WG);"
assert s.count(a)==1;s=s.replace(a,a+"\n    always @(posedge clk_n or negedge rn)\n        if (!rn) wq_done[2] <= 0; else wq_done[2] <= s2w_v && s2w_p == 2;")
(OUT/'ot_vms_bank_q2_faces_body.sv').write_text(s)
c=(CAP/'q2_core_renamed.sv').read_text().replace('hfd_vms_bank_native_q2__ot_pr_core','ot_vms_bank_q2_faces_core').replace('input wire clk,','input wire clk, clk_n, clk_s, clk_e, clk_w,').replace('ot_vms_bank_static_strap #(','ot_vms_bank_q2_faces_body #(').replace('.clk(clk),','.clk(clk),.clk_n(clk_n),.clk_s(clk_s),.clk_e(clk_e),.clk_w(clk_w),')
(OUT/'ot_vms_bank_q2_faces_core.sv').write_text(c)
w=(CAP/'q2_wrapper.v').read_text().replace('module hfd_vms_bank_native_q2 (','module hfd_vms_bank_native_q2_faces (').replace('bid, sid, clk, rst_n','bid, sid, clk, clk_n, clk_s, clk_e, clk_w, rst_n').replace('  input clk;','  input clk, clk_n, clk_s, clk_e, clk_w;').replace('hfd_vms_bank_native_q2__ot_pr_core u_ot_pr_core','ot_vms_bank_q2_faces_core u_ot_pr_core').replace('.clk(clk),','.clk(clk),.clk_n(clk_n),.clk_s(clk_s),.clk_e(clk_e),.clk_w(clk_w),')
faces={'w':['rq0','rq4','wq0','xq'],'e':['rq1','wq1','xq2'],'s':['rq3','dq','pq'],'n':['rq2','kq','wq2','bid','sid','rslot_v','rslot','wslot_v','wslot']}
for f,names in faces.items():
 for n in names:
  a=f'always @(posedge clk) {n}__ot_q';assert w.count(a)==1;w=w.replace(a,f'always @(posedge clk_{f}) {n}__ot_q')
(OUT/'hfd_vms_bank_native_q2_faces.sv').write_text(w)
t=(Q0/'tb_hbm_vm_q0_faces.sv').read_text().replace('q0_faces','q2_faces').replace('SID=0,RG=5,WG=2','SID=2,RG=5,WG=3').replace('.wq_done0(wide_done[b*WG]),.wq_done1(wide_done[b*WG+1]));','.wq_done0(wide_done[b*WG]),.wq_done1(wide_done[b*WG+1]),\n          .wq2(wq[(b*WG+2)*281+:281]),.wq_done2(wide_done[b*WG+2]));')
(OUT/'tb_hbm_vm_q2_faces.sv').write_text(t)
r=(Q0/'run.sh').read_text().replace('q0_faces','q2_faces').replace('Q0_FACE_CLOCKS','Q2_FACE_CLOCKS').replace('faces_q0','faces_q2')
(OUT/'run.sh').write_text(r);(OUT/'run.sh').chmod(0o755)
rec={'status':'SOURCE_CANDIDATE_ONLY','quadrant':2,'RG':5,'WG':3,'normal_edges_added':0,'return_edges':7,'write_done_edges':4,'input_face_ownership':faces,'files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.sv')}}
(ROOT/'results/physical/hsm_takeover_0825/q2_faces_source.json').write_text(json.dumps(rec,indent=2)+'\n')
print('q2 source candidate generated; no physical adoption')
