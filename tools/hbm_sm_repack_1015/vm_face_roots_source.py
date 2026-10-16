#!/usr/bin/env python3
"""Additive native VM clock domains derived from exact per-quadrant pin faces."""
import hashlib,json,pathlib,re
R=pathlib.Path(__file__).resolve().parents[2];D=R/'rtl/hbm_accel/generic/vm/static'
s=(D/'ot_vms_bank_static_local_roots.sv').read_text()
s=s.replace('module ot_vms_bank_static_local_roots #(','module ot_vms_bank_static_face_roots #(',1)
s=s.replace('parameter integer MUT = 0','parameter [RG*2-1:0] R_FACE = {RG{2\'d3}},\n    parameter [WG*2-1:0] W_FACE = {WG{2\'d3}},\n    parameter integer MUT = 0',1).replace('input wire [5:0] clk_local','input wire [11:0] clk_local',1)
# Map former internal domains, then replace whole shared input/output blocks.
for old,new in [(5,11),(4,7),(3,6),(2,5),(1,4),(0,0)]:s=s.replace(f'posedge clk_local[{old}]',f'posedge FACE_TMP[{new}]')
s=s.replace('FACE_TMP','clk_local').replace('ce_pipe(.clk(clk_local[5])','ce_pipe(.clk(clk_local[8])')
a=s.index('    always @(posedge clk_local[0]) begin');b=s.index('    // output registers:',a)
s=s[:a]+'''    // The physical grant names each port face; no capture is shared across faces.
    for(genvar g=0;g<RG;g=g+1)begin:g_face_read_capture
        always @(posedge clk_local[R_FACE[g*2+:2]]) rq_d[g*17+:17] <= rq[g*17+:17];
        always @(posedge clk_local[R_FACE[g*2+:2]] or negedge rn)
            if(!rn)rq_v[g]<=0;else rq_v[g]<=rq[g*17+16];
    end
    for(genvar g=0;g<WG;g=g+1)begin:g_face_write_capture
        always @(posedge clk_local[W_FACE[g*2+:2]])wq_d[g*281+:281]<=wq[g*281+280]?wq[g*281+:281]:281'd0;
        always @(posedge clk_local[W_FACE[g*2+:2]] or negedge rn)
            if(!rn)wq_v[g]<=0;else wq_v[g]<=wq[g*281+280];
    end
    always @(posedge clk_local[0])kq_d<=kq[280]?kq:281'd0;
    always @(posedge clk_local[1])x2_d<=xq2[275]?xq2:276'd0;
    always @(posedge clk_local[3])xq_d<=xq[275]?xq:276'd0;
    always @(posedge clk_local[2])begin
        pq_d<=pq;dq_d<=dq[280]?dq:281'd0;
        pqw_d<=(pq[284]&&pq[283])?pq[282:8]:275'd0;
    end
    always @(posedge clk_local[0] or negedge rn)if(!rn)kq_v<=0;else kq_v<=kq[280];
    always @(posedge clk_local[1] or negedge rn)if(!rn)x2_v<=0;else x2_v<=xq2[275];
    always @(posedge clk_local[3] or negedge rn)if(!rn)xq_v<=0;else xq_v<=xq[275];
    always @(posedge clk_local[2] or negedge rn)
        if(!rn)begin pq_v<=0;dq_v<=0;end else begin pq_v<=pq[284];dq_v<=dq[280];end
'''+s[b:]
# Egress is actual E-face boundary state, independent of the S1 decode root.
s=s.replace(' eg_v <= 0;','').replace('            eg_v <= eg_c;\n','').replace('        eg_d <= wr_decode[274:0];','')
pos=s.index('    // ------------------------------------------------------------------ S2:')
s=s[:pos]+'''    always @(posedge clk_local[9] or negedge rn)if(!rn)eg_v<=0;else eg_v<=eg_c;
    always @(posedge clk_local[9])eg_d<=wr_decode[274:0];
'''+s[pos:]
# Done signals preserve the macro write edge and move to their actual faces.
s=s.replace("            wq_done <= '0; dq_done <= 1'b0; kq_done <= 1'b0; xq_done <= 1'b0; xq2_done <= 1'b0;\n",'')
a=s.index('            // done =');b=s.index('            c_v <=',a);s=s[:a]+s[b:]
pos=s.index('    // capture flops:')
done='''    for(genvar g=0;g<WG;g=g+1)begin:g_face_write_done
        always @(posedge clk_local[8+W_FACE[g*2+:2]] or negedge rn)
            if(!rn)wq_done[g]<=0;else wq_done[g]<=s2w_v&&s2w_p==4'(g);
    end
'''
for signal,face,owner in [('dq_done',2,'WG+4'),('kq_done',0,'WG'),('xq_done',3,'WG+1'),('xq2_done',1,'WG+3')]:done+=f"    always @(posedge clk_local[{8+face}] or negedge rn)if(!rn){signal}<=0;else {signal}<=s2w_v&&s2w_p==4'({owner});\n"
s=s[:pos]+done+s[pos:]
# Response valid/data retained per logical owner, on the matching physical face.
a=s.index('    always @(posedge clk_local[11] or negedge rn)',s.index('    // R: correct'));s=s[:a]+'''    for(genvar g=0;g<RG;g=g+1)begin:g_face_response
        always @(posedge clk_local[8+R_FACE[g*2+:2]] or negedge rn)
            if(!rn)rr_v[g]<=0;else rr_v[g]<=d_v&&d_p==4'(g);
        always @(posedge clk_local[8+R_FACE[g*2+:2]])
            if(d_v&&d_p==4'(g))rr_d[g*256+:256]<=cor;
    end
    always @(posedge clk_local[10] or negedge rn)
        if(!rn)pr_v<=0;else pr_v<=(d_v&&d_p==4'(RG))||dw_v;
    always @(posedge clk_local[10])pr_d<=(d_v&&d_p==4'(RG))?{1'b0,d_tag,cor}:{1'b1,dw_tag,256'd0};
    always @(posedge clk_local[8] or negedge rn)
        if(!rn)begin ue<=0;status<=0;ce_v_q<=0;ce_n_q<=0;ue_q<=0;end
        else begin
            ce_v_q<=d_v;ce_n_q<=nce;ue_q<=d_v&&nue;
            if(ue_q)ue<=1;
            status<={flt,ue,ce};
        end
endmodule
`default_nettype wire
'''
assert 'd_syn[k*7 +: 7] <= sk;' in s and 'ot_vms_ce_counter_pipe ce_pipe' in s and s.count('endmodule')==1
(D/'ot_vms_bank_static_face_roots.sv').write_text(s)
clocks=['clk_in_n','clk_in_e','clk_in_s','clk_in_w','clk_ctrl','clk_s1','clk_s2','clk_ecc','clk_out_n','clk_out_e','clk_out_s','clk_out_w']
slots=json.loads((R/'results/arch/hbm_die_v15/vm_native_local_grants_1016.json').read_text())['slots'];maps=[]
for q,slot in enumerate(slots):
 face={p['name'].split('[')[0]: 'NESW'.index(p['face']) for p in slot['pins']}
 rg=4 if q==1 else 5;wg=2 if q<2 else 3
 rf=sum(face[f'rq{i}']<<(2*i) for i in range(rg));wf=sum(face[f'wq{i}']<<(2*i) for i in range(wg))
 text=(D/'physical'/f'hfd_vms_bank_local_q{q}.sv').read_text().replace(f'hfd_vms_bank_local_q{q}',f'hfd_vms_bank_face_q{q}')
 text=text.replace('clk_pin,clk_ctrl,clk_s1,clk_s2,clk_ecc,clk_out,clk_ma,clk_mb,clk_mc',','.join(clocks+['clk_ma','clk_mb','clk_mc']))
 text=text.replace('ot_vms_bank_static_local_roots','ot_vms_bank_static_face_roots')
 text=text.replace(f'.WG({wg})',f'.WG({wg}),.R_FACE({rg*2}\'h{rf:x}),.W_FACE({wg*2}\'h{wf:x})')
 assert '.R_FACE(' in text
 text=text.replace('.clk_local({clk_out,clk_ecc,clk_s2,clk_s1,clk_ctrl,clk_pin})','.clk_local({'+','.join(reversed(clocks))+'})')
 (D/'physical'/f'hfd_vms_bank_face_q{q}.sv').write_text(text)
 maps.append(dict(q=q,RG=rg,WG=wg,read_faces=[face[f'rq{i}'] for i in range(rg)],write_faces=[face[f'wq{i}'] for i in range(wg)]))
