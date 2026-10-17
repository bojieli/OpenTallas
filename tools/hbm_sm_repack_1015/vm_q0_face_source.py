#!/usr/bin/env python3
"""Additive q0 candidate: relocate existing boundary state onto four real clocks.

Uses the byte-pinned, actually consumed nat2 source capsule. No pipeline edge is
inserted or removed. All five clocks are related, equal-frequency die entries.
This generator prepares source only; typed pins and physical proof are separate.
"""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
CAP = ROOT / 'results/physical/hsm_takeover_0825/nat2_exact'
OUT = ROOT / 'rtl/hbm_accel/generic/vm/static/faces_q0'
OUT.mkdir(exist_ok=True)

def change(s, a, b):
    assert s.count(a) == 1, (a[:100], s.count(a))
    return s.replace(a, b)

s = (CAP / 'ot_vms_bank_static_strap.sv').read_text()
s = change(s, 'module ot_vms_bank_static_strap #(', 'module ot_vms_bank_q0_faces_body #(')
s = change(s, 'input wire clk, rst_n,', 'input wire clk, rst_n,\n    input wire clk_n, clk_s, clk_e, clk_w,')
# This is deliberately q0 only; no unsound generic face mapping.
s = change(s, 'if (RG < 1 || RG > 15 || WG < 1 || WG > 10)', 'if (RG != 5 || WG != 2)')
s = change(s, 's1r_v <= 0; eg_v <= 0;', 's1r_v <= 0;')
s = change(s, '            eg_v <= eg_c;\n', '')
s = change(s, '        eg_d <= (EG_WIDE != 0) ? eg_or[274:0] : wr_decode[274:0];\n', '')
pos = s.index('    // ------------------------------------------------------------------ S2: macro pins')
s = s[:pos] + '''    // Existing egress state belongs to the E pin clock, with no new edge.
    always @(posedge clk_e or negedge rn)
        if (!rn) eg_v <= 0; else eg_v <= eg_c;
    always @(posedge clk_e)
        eg_d <= (EG_WIDE != 0) ? eg_or[274:0] : wr_decode[274:0];
''' + s[pos:]
s = change(s, "            wq_done <= '0; dq_done <= 1'b0; kq_done <= 1'b0; xq_done <= 1'b0; xq2_done <= 1'b0;\n", '')
s = change(s, '''            for (integer g = 0; g < WG; g = g + 1) wq_done[g] <= s2w_v && s2w_p == 4'(g);
            dq_done <= s2w_v && s2w_p == 4'(WG+4); kq_done <= s2w_v && s2w_p == 4'(WG); xq_done <= s2w_v && s2w_p == 4'(WG + 1);
            xq2_done <= s2w_v && s2w_p == 4'(WG + 3);
''', '')
pos = s.index('    // capture flops:')
s = s[:pos] + '''    always @(posedge clk_w or negedge rn)
        if (!rn) begin wq_done[0] <= 0; xq_done <= 0; end
        else begin wq_done[0] <= s2w_v && s2w_p == 0;
                   xq_done <= s2w_v && s2w_p == 4'(WG+1); end
    always @(posedge clk_e or negedge rn)
        if (!rn) begin wq_done[1] <= 0; xq2_done <= 0; end
        else begin wq_done[1] <= s2w_v && s2w_p == 1;
                   xq2_done <= s2w_v && s2w_p == 4'(WG+3); end
    always @(posedge clk_s or negedge rn)
        if (!rn) dq_done <= 0; else dq_done <= s2w_v && s2w_p == 4'(WG+4);
    always @(posedge clk_n or negedge rn)
        if (!rn) kq_done <= 0; else kq_done <= s2w_v && s2w_p == 4'(WG);
''' + s[pos:]
s = change(s, "rr_v <= '0; pr_v <= 1'b0; ue <= 1'b0; status <= 18'd0;", "ue <= 1'b0;")
s = change(s, "            for (integer g = 0; g < RG; g = g + 1) rr_v[g] <= d_v && d_p == 4'(g);\n", '')
s = change(s, "            pr_v <= (d_v && d_p == 4'(RG)) || dw_v;\n", '')
s = change(s, '            status <= {flt, ue, ce};\n', '')
s = change(s, '''        for (integer g = 0; g < RG; g = g + 1)
            if (d_v && d_p == 4'(g)) rr_d[g*256 +: 256] <= cor;
        pr_d <= (d_v && d_p == 4'(RG)) ? {1'b0, d_tag, cor} : {1'b1, dw_tag, 256'd0};
''', '')
pos = s.rindex('endmodule')
s = s[:pos] + '''    // Genvar selects a wire, never a runtime clock mux.
    for (genvar f = 0; f < 5; f = f + 1) begin : face_response
        wire face_clk;
        if (f == 0 || f == 4) assign face_clk = clk_w;
        else if (f == 1) assign face_clk = clk_e;
        else if (f == 2) assign face_clk = clk_n;
        else assign face_clk = clk_s;
        always @(posedge face_clk or negedge rn)
            if (!rn) rr_v[f] <= 0; else rr_v[f] <= d_v && d_p == 4'(f);
        always @(posedge face_clk)
            if (d_v && d_p == 4'(f)) rr_d[f*256 +: 256] <= cor;
    end
    always @(posedge clk_s or negedge rn)
        if (!rn) pr_v <= 0; else pr_v <= (d_v && d_p == 4'(RG)) || dw_v;
    always @(posedge clk_s)
        pr_d <= (d_v && d_p == 4'(RG)) ? {1'b0,d_tag,cor} : {1'b1,dw_tag,256'd0};
    always @(posedge clk_n or negedge rn)
        if (!rn) status <= 0; else status <= {flt,ue,ce};
''' + s[pos:]
(OUT / 'ot_vms_bank_q0_faces_body.sv').write_text(s)

