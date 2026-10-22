from pathlib import Path
import hashlib,json,difflib
p=Path('rtl/qwen_sys/host_20261013/qkd_host_native_engine.sv');old=p.read_text()
assert hashlib.sha256(old.encode()).hexdigest()=='b49162d88eb2f47e1dfee5c9036ac08a20ffe9b0796b70a89bb3cb2f0d5d1d63'
s=old.replace('    parameter integer APIPE  = 0,','    parameter integer APIPE  = 0,\n    // Owner-selected six-slot stream architecture; explicit new temporal ABI.\n    parameter integer SPIPE6 = 0,')
s=s.replace('    wire [31:0] u_raddr = (APIPE != 0) ? ap_raddr : s_raddr;', '    wire sp_constants_ok, sp_empty, sp_pending, sp_rdy0, sp_drain_edge;\n    wire [31:0] u_raddr = (SPIPE6 != 0) ? s_raddr : ((APIPE != 0) ? ap_raddr : s_raddr);')
s=s.replace('    wire [31:0] u_kcode = (APIPE != 0) ? ap_kcode : k_code;', '    wire [31:0] u_kcode = (SPIPE6 != 0) ? k_code : ((APIPE != 0) ? ap_kcode : k_code);')
s=s.replace('    wire [31:0] u_kscal = (APIPE != 0) ? ap_kscal : k_scal;', '    wire [31:0] u_kscal = (SPIPE6 != 0) ? k_scal : ((APIPE != 0) ? ap_kscal : k_scal);')
s=s.replace('    wire        u_mine  = (APIPE != 0) ? ap_mine  : s_mine;', '    wire        u_mine  = (SPIPE6 != 0) ? s_mine : ((APIPE != 0) ? ap_mine : s_mine);')
s=s.replace('    wire        ap_go   = (APIPE == 0) || ap_ok || st_mode == M_RAW;', '    wire        ap_go   = (SPIPE6 != 0) ? sp_constants_ok : ((APIPE == 0) || ap_ok || st_mode == M_RAW);')
s=s.replace('    wire st_go = st_adv && (!st_wv || w_rdy);', '    wire st_go = st_adv && ((SPIPE6 != 0) ? sp_rdy0 : (!st_wv || w_rdy));')
block='''
    // Six ordered elastic operation slots, P0..P5. No payload reset or mask.
    // A no-write token preserves source progress/order without consuming a credit.
    // Only selected AW32/K2/QPIPE2 production shape is proposed in this lane.
    generate if (SPIPE6 != 0 && (AW != 32 || APIPE != 0 || HDMAX != 128 || KVHMAX != 2 || QKV != 1 || QPIPE != 2 || NATIVE_ROWS != 1 || QMUT != 0)) begin : g_bad_spipe6
        QKD_SPIPE6_UNREVIEWED_PARAMETER_SHAPE refuse();
    end endgenerate
    function automatic [16:0] sp_add16(input [15:0] a,b,input ci);
        reg [15:0] g[0:4],p[0:4]; reg [16:0] z; integer l,i;
        begin
            g[0]=a&b; p[0]=a^b;
            for(l=0;l<4;l=l+1) for(i=0;i<16;i=i+1)
                if(i>=(1<<l)) begin
                    g[l+1][i]=g[l][i]|(p[l][i]&g[l][i-(1<<l)]);
                    p[l+1][i]=p[l][i]&p[l][i-(1<<l)];
                end else begin g[l+1][i]=g[l][i];p[l+1][i]=p[l][i];end
            z[0]=p[0][0]^ci;
            for(i=1;i<16;i=i+1)z[i]=p[0][i]^(g[4][i-1]|(p[4][i-1]&ci));
            z[16]=g[4][15]|(p[4][15]&ci); sp_add16=z;
        end
    endfunction
    function automatic [159:0] sp_reduce10(input [319:0] x);
        reg [31:0] a[0:9],b[0:6],c[0:4];integer i;
        begin
            for(i=0;i<10;i=i+1)a[i]=x[i*32+:32];
            for(i=0;i<3;i=i+1)begin
                b[2*i]=a[3*i]^a[3*i+1]^a[3*i+2];
                b[2*i+1]=((a[3*i]&a[3*i+1])|(a[3*i]&a[3*i+2])|(a[3*i+1]&a[3*i+2]))<<1;
            end
            b[6]=a[9];
            for(i=0;i<2;i=i+1)begin
                c[2*i]=b[3*i]^b[3*i+1]^b[3*i+2];
                c[2*i+1]=((b[3*i]&b[3*i+1])|(b[3*i]&b[3*i+2])|(b[3*i+1]&b[3*i+2]))<<1;
            end
            c[4]=b[6];sp_reduce10={c[4],c[3],c[2],c[1],c[0]};
        end
    endfunction
    function automatic [63:0] sp_reduce5(input [159:0] x);
        reg [31:0] a[0:4],b[0:3],c[0:2],z0,z1;integer i;
        begin
            for(i=0;i<5;i=i+1)a[i]=x[i*32+:32];
            b[0]=a[0]^a[1]^a[2];b[1]=((a[0]&a[1])|(a[0]&a[2])|(a[1]&a[2]))<<1;b[2]=a[3];b[3]=a[4];
            c[0]=b[0]^b[1]^b[2];c[1]=((b[0]&b[1])|(b[0]&b[2])|(b[1]&b[2]))<<1;c[2]=b[3];
            z0=c[0]^c[1]^c[2];z1=((c[0]&c[1])|(c[0]&c[2])|(c[1]&c[2]))<<1;
            sp_reduce5={z1,z0};
        end
    endfunction
    reg [5:0] sp_v;
    wire [5:0] sp_ready;
    reg [1:0] sp_prep;
    reg sp_const_valid;
    reg [16:0] sp_ring_lo;
    reg [31:0] sp_ring_mask;
    reg sp_ring_nz,sp_ring_poison;
    reg [2:0] sp_ns_mask;
    wire [16:0] sp_ring_hi=sp_add16(st_d[143:128],16'hffff,sp_ring_lo[16]);
    assign sp_constants_ok=sp_const_valid;
    assign sp_empty=!(|sp_v);
    reg sp_done_pending;
    assign sp_pending=sp_done_pending;
    reg [255:0] sp_data[0:5];
    reg [5:0] sp_write;
    reg [3:0] sp_poison;
    // P0 snapshot (151 address bits), plus payload/write/whole-arithmetic witness.
    reg [31:0] sp_base0,sp_stride0,sp_mask0,sp_row0;
    reg sp_rnz0;
    reg [4:0] sp_pitch0,sp_sec0;
    reg [1:0] sp_ldie0,sp_lns0,sp_mode0;
    reg [2:0] sp_nsm0,sp_ph0;
    // P1/P2 carry-save state; P3 registered low carry; P4/P5 complete address.
    reg [159:0] sp_sum1;
    reg [63:0] sp_sum2;
    reg [15:0] sp_low3,sp_hx3,sp_hy3;
    reg sp_carry3;
    reg [31:0] sp_addr4,sp_addr5;
    wire [16:0] sp_low_result=sp_add16(sp_sum2[15:0],sp_sum2[47:32],1'b0);
    wire [16:0] sp_high_result=sp_add16(sp_hx3,sp_hy3,sp_carry3);
    assign sp_ready[5]=!sp_v[5]||!sp_write[5]||w_rdy;
    for(genvar sj=0;sj<5;sj=sj+1)begin : g_sp_ready
        assign sp_ready[sj]=!sp_v[sj]||sp_ready[sj+1];
    end
    assign sp_rdy0=sp_ready[0];
    // Used only while st_pad blocks new issues; includes same-edge final retire.
    assign sp_drain_edge=!(|sp_v[4:0])&&(!sp_v[5]||sp_ready[5]);
    wire [31:0] sp_gd1=(sp_row0>>4)>>sp_ldie0;
    wire [31:0] sp_gs1=sp_gd1>>sp_lns0;
    wire [2:0] sp_stk1=sp_gd1[2:0]&sp_nsm0;
    wire [31:0] sp_local1=sp_rnz0?(sp_row0&sp_mask0):((sp_gs1<<4)|(sp_row0&32'd15));
    wire [31:0] sp_sb1=sp_gs1>>6;
    wire [4:0] sp_qgroup1=5'd1+{1'b0,sp_gs1[5:2]};
    reg [31:0] sp_terms[0:9];integer si;
    always @* begin
        for(si=0;si<10;si=si+1)sp_terms[si]=32'd0;
        case(sp_mode0)
            M_RAW:begin sp_terms[0]=sp_base0;sp_terms[1]=sp_row0;end
            M_ROWS:begin
                sp_terms[0]=sp_base0;
                for(si=0;si<3;si=si+1)sp_terms[1+si]=sp_rnz0?32'd0:((sp_stride0<<si)&{32{sp_stk1[si]}});
                for(si=0;si<5;si=si+1)sp_terms[4+si]=(sp_local1<<si)&{32{sp_pitch0[si]}};
                sp_terms[9]={27'd0,sp_sec0};
            end
            M_IKEY:begin
                sp_terms[0]=sp_base0;
                for(si=0;si<3;si=si+1)sp_terms[1+si]=sp_rnz0?32'd0:((sp_stride0<<si)&{32{sp_stk1[si]}});
                sp_terms[4]=sp_sb1<<11;sp_terms[5]=sp_sb1<<7;
                if(sp_ph0<3'd2)begin
                    sp_terms[6]={27'd0,sp_qgroup1}<<7;
                    sp_terms[7]={30'd0,sp_gs1[1:0]}<<5;
                    sp_terms[8]=(sp_row0&32'd15)<<1;sp_terms[9]={29'd0,sp_ph0};
                end else if(sp_ph0==3'd2)begin
                    for(si=0;si<10;si=si+1)sp_terms[si]=32'd0;
                end else begin
                    sp_terms[6]={26'd0,sp_gs1[5:0]}<<1;
                    sp_terms[7]=(sp_ph0==3'd4)?32'd1:32'd0;
                end
            end
            default:begin end
        endcase
    end
    wire [319:0] sp_terms_flat={sp_terms[9],sp_terms[8],sp_terms[7],sp_terms[6],sp_terms[5],sp_terms[4],sp_terms[3],sp_terms[2],sp_terms[1],sp_terms[0]};
    integer sv;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin sp_v<=0;sp_prep<=0;sp_const_valid<=0;end
        else if(SPIPE6!=0)begin
            if(s_disp)begin sp_prep<=1;sp_const_valid<=0;end
            else if(sp_prep==1)sp_prep<=2;
            else if(sp_prep==2)begin sp_prep<=0;sp_const_valid<=1;end
            else if(!st_act)sp_const_valid<=0;
            if(sp_ready[0])sp_v[0]<=st_go;
            for(sv=1;sv<6;sv=sv+1)if(sp_ready[sv])sp_v[sv]<=sp_v[sv-1];
        end
    end
    integer sdj;
    always @(posedge clk)if(SPIPE6!=0)begin
        if(sp_prep==1)begin
            sp_ring_lo<=sp_add16(st_d[127:112],16'hffff,1'b0);
            sp_ring_nz<=(st_d[143:112]!=0);
            sp_ring_poison<=(^st_d[143:112])^(^st_d[143:112]);
            sp_ns_mask<=(3'd1<<st_d[233:232])-3'd1;
        end
        if(sp_prep==2)sp_ring_mask<={sp_ring_hi[15:0],sp_ring_lo[15:0]}^{32{sp_ring_poison}};
        if(st_go)begin
            sp_base0<=st_d[47:16];sp_stride0<=st_d[79:48];sp_mask0<=sp_ring_mask;sp_row0<=st_row;
            sp_rnz0<=sp_ring_nz;sp_pitch0<=s_pitch;sp_sec0<=st_sec;sp_ldie0<=s_ldie;sp_lns0<=s_lns;
            sp_mode0<=st_mode;sp_nsm0<=sp_ns_mask;sp_ph0<=st_ph;sp_data[0]<=st_wd;sp_write[0]<=st_wv;
            // Exact original arithmetic alternative, BEFORE global QKV/outputmux.
            sp_poison[0]<=(^st_wa)^(^st_wa);
        end
        for(sdj=1;sdj<6;sdj=sdj+1)if(sp_ready[sdj]&&sp_v[sdj-1])begin
            sp_data[sdj]<=sp_data[sdj-1];sp_write[sdj]<=sp_write[sdj-1];
        end
        for(sdj=1;sdj<4;sdj=sdj+1)if(sp_ready[sdj]&&sp_v[sdj-1])sp_poison[sdj]<=sp_poison[sdj-1];
        if(sp_ready[1]&&sp_v[0])sp_sum1<=sp_reduce10(sp_terms_flat);
        if(sp_ready[2]&&sp_v[1])sp_sum2<=sp_reduce5(sp_sum1);
        if(sp_ready[3]&&sp_v[2])begin
            sp_low3<=sp_low_result[15:0];sp_carry3<=sp_low_result[16];sp_hx3<=sp_sum2[31:16];sp_hy3<=sp_sum2[63:48];
        end
        if(sp_ready[4]&&sp_v[3])sp_addr4<={sp_high_result[15:0],sp_low3}^{32{sp_poison[3]}};
        if(sp_ready[5]&&sp_v[4])sp_addr5<=sp_addr4;
    end
'''
needle='    // ROWS: the row ends with its last output sector';s=s.replace(needle,block+'\n'+needle)
s=s.replace('    assign w_v    = qk_wv || st_wv;', '    wire sp_external_v=sp_v[5]&&sp_write[5];\n    assign w_v    = qk_wv || ((SPIPE6!=0)?sp_external_v:st_wv);')
s=s.replace(' : st_wa;', ' : ((SPIPE6!=0)?sp_addr5:st_wa);')
s=s.replace(' : st_wd;', ' : ((SPIPE6!=0)?sp_data[5]:st_wd);')
s=s.replace('assign done_v = (APIPE >= 2) ? done_q : done_r; assign done_tag = (APIPE >= 2) ? dtag_q : dtag_r;', 'assign done_v = (SPIPE6==0 && APIPE >= 2) ? done_q : done_r; assign done_tag = (SPIPE6==0 && APIPE >= 2) ? dtag_q : dtag_r;')
s=s.replace(' || qp_busy;', ' || qp_busy || ((SPIPE6!=0)&&(!sp_empty||sp_pending));')
s=s.replace('&& !((QPIPE != 0) && s_fill[nslot]);','&& !((QPIPE != 0) && s_fill[nslot]) && (SPIPE6==0 || (sp_empty&&!sp_pending));')
s=s.replace('&& s_pre == 2\'b00 && !qp_busy;', '&& s_pre == 2\'b00 && !qp_busy && (SPIPE6==0 || (sp_empty&&!sp_pending));')
s=s.replace('done_r <= 1\'b0; dtag_r <= 0; nsec_r <= 0; n_beats <= 0;', 'done_r <= 1\'b0; dtag_r <= 0; nsec_r <= 0; n_beats <= 0; sp_done_pending<=0;')
s=s.replace('            done_r <= 1\'b0;\n', '            done_r <= 1\'b0;\n            if(SPIPE6!=0 && sp_done_pending)begin\n                sp_done_pending<=0;\n                if(st_d[7])begin done_r<=1;dtag_r<=st_d[15:8];end\n            end\n',1)
s=s.replace('if ((APIPE >= 2) ? wf_q : w_fire)', 'if ((SPIPE6==0 && APIPE >= 2) ? wf_q : w_fire)')
s=s.replace('if (st_beats == 0 || (pad_take && st_beats == 16\'d1)) begin','if ((st_beats == 0 || (pad_take && st_beats == 16\'d1)) && (SPIPE6==0 || sp_drain_edge)) begin')
s=s.replace('                    if (st_d[7]) begin done_r <= 1\'b1; dtag_r <= st_d[15:8]; end','                    if(SPIPE6!=0)sp_done_pending<=1;\n                    else if (st_d[7]) begin done_r <= 1\'b1; dtag_r <= st_d[15:8]; end')
p.write_text(s)
r=Path('results/arch/hroot_registered_stream_1021');r.mkdir(parents=True,exist_ok=True)
(r/'source.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='539e8df61/b491/source',tofile='SPIPE6 source-only candidate')))
(r/'source_binding.json').write_text(json.dumps({'base_commit':'539e8df61','base_sha256':hashlib.sha256(old.encode()).hexdigest(),'candidate_sha256':hashlib.sha256(s.encode()).hexdigest(),'parameters':{'AW':32,'HDMAX':128,'KVHMAX':2,'QKV':1,'APIPE':0,'SPIPE6':1,'QPIPE':2,'NATIVE_ROWS':1,'QMUT':0},'scope':'selected source/model implementation only; NO compile/simulation/map/native/cold/gate yet'},indent=2)+'\n')