t=(D/'ot_vms_bank_local_physical.sv').read_text().replace('ot_vms_bank_local_physical','ot_vms_bank_face_physical').replace('hfd_vms_bank_local_q','hfd_vms_bank_face_q').replace('input wire [5:0] clk_local','input wire [11:0] clk_local')
old='.clk_pin(clk_local[0]),.clk_ctrl(clk_local[1]),.clk_s1(clk_local[2]),.clk_s2(clk_local[3]),.clk_ecc(clk_local[4]),.clk_out(clk_local[5])'
assert t.count(old)==4
t=t.replace(old,','.join(f'.{c}(die_local[{i}])' for i,c in enumerate(clocks)))
t=t.replace('MUT!=5)', 'MUT!=5&&(MUT<6||MUT>17))')
t=t.replace(' generate',' wire[11:0]die_local=MUT>=6&&MUT<=17&&bid==7?(clk_local&~(12\'d1<<(MUT-6))):clk_local;\n generate',1)
(D/'ot_vms_bank_face_physical.sv').write_text(t)
b=(D/'native_abi_1016/tb_hbm_vm_local_literal.sv').read_text().replace('tb_hbm_vm_local_literal','tb_hbm_vm_face_literal').replace('ot_vms_bank_local_physical','ot_vms_bank_face_physical').replace('{6{clk}}','{12{clk}}')
(D/'native_abi_1016/tb_hbm_vm_face_literal.sv').write_text(b)
b=(D/'native_abi_1016/run_local_literal.sh').read_text().replace('local_literal','face_literal').replace('local_roots.sv','face_roots.sv').replace('local_physical.sv','face_physical.sv').replace('hfd_vms_bank_local_q','hfd_vms_bank_face_q').replace('0 1 3 4 5;','0 1 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17;').replace("echo 'VM_LOCAL_LITERAL_ALL_PASS 4 actual shapes x8 banks x24SRAMs; read permutation/bank identity/slice identity mutants rejected'",'''echo "VM_FACE_LITERAL_ALL_PASS selected_sid=$ONLY_SID actual8banks24SRAMs; permutation/identity/3macro+12localclockdrop mutants rejected"''')
p=D/'native_abi_1016/run_face_literal.sh';p.write_text(b);p.chmod(0o755)
manifest=dict(schema='opentallas.vm_face_roots_source.v1',roots=clocks+['clk_ma','clk_mb','clk_mc'],map_legend='0N1E2S3W',quadrants=maps,normal_data_edges_added=0,capture_write_edges=3,response_read_edges=6,source_scope='Additive candidate, stableS unchanged; no physical views or native claims.',macro_floorplan_proposal={'outline_um':[270,313.2],'macros':'3actual174.744x70.488 SRAMs with20um vertical channels; phase/legalisation must be exact before kit'},files={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [D/'ot_vms_bank_static_face_roots.sv',D/'ot_vms_bank_face_physical.sv']+list((D/'physical').glob('hfd_vms_bank_face_q*.sv'))})
(D/'native_abi_1016/face_roots_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