core = (CAP / 'q0_core_renamed.sv').read_text()
core = change(core, 'module hfd_vms_bank_native_q0__ot_pr_core(', 'module ot_vms_bank_q0_faces_core(')
core = change(core, 'input wire clk,', 'input wire clk, clk_n, clk_s, clk_e, clk_w,')
core = change(core, 'ot_vms_bank_static_strap #(', 'ot_vms_bank_q0_faces_body #(')
core = change(core, '.clk(clk),', '.clk(clk), .clk_n(clk_n), .clk_s(clk_s), .clk_e(clk_e), .clk_w(clk_w),')
(OUT / 'ot_vms_bank_q0_faces_core.sv').write_text(core)

wrapper = (CAP / 'q0_wrapper.v').read_text()
wrapper = change(wrapper, 'module hfd_vms_bank_native_q0 (', 'module hfd_vms_bank_native_q0_faces (')
wrapper = change(wrapper, 'bid, sid, clk, rst_n', 'bid, sid, clk, clk_n, clk_s, clk_e, clk_w, rst_n')
wrapper = change(wrapper, '  input clk;', '  input clk, clk_n, clk_s, clk_e, clk_w;')
faces = {'w': ['rq0','rq4','wq0','xq'], 'e':['rq1','wq1','xq2'],
         's':['rq3','dq','pq'], 'n':['rq2','kq','bid','sid','rslot_v','rslot','wslot_v','wslot']}
for face, names in faces.items():
    for name in names:
        wrapper = change(wrapper, f'always @(posedge clk) {name}__ot_q', f'always @(posedge clk_{face}) {name}__ot_q')
wrapper = change(wrapper, 'hfd_vms_bank_native_q0__ot_pr_core u_ot_pr_core', 'ot_vms_bank_q0_faces_core u_ot_pr_core')
wrapper = change(wrapper, '.clk(clk),', '.clk(clk), .clk_n(clk_n), .clk_s(clk_s), .clk_e(clk_e), .clk_w(clk_w),')
(OUT / 'hfd_vms_bank_native_q0_faces.sv').write_text(wrapper)
receipt = {'status':'SOURCE_CANDIDATE_ONLY', 'normal_edges_added':0, 'return_edges':7, 'write_done_edges':4,
           'clock_ports':['clk','clk_n','clk_s','clk_e','clk_w'], 'input_face_ownership':faces,
           'files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.sv')}}
(ROOT / 'results/physical/hsm_takeover_0825/q0_faces_source.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
