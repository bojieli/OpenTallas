// Generated AHUB6 private partial controls; native census and behavioral qualification mandatory.
module qkd_ahub6_static_io_safe #(
    parameter [63:0] AP_OFS = {4{16'd2}},
    parameter integer FR_OFS = 0,
    parameter integer WF_RLY = 0,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input wire [3:0] rst_group,
    // attention root word (kvs_attn attn_root {start_qk, ep, layer, ctx, cal[127:16], cal[175:160]})
    input  wire          hs_start,
    input  wire [15:0]   hs_ep,
    input  wire [5:0]    hs_layer,
    input  wire [13:0]   hs_ctx,
    input  wire [111:0]  hs_cal_lo,           // cal[127:16]: LMAX_START, Z_START, HUB_LMAX, HUB_Z, HUB_RECIP, HUB_PUB, PV_START
    input  wire [15:0]   hs_cal_r,            // cal[175:160]: R
    // to the hub
    output wire          start,
    output wire [31:0] start_all,
    output reg  [15:0]   epoch,
    output reg  [5:0]    layer,
    output reg  [13:0]   T,
    output wire [191:0]  hub_cal,             // {RZ_PUBLISH, RECIP_ISSUE, Z_START, LMAX_ISSUE, Z_IN x4, LMAX_IN x4}
    output reg  [63:0]   si_epoch,
    output reg  [23:0]   si_layer,
    // from the hub
    input  wire          rz_publish,
    input  wire [15:0]   rz_epoch,
    input  wire [127:0]  rz_vector,
    input  wire          hub_fault,
    // export to pvfin.fr and the die hub fault
    output reg           fr_valid,
    output reg  [15:0]   fr_epoch,
    output reg  [127:0]  fr_rz,
    output reg           fault
);
    wire rst_n = rst_group[0];
    assign start = start_all[0];
    // KV-AHUBDW 10-18 (pin rule: flop-first pins): every hs bit lands in a pin flop first (cal_q / cal_r_q beside start /
    // epoch / layer / T); the calendar adds (constant AP_OFS) and the export target are computed from the pin flops in the
    // same cycle start is high, so the hub still samples hub_cal on start (no added edge, behaviour unchanged).
    reg  [111:0] cal_q;  reg [15:0] cal_r_q;
    always @(posedge ck) begin cal_q <= hs_cal_lo; cal_r_q <= hs_cal_r; end
    wire [15:0] c_lmax = cal_q[15:0],  c_z = cal_q[31:16],  c_hl = cal_q[47:32], c_hz = cal_q[63:48];
    wire [15:0] c_hr = cal_q[79:64],   c_hp = cal_q[95:80], c_pv = cal_q[111:96];
    reg  [191:0] cal_n;
    integer s_;
    always @* begin
        cal_n = {c_hp, c_hr, c_hz, c_hl, 128'd0};
        for (s_ = 0; s_ < 4; s_ = s_ + 1) begin
            cal_n[16*s_ +: 16]      = c_lmax + AP_OFS[16*s_ +: 16];
            cal_n[64 + 16*s_ +: 16] = c_z + AP_OFS[16*s_ +: 16];
        end
    end
    // export target from the same command's PV_START + R (17-bit + sign: never wraps into a reachable age)
    // KV-AHUB7 10-19 (COORD 17:00): the export leaves WF_RLY registered relay edges before the W-face pins, so u_io emits
    // WF_RLY edges earlier; FR_OFS keeps its die meaning (fr still lands on pvfin's R slot, no die re-binding).
    wire signed [18:0] tgt_n = $signed({3'd0, c_pv}) + $signed({3'd0, cal_r_q}) + FR_OFS - WF_RLY + ((MUT == 1) ? 1 : 0);
    // pin stage (every input registered; start / held words ride together, so the hub samples one coherent command)
    for(genvar c=0;c<32;c=c+1) begin:g_start_copy
        ot_ahub6_async_copy #(.ID(c)) u_ff(.ck(ck),.rn(rst_group[c/8]),.d(hs_start),.q(start_all[c]));
    end
    // KV-AHUBDW2 10-18: T is HELD with the command (captured with hs_start, as the core holds epoch / layer) so the core
    // can register nblk(T) and its calendar decodes one edge ahead (qkd_ahub6_static_core_la_safe).
    // T_p is the pin flop; T_h holds the start cycle's T; T = start ? T_p : T_h (flops first, then the mux).
    reg  [13:0] T_p, T_h;
    always @(posedge ck) begin
        epoch <= hs_ep; layer <= hs_layer; T_p <= hs_ctx;
        if (start_all[1]) T_h <= T_p;
    end
    always @* T = start_all[2] ? T_p : T_h;
    assign hub_cal = cal_n;
    reg signed [18:0] tgt_q;
    always @(posedge ck) begin
        if(start_all[3]) tgt_q[9:0] <= tgt_n[9:0];
        if(start_all[4]) tgt_q[18:10] <= tgt_n[18:10];
    end
    // held si identity (the native service's held_epoch / held_layer, captured on start)
    for(genvar c=0;c<4;c=c+1) begin:g_identity
        always @(posedge ck) if(start_all[5+c]) si_epoch[16*c+:16] <= epoch;
        always @(posedge ck) if(start_all[9+c/2]) si_layer[6*c+:6] <= layer;
    end
    // ---- reciprocal export: one registered word at io age tgt ---------------------------------------------------------
    reg         active, published, xf;
    reg  [15:0] age;
    reg  [15:0] prev_ep;
    wire [16:0] age_nx = start_all[11] ? 17'd1 : {1'b0, age} + 17'd1;     // io age of the NEXT cycle
    // KV-AHUBDW2 10-18 (route a1: u_io.cal_r_q -> PV_START + R adder -> age compare -> 145 export enables at the W face,
    // -412 ps): the export edge is decided ONE EDGE AHEAD into em_q from the latched target tgt_q (a 19-bit equality of
    // flops), so the export flops' enable is one flop.  Same export edge as before for every meetable slot; a slot < 3
    // (export on the start edge or the one after, never a compiled slot: PV_START + R is hundreds of cycles) is now an
    // unmeetable-slot fault, and a start on a pending export edge (the next command colliding with the export) faults.
    reg         em_q;
    wire        emit   = em_q;
    // KV-AHUBDW2 a2e 10-18 (gate a2d: u_io.em_q (397,531) -> W-face fr_rz / fr_epoch export flops -11.1 ps, 16 levels over
    // ~660 um): em_w is a kept copy of em_q (same D, same reset) that drives only the W-face export (fr_valid, fr_rz,
    // fr_epoch, prev_ep), so it places beside the fr flops and em_q keeps the local io bookkeeping.  Same edges.
    wire [19:0] em_w_copy;
    wire em_w = em_w_copy[0];
    for(genvar c=0;c<20;c=c+1) begin:g_export_copy
        ot_ahub6_async_copy #(.ID(64+c)) u_ff(.ck(ck),.rn(rst_group[1+c/8]),.d(em_d),.q(em_w_copy[c]));
    end
    wire        bad_t  = start_all[11] && (tgt_n < 19'sd3 || tgt_n > 19'sd65535);
    wire        em_d   = !start && active && !em_q && ($signed({3'b0, 16'(age + 16'd1)}) + 19'sd1 == tgt_q);
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin active <= 1'b0; published <= 1'b0; fr_valid <= 1'b0; xf <= 1'b0; em_q <= 1'b0; end
        else begin
            fr_valid <= em_w;
            em_q <= em_d;
            if (start) begin active <= !bad_t; published <= 1'b0; xf <= bad_t || em_q; end
            else begin
                if (active && rz_publish) published <= 1'b1;
                if (rz_publish && !active) xf <= 1'b1;                           // a publication outside any pass
                if (emit) active <= 1'b0;                                          // once per pass
            end
            if (emit && !published) xf <= 1'b1;                                   // rz late: export before publication
            if (active && age_nx[16]) xf <= 1'b1;                                  // slot beyond the age range
        end
    end
    wire [127:0] export_rz = (MUT == 2) ? {rz_vector[127:64], rz_vector[31:0], rz_vector[63:32]} : rz_vector;
    wire [15:0] export_epoch = (MUT == 3) ? prev_ep : rz_epoch;
    for(genvar c=0;c<16;c=c+1) begin:g_export_data
        always @(posedge ck) if(em_w_copy[c]) fr_rz[8*c+:8] <= export_rz[8*c+:8];
    end
    for(genvar c=0;c<2;c=c+1) begin:g_export_epoch
        always @(posedge ck) if(em_w_copy[16+c]) fr_epoch[8*c+:8] <= export_epoch[8*c+:8];
        always @(posedge ck) if(em_w_copy[18+c]) prev_ep[8*c+:8] <= rz_epoch[8*c+:8];
    end
    for(genvar c=0;c<2;c=c+1) begin:g_age
        always @(posedge ck or negedge rst_group[c])
            if(!rst_group[c]) age[8*c+:8]<=0;
            else if(start_all[30+c]) age[8*c+:8]<=(c==0)?8'd1:8'd0;
            else if(active) age[8*c+:8]<=age_nx[8*c+:8];
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0; else fault <= xf || hub_fault;
endmodule

module qkd_ahub6_static_dec_safe #(
    parameter integer Z_IN_STRIDE=16,
    parameter integer Z_LEVEL_GAP=10, GROUP=-1
)(
    input wire [16:0] edge_age,
    input wire active,
    input wire [63:0] LMAX_IN_AGE,Z_IN_AGE,
    input wire [15:0] LMAX_ISSUE_AGE,Z_START_AGE,RECIP_ISSUE_AGE,RECIP_RETURN_AGE,RZ_PUBLISH_AGE,
    input wire [19:0] nblk_v,
    output reg [3:0] lm_slot,z_slot,done_slot,
    output reg [7:0] slot_h,
    output reg [15:0] slot_k,
    output wire m_issue,
    output wire [1:0] mh,
    output reg [3:0] issue,
    output reg [5:0] pair_base,
    output wire recip_issue,recip_return,
    output wire [1:0] recip_head,return_head,
    output wire pub_hit
);
    // KV-AHUBDW3 a3 10-18 (route a2 b698f22ab TT -55.2 / -26.5): every window is decoded from ONE subtraction
    // d = edge_age - START (17 b) compared against constants / nblk, not START + width added and compared (two carry
    // chains).  Exact: for d >= 0, edge_age < START + c <=> d < c; edge_age < Z + 16 n <=> d / 16 < n; edge_age == Z + 16 n
    // <=> d % 16 == 0 && d / 16 == n; (edge_age - Z) % 16 = d % 16; 2'(edge_age - X) = d[1:0].  The Z-tree issue levels
    // l = 1..6 start at Z_START_AGE + B_l with B_l elaboration constants (B_1 = 0, B_l+1 = B_l + burst_l + Z_LEVEL_GAP).
    wire [4:0] nblk[0:3];
    for(genvar s=0;s<4;s=s+1)assign nblk[s]=nblk_v[5*s+:5];
    wire [17:0] dl[0:3], dz[0:3];
    for(genvar s=0;s<4;s=s+1)begin:g_d
        assign dl[s]={1'b0,edge_age}-{2'b0,LMAX_IN_AGE[16*s+:16]};
        assign dz[s]={1'b0,edge_age}-{2'b0,Z_IN_AGE[16*s+:16]};
    end
    wire [17:0] dmi={1'b0,edge_age}-{2'b0,LMAX_ISSUE_AGE}, dzs={1'b0,edge_age}-{2'b0,Z_START_AGE},
                dri={1'b0,edge_age}-{2'b0,RECIP_ISSUE_AGE}, drr={1'b0,edge_age}-{2'b0,RECIP_RETURN_AGE};
    integer base,np,burst;
    always @* begin
        lm_slot=0;z_slot=0;done_slot=0;slot_h=0;slot_k=0;
        for(integer s=0;s<4;s=s+1)begin
          if(GROUP<0 || GROUP==s)begin
            if(active && !dl[s][17] && dl[s][16:0]<4)begin
                lm_slot[s]=1;slot_h[2*s+:2]=dl[s][1:0];
            end
            if(active && !dz[s][17] && (dz[s][16:0]/Z_IN_STRIDE)<nblk[s])begin
                if(dz[s][16:0]%Z_IN_STRIDE<4)begin
                    z_slot[s]=1;slot_h[2*s+:2]=2'(dz[s][16:0]%Z_IN_STRIDE);
                    slot_k[4*s+:4]=4'(dz[s][16:0]/Z_IN_STRIDE);
                end
            end
            done_slot[s]=active && !dz[s][17] && dz[s][16:0]%Z_IN_STRIDE==0 && (dz[s][16:0]/Z_IN_STRIDE)==nblk[s];
          end
        end
    end
    assign m_issue=(GROUP<0 || GROUP==4) && active && !dmi[17] && dmi[16:0]<4;
    assign mh=(GROUP<0 || GROUP==4)?dmi[1:0]:0;
    always @*begin
        issue=0;pair_base=0;base=0;
        for(integer l=1;l<=6;l=l+1)begin
            np=64>>l;burst=(np+3)/4;
            if((GROUP<0 || GROUP==5) && active && !dzs[17] && dzs[16:0]>=base && dzs[16:0]<base+burst)begin
                pair_base=6'((dzs[16:0]-base)*4);
                for(integer a=0;a<4;a=a+1)issue[a]=((dzs[16:0]-base)*4+a)<np;
            end
            base=base+burst+Z_LEVEL_GAP;
        end
    end
    assign recip_issue=(GROUP<0 || GROUP==6) && active && !dri[17] && dri[16:0]<4;
    assign recip_return=(GROUP<0 || GROUP==7) && active && !drr[17] && drr[16:0]<4;
    assign recip_head=(GROUP<0 || GROUP==6)?dri[1:0]:0;
    assign return_head=(GROUP<0 || GROUP==7)?drr[1:0]:0;
    assign pub_hit=(GROUP<0 || GROUP==8) && edge_age==RZ_PUBLISH_AGE;
endmodule

module qkd_ahub6_static_core_la_safe #(
    parameter integer Z_IN_STRIDE=16,
    parameter integer Z_LEVEL_GAP=10,
    parameter integer RS_RLY=0,                         // KV-AHUB7: per-tree relay stage on the reciprocal root select
    parameter integer Z_RT=0,                           // KV-AHUB3 10-19: edges added to the core->Z tree->core round trip (relays / landings)
    parameter integer MUT=0                             // 4 (bench negative control): decodes registered NOT ahead; 5: RS relay bypassed
)(
    input wire [207:0] cal,
    input wire clk,rst_n,start,active_layer_parity,
    input wire [31:0] start_all,
    input wire [15:0] request_epoch,input wire [5:0] active_layer,
    input wire [13:0] T,
    input wire [3:0] si_valid,si_g,si_any,input wire [63:0] si_epoch,input wire [23:0] si_layer,
    input wire [7:0] si_type,si_hh,
    input wire [15:0] si_k,
    input wire [127:0] si_data,
    output reg [143:0] am,
    output reg [3:0] zh_start,
    output reg [511:0] zh_we,zh_sid,
    output reg [15:0] zh_iv,
    output reg [3:0] zh_g,
    output reg [23:0] zh_p,
    input wire [255:0] zh_root,
    input wire [15:0] zh_err,
    output reg rc_v,
    output reg [31:0] rc_x,
    input wire [31:0] rc_y,
    input wire rc_vo,rc_fault,
    output reg rz_valid,
    output reg [1:0] rz_head,
    output reg [31:0] rz_data,
    output reg [15:0] rz_epoch,output reg rz_publish,
    output wire [127:0] rz4,
    output reg fault
);
    // KV-AHUB7 10-19 (gate a6 textbook.high_fanout: rn[1] 296 loads): region 4 carries zseen[2..3] (two ~150-load copies)
    wire [31:0] rn;
    ot_ahub6_reset_two #(.COPIES(32)) u_rr (.ck(clk),.d(rst_n),.q(rn));
    wire [8:0] active_decode;
    for(genvar c=0;c<9;c=c+1) begin:g_active_copy
        ot_ahub6_async_copy #(.ID(440+c)) u_ff(.ck(clk),.rn(rn[0]),.d(start_all[25] || active),.q(active_decode[c]));
    end
    reg active,parity;reg [15:0] epoch;reg [5:0] layer;
    wire [63:0] LMAX_IN_AGE,Z_IN_AGE;wire [15:0] LMAX_ISSUE_AGE,Z_START_AGE,RECIP_ISSUE_AGE,RECIP_RETURN_AGE,RZ_PUBLISH_AGE;
    wire [207:0] held_cal;
    assign {RZ_PUBLISH_AGE,RECIP_RETURN_AGE,RECIP_ISSUE_AGE,Z_START_AGE,LMAX_ISSUE_AGE,Z_IN_AGE,LMAX_IN_AGE}=held_cal;
    for(genvar c=0;c<13;c=c+1) begin:g_calendar
        reg [15:0] word_q;
        always @(posedge clk) if(start_all[12+c]) word_q <= cal[16*c+:16];
        assign held_cal[16*c+:16]=word_q;
    end
    wire [15:0] c_rzp,c_rra,c_ria,c_zsa,c_lis;wire [63:0] c_zin,c_lin;
    assign {c_rzp,c_rra,c_ria,c_zsa,c_lis,c_zin,c_lin}=cal;
    // nblk(T) registered from the held command T (u_io); zmask from it
    reg [19:0] nblk_q;
    always @(posedge clk)
        for(integer s=0;s<4;s=s+1)
            nblk_q[5*s+:5]<=(T>14'(128*s))?5'(((T-14'(128*s)-14'd1)>>9)+14'd1):5'd0;
    reg [63:0] zmask;
    always @*begin
        zmask=0;
        for(integer s=0;s<4;s=s+1)for(integer k=0;k<16;k=k+1)if(k<nblk_q[5*s+:5])zmask[4*k+s]=1'b1;
    end
    wire [15:0] age;
    wire [3:0] first_copy;
    wire first_q=first_copy[0];
    for(genvar c=0;c<4;c=c+1) begin:g_first_copy
        ot_ahub6_async_copy #(.ID(300+c),.INIT(1)) u_ff(.ck(clk),.rn(rn[0]),.d(start_all[25] || (first_q && !active)),.q(first_copy[c]));
    end                                        // == (age == 0): edge age 1 this cycle
    // KV-AHUBDW2 a2e 10-18 (gate a2d: u_core.first_q (396,517) -> W-side rz[1] -5 ps): first_r is a kept copy of first_q
    // (same D, same reset) selecting only recip_return / return_head, so it places beside the rz registers.  Same edges.
    (* keep *) reg first_r;
    // ---- decodes: registered look-ahead (dq, from the next edge age) or, on the first cycle, at edge age 1 (d1) ----
    wire [16:0] e_next=(MUT==4)?{1'b0,age}+17'd1:(active && age!=16'hffff)?{1'b0,age}+17'd2:{1'b0,age}+17'd1;
    wire [3:0] n_lm,n_z,n_dn,n_is,o_lm,o_z,o_dn,o_is;wire [7:0] n_sh,o_sh;wire [15:0] n_sk,o_sk;
    wire n_mi,n_ri,n_rr,n_pb,o_mi,o_ri,o_rr,o_pb;wire [1:0] n_mh,n_rh,n_th,o_mh,o_rh,o_th;wire [5:0] n_pa,o_pa;
    wire [16:0] decode_age[0:8];
    wire [3:0] dec_n_lm_slot[0:8];
    wire [3:0] dec_n_z_slot[0:8];
    wire [3:0] dec_n_done_slot[0:8];
    wire [7:0] dec_n_slot_h[0:8];
    wire [15:0] dec_n_slot_k[0:8];
    wire [0:0] dec_n_m_issue[0:8];
    wire [1:0] dec_n_mh[0:8];
    wire [3:0] dec_n_issue[0:8];
    wire [5:0] dec_n_pair_base[0:8];
    wire [0:0] dec_n_recip_issue[0:8];
    wire [0:0] dec_n_recip_return[0:8];
    wire [1:0] dec_n_recip_head[0:8];
    wire [1:0] dec_n_return_head[0:8];
    wire [0:0] dec_n_pub_hit[0:8];
    wire [3:0] dec_o_lm_slot[0:8];
    wire [3:0] dec_o_z_slot[0:8];
    wire [3:0] dec_o_done_slot[0:8];
    wire [7:0] dec_o_slot_h[0:8];
    wire [15:0] dec_o_slot_k[0:8];
    wire [0:0] dec_o_m_issue[0:8];
    wire [1:0] dec_o_mh[0:8];
    wire [3:0] dec_o_issue[0:8];
    wire [5:0] dec_o_pair_base[0:8];
    wire [0:0] dec_o_recip_issue[0:8];
    wire [0:0] dec_o_recip_return[0:8];
    wire [1:0] dec_o_recip_head[0:8];
    wire [1:0] dec_o_return_head[0:8];
    wire [0:0] dec_o_pub_hit[0:8];
    for(genvar dg=0;dg<9;dg=dg+1)begin:g_decode
        wire [15:0] local_age;
        if(dg<8)begin:g_age
            ot_ahub6_async_word #(.W(16),.ID(601+dg)) u_ff(.ck(clk),.rn(rn[24+dg]),.d(age_next),.q(local_age));
        end else begin:g_original assign local_age=age;end
        assign decode_age[dg]=(MUT==4)?{1'b0,local_age}+17'd1:(active_decode[dg] && local_age!=16'hffff)?{1'b0,local_age}+17'd2:{1'b0,local_age}+17'd1;

qkd_ahub6_static_dec_safe #(.Z_IN_STRIDE(Z_IN_STRIDE),.Z_LEVEL_GAP(Z_LEVEL_GAP),.GROUP(dg)) u_n(.edge_age(decode_age[dg]),.active(active_decode[dg]),.LMAX_IN_AGE(LMAX_IN_AGE),.Z_IN_AGE(Z_IN_AGE),.LMAX_ISSUE_AGE(LMAX_ISSUE_AGE),.Z_START_AGE(Z_START_AGE),.RECIP_ISSUE_AGE(RECIP_ISSUE_AGE),.RECIP_RETURN_AGE(RECIP_RETURN_AGE),.RZ_PUBLISH_AGE(RZ_PUBLISH_AGE),.nblk_v(nblk_q),.lm_slot(dec_n_lm_slot[dg]),.z_slot(dec_n_z_slot[dg]),.done_slot(dec_n_done_slot[dg]),.slot_h(dec_n_slot_h[dg]),.slot_k(dec_n_slot_k[dg]),.m_issue(dec_n_m_issue[dg]),.mh(dec_n_mh[dg]),.issue(dec_n_issue[dg]),.pair_base(dec_n_pair_base[dg]),.recip_issue(dec_n_recip_issue[dg]),.recip_return(dec_n_recip_return[dg]),.recip_head(dec_n_recip_head[dg]),.return_head(dec_n_return_head[dg]),.pub_hit(dec_n_pub_hit[dg]));
qkd_ahub6_static_dec_safe #(.Z_IN_STRIDE(Z_IN_STRIDE),.Z_LEVEL_GAP(Z_LEVEL_GAP),.GROUP(dg)) u_o(.edge_age(17'd1),.active(active_decode[dg]),.LMAX_IN_AGE(LMAX_IN_AGE),.Z_IN_AGE(Z_IN_AGE),.LMAX_ISSUE_AGE(LMAX_ISSUE_AGE),.Z_START_AGE(Z_START_AGE),.RECIP_ISSUE_AGE(RECIP_ISSUE_AGE),.RECIP_RETURN_AGE(RECIP_RETURN_AGE),.RZ_PUBLISH_AGE(RZ_PUBLISH_AGE),.nblk_v(nblk_q),.lm_slot(dec_o_lm_slot[dg]),.z_slot(dec_o_z_slot[dg]),.done_slot(dec_o_done_slot[dg]),.slot_h(dec_o_slot_h[dg]),.slot_k(dec_o_slot_k[dg]),.m_issue(dec_o_m_issue[dg]),.mh(dec_o_mh[dg]),.issue(dec_o_issue[dg]),.pair_base(dec_o_pair_base[dg]),.recip_issue(dec_o_recip_issue[dg]),.recip_return(dec_o_recip_return[dg]),.recip_head(dec_o_recip_head[dg]),.return_head(dec_o_return_head[dg]),.pub_hit(dec_o_pub_hit[dg]));
end
assign n_lm[0]=dec_n_lm_slot[0][0];
assign n_lm[1]=dec_n_lm_slot[1][1];
assign n_lm[2]=dec_n_lm_slot[2][2];
assign n_lm[3]=dec_n_lm_slot[3][3];
assign n_z[0]=dec_n_z_slot[0][0];
assign n_z[1]=dec_n_z_slot[1][1];
assign n_z[2]=dec_n_z_slot[2][2];
assign n_z[3]=dec_n_z_slot[3][3];
assign n_dn[0]=dec_n_done_slot[0][0];
assign n_dn[1]=dec_n_done_slot[1][1];
assign n_dn[2]=dec_n_done_slot[2][2];
assign n_dn[3]=dec_n_done_slot[3][3];
assign n_sh[0+:2]=dec_n_slot_h[0][0+:2];
assign n_sh[2+:2]=dec_n_slot_h[1][2+:2];
assign n_sh[4+:2]=dec_n_slot_h[2][4+:2];
assign n_sh[6+:2]=dec_n_slot_h[3][6+:2];
assign n_sk[0+:4]=dec_n_slot_k[0][0+:4];
assign n_sk[4+:4]=dec_n_slot_k[1][4+:4];
assign n_sk[8+:4]=dec_n_slot_k[2][8+:4];
assign n_sk[12+:4]=dec_n_slot_k[3][12+:4];
assign n_mi=dec_n_m_issue[4];
assign n_mh=dec_n_mh[4];
assign n_is=dec_n_issue[5];
assign n_pa=dec_n_pair_base[5];
assign n_ri=dec_n_recip_issue[6];
assign n_rr=dec_n_recip_return[7];
assign n_rh=dec_n_recip_head[6];
assign n_th=dec_n_return_head[7];
assign n_pb=dec_n_pub_hit[8];
assign o_lm[0]=dec_o_lm_slot[0][0];
assign o_lm[1]=dec_o_lm_slot[1][1];
assign o_lm[2]=dec_o_lm_slot[2][2];
assign o_lm[3]=dec_o_lm_slot[3][3];
assign o_z[0]=dec_o_z_slot[0][0];
assign o_z[1]=dec_o_z_slot[1][1];
assign o_z[2]=dec_o_z_slot[2][2];
assign o_z[3]=dec_o_z_slot[3][3];
assign o_dn[0]=dec_o_done_slot[0][0];
assign o_dn[1]=dec_o_done_slot[1][1];
assign o_dn[2]=dec_o_done_slot[2][2];
assign o_dn[3]=dec_o_done_slot[3][3];
assign o_sh[0+:2]=dec_o_slot_h[0][0+:2];
assign o_sh[2+:2]=dec_o_slot_h[1][2+:2];
assign o_sh[4+:2]=dec_o_slot_h[2][4+:2];
assign o_sh[6+:2]=dec_o_slot_h[3][6+:2];
assign o_sk[0+:4]=dec_o_slot_k[0][0+:4];
assign o_sk[4+:4]=dec_o_slot_k[1][4+:4];
assign o_sk[8+:4]=dec_o_slot_k[2][8+:4];
assign o_sk[12+:4]=dec_o_slot_k[3][12+:4];
assign o_mi=dec_o_m_issue[4];
assign o_mh=dec_o_mh[4];
assign o_is=dec_o_issue[5];
assign o_pa=dec_o_pair_base[5];
assign o_ri=dec_o_recip_issue[6];
assign o_rr=dec_o_recip_return[7];
assign o_rh=dec_o_recip_head[6];
assign o_th=dec_o_return_head[7];
assign o_pb=dec_o_pub_hit[8];
    reg [3:0] q_lm,q_z,q_dn,q_is;reg [7:0] q_sh;reg [15:0] q_sk;reg q_mi,q_ri,q_rr,q_pb;reg [1:0] q_mh,q_rh,q_th;
    reg [5:0] q_pa;
    always @(posedge clk)begin
        q_lm<=n_lm;q_z<=n_z;q_dn<=n_dn;q_sh<=n_sh;q_sk<=n_sk;q_mi<=n_mi;q_is<=n_is;q_pa<=n_pa;
        q_ri<=n_ri;q_rr<=n_rr;q_pb<=n_pb;
        // KV-AHUBDW3 a3: the three 2-bit heads that select wide muxes (mh: 16 lm words -> ma_x; recip_head: 4 roots ->
        // rc_x; return_head: rz[] / rz_head) are registered for EVERY cycle, the first one included: on a start_all[25] edge they
        // load the edge-age-1 head of the calendar being latched (2'(1 - X) of cal, exactly u_d1's head once X <= cal), so
        // no first_q mux and no calendar-register subtract sits in front of the 64-load selects (route a2: RECIP_ISSUE_AGE
        // -> u_d1 -> first_q mux -> 32 x 4:1 -> rc_x, TT -55.2 ps).  Same values on every edge as before.
        q_mh<=start_all[29]?2'(2'd1-c_lis[1:0]):n_mh;
        q_rh<=start_all[29]?2'(2'd1-c_ria[1:0]):n_rh;
        q_th<=start_all[29]?2'(2'd1-c_rra[1:0]):n_th;
    end
    // KV-AHUB6 10-19 (route a5 74c87116c TT -357.4: u_core.q_rh[0] -> 32 rc_x, 2 AO21 + ~650 ps of buffered wire: the
    // 2-bit head reached a 4:1 mux spread between the four Z trees): the reciprocal root select is a REGISTERED ONE-HOT,
    // one flop per Z tree (q_rs[a] == (q_rh == a), same D source, same edge), and rc_x is an AND-OR of the four roots, so
    // each select flop drives only its own tree's 32 AND gates.  Edge-exact (q_rs == 4'b1 << q_rh on every edge).
    (* keep *) reg [3:0] q_rs;
    always @(posedge clk) q_rs<=4'd1<<(start_all[29]?2'(2'd1-c_ria[1:0]):n_rh);
    wire [3:0] lm_slot=first_copy[1]?o_lm:q_lm, z_slot=first_copy[3]?o_z:q_z, done_slot=first_q?o_dn:q_dn, issue=first_q?o_is:q_is;
    wire [7:0] slot_h=first_copy[1]?o_sh:q_sh;
    wire [15:0] slot_k=first_copy[2]?o_sk:q_sk;
    wire m_issue=first_q?o_mi:q_mi, recip_issue=first_q?o_ri:q_ri, recip_return=first_r?o_rr:q_rr, pub_hit=first_q?o_pb:q_pb;
    wire [1:0] mh=q_mh, recip_head=q_rh, return_head=q_th;
    wire [5:0] pair_base=first_copy[3]?o_pa:q_pa;
    reg [3:0] lm_b,z_b,any_b;
    reg [7:0] hh_b;
    reg [15:0] k_b;
    reg [127:0] data_b;
    wire [19:0] start_b_copy;
    wire start_b = start_b_copy[0];
    for(genvar c=0;c<20;c=c+1) begin:g_start_b_copy
        ot_ahub6_async_copy #(.ID(128+c)) u_ff(.ck(clk),.rn(rn[7]),.d(start_all[26+c/5]),.q(start_b_copy[c]));
    end
    always @(posedge clk or negedge rn[0])
        if(!rn[0])begin active<=0;first_r<=1;lm_b<=0;z_b<=0;end
        else begin
            lm_b<=lm_slot;z_b<=z_slot;
            first_r<=start_all[25] || (first_r && !active);
            if(start_all[25])begin active<=1;lm_b<=0;z_b<=0;end

        end
    wire [15:0] age_next=start_all[26]?16'd0:(active && age!=16'hffff)?age+16'd1:age;
    ot_ahub6_async_word #(.W(16),.ID(600)) u_age(.ck(clk),.rn(rn[5]),.d(age_next),.q(age));
    always @(posedge clk or negedge rn[6])
        if(!rn[6])epoch[7:0]<=0;else if(start_all[27])epoch[7:0]<=request_epoch[7:0];
    always @(posedge clk or negedge rn[6])
        if(!rn[6])epoch[15:8]<=0;else if(start_all[31])epoch[15:8]<=request_epoch[15:8];
    always @(posedge clk or negedge rn[6])
        if(!rn[6])begin parity<=0;layer<=0;end
        else if(start_all[4])begin parity<=active_layer_parity;layer<=active_layer;end
    always @(posedge clk)begin any_b<=si_any;hh_b<=slot_h;k_b<=slot_k;data_b<=si_data;end
    wire [31:0] lm[0:15];
    reg [15:0] lany;
    reg [127:0] zseen[0:3];
    reg [15:0] lm_seen;
    reg [3:0] done_seen;
    always @(posedge clk or negedge rn[1])
        if(!rn[1]) lany<=0;
        else if(start_b_copy[0]) lany<=0;
        else for(integer a=0;a<4;a=a+1) if(lm_b[a]) lany[4*a+hh_b[2*a+:2]]<=any_b[a];
    always @(posedge clk or negedge rn[2])
        if(!rn[2]) lm_seen<=0;
        else if(start_b_copy[1]) lm_seen<=0;
        else for(integer a=0;a<4;a=a+1) if(lm_b[a]) lm_seen[4*a+hh_b[2*a+:2]]<=1;
    always @(posedge clk or negedge rn[4])
        if(!rn[4]) done_seen<=0;
        else if(start_b_copy[2]) done_seen<=0;
        else for(integer a=0;a<4;a=a+1) if(done_slot[a]) done_seen[a]<=1;
    for(genvar sh=0;sh<4;sh=sh+1) begin:g_seen_head
        wire [23:0] local_hk;
        wire [3:0] local_z;
        ot_ahub6_word #(.W(24),.ID(200+sh)) u_hk(.ck(clk),.d({slot_h,slot_k}),.q(local_hk));
        ot_ahub6_async_word #(.W(4),.ID(220+sh)) u_z(.ck(clk),.rn(rn[16+sh]),.d(start_all[0]?4'd0:z_slot),.q(local_z));
        for(genvar c=0;c<4;c=c+1) begin:g_chunk
            ot_ahub6_seen_bits #(.HEAD(sh),.BASE(16*c),.ID(sh*4+c)) u_bits(
                .ck(clk),.rn(rn[8+sh*2+c/2]),.clear(start_b_copy[4+sh*4+c]),
                .z(local_z),.hk(local_hk),.q(zseen[sh][16*c+:16]));
        end
        // Original indices have a zero MSB; the upper half is reset-only zero.
        always @(posedge clk or negedge rn[20+sh])
            if(!rn[20+sh])zseen[sh][127:64]<=0;
            else if(start_b_copy[4+sh*4])zseen[sh][127:64]<=0;
    end
    for(genvar a=0;a<4;a=a+1)begin:g_lm_store
        for(genvar h=0;h<4;h=h+1)begin:g_head
            for(genvar c=0;c<4;c=c+1)begin:g_chunk
                ot_ahub6_lm_word #(.HEAD(h),.ID(a*16+h*4+c)) u_word(
                    .ck(clk),.rn(rn[24+a]),.start(start_all[(a==0)?0:(a==1)?9:(a==2)?10:30]),.en(lm_slot[a]),.head(slot_h[2*a+:2]),.d(data_b[32*a+8*c+:8]),.q(lm[4*a+h][8*c+:8]));
            end
        end
    end
    always @(posedge clk or negedge rn[0])if(!rn[0])zh_start<=0;else zh_start<={4{start_b_copy[2]}};
    always @(posedge clk)zh_sid<={4{data_b}};
    for(genvar sh=0;sh<4;sh=sh+1)begin:g_write_head
        for(genvar c=0;c<4;c=c+1)begin:g_chunk
            ot_ahub6_write_bits #(.HEAD(sh),.BASE(16*c),.ID(sh*4+c)) u_bits(
                .ck(clk),.z(g_seen_head[sh].local_z),.hk(g_seen_head[sh].local_hk),.q(zh_we[128*sh+16*c+:16]));
        end
        always @(posedge clk)zh_we[128*sh+64+:64]<=0;
    end
    function automatic fgt(input [31:0] a,input [31:0] b);
        fgt=(a[31]!=b[31])?!a[31]:(!a[31]?(a[30:0]>b[30:0]):(a[30:0]<b[30:0]));
    endfunction
    function automatic [32:0] fmax2(input [31:0] x,input ax,input [31:0] y,input ay);
        fmax2=!ax?{ay,y}:(!ay?{1'b1,x}:{1'b1,(fgt(y,x)?y:x)});
    endfunction
    // SAFE1: same-edge one-hot local LM selects. Each retained select
    // drives eight AND gates, rather than a binary head driving 128 muxes.
    (* keep = "true" *) reg [3:0] lm_sel[0:3][0:3];
    for(genvar ls=0;ls<4;ls=ls+1)begin:g_lm_stack
        for(genvar sl=0;sl<4;sl=sl+1)begin:g_lm_slice
            always @(posedge clk)
                lm_sel[ls][sl]<=4'd1<<(start_all[25+ls]?2'(2'd1-c_lis[1:0]):n_mh);
            always @(posedge clk)
                ma_x[32*ls+8*sl+:8]<=
                    ({8{lm_sel[ls][sl][0]}}&lm[4*ls+0][8*sl+:8])|
                    ({8{lm_sel[ls][sl][1]}}&lm[4*ls+1][8*sl+:8])|
                    ({8{lm_sel[ls][sl][2]}}&lm[4*ls+2][8*sl+:8])|
                    ({8{lm_sel[ls][sl][3]}}&lm[4*ls+3][8*sl+:8]);
        end
    end
    // SAFE1: local return-head select; binary q_th remains only metadata.
    (* keep = "true" *) reg [3:0] ret_sel[0:3];
    for(genvar sl=0;sl<4;sl=sl+1)begin:g_ret_sel
        always @(posedge clk)
            ret_sel[sl]<=4'd1<<(start_all[28]?2'(2'd1-c_rra[1:0]):n_th);
        for(genvar rh=0;rh<4;rh=rh+1)begin:g_head
            ot_ahub6_rz_word #(.ID(rh*4+sl)) u_word(.ck(clk),.en(return_enable_copy[rh*4+sl]),.sel(ret_sel[sl][rh]),.d(rc_y[8*sl+:8]),.q(rz[rh][8*sl+:8]));
        end
    end
    reg ma_v,mb_v,mo_v;
    reg [1:0] ma_h,mb_h,mo_h;
    reg [127:0] ma_x;
    reg [3:0] ma_a;
    reg [63:0] mb_x;
    reg [1:0] mb_a;
    reg [31:0] mo_data;
    wire [32:0] m01,m23,mfin;
    wire [15:0] ma_available;
    wire [7:0] mb_available;
    assign m01[32]=ma_a[0] || ma_a[1];
    assign m23[32]=ma_a[2] || ma_a[3];
    assign mfin[32]=mb_a[0] || mb_a[1];
    for(genvar a=0;a<4;a=a+1)begin:g_max_available
        for(genvar c=0;c<4;c=c+1)begin:g_chunk
            ot_ahub6_word #(.W(1),.ID(800+a*4+c)) u_ff(.ck(clk),.d(lany[4*a+mh]),.q(ma_available[4*a+c]));
        end
    end
    for(genvar c=0;c<4;c=c+1)begin:g_max_chunk
        ot_ahub6_word #(.W(1),.ID(820+c)) u_av0(.ck(clk),.d(m01[32]),.q(mb_available[c]));
        ot_ahub6_word #(.W(1),.ID(824+c)) u_av1(.ck(clk),.d(m23[32]),.q(mb_available[4+c]));
        ot_ahub6_max_bits #(.BASE(8*c),.ID(c)) u_pair0(.x(ma_x[31:0]),.y(ma_x[63:32]),.ax(ma_available[c]),.ay(ma_available[4+c]),.q(m01[8*c+:8]));
        ot_ahub6_max_bits #(.BASE(8*c),.ID(4+c)) u_pair1(.x(ma_x[95:64]),.y(ma_x[127:96]),.ax(ma_available[8+c]),.ay(ma_available[12+c]),.q(m23[8*c+:8]));
        ot_ahub6_max_bits #(.BASE(8*c),.ID(8+c)) u_final(.x(mb_x[31:0]),.y(mb_x[63:32]),.ax(mb_available[c]),.ay(mb_available[4+c]),.q(mfin[8*c+:8]));
    end
    // am valid leaves on mo_v (no u_io.start_all[25] term on the am pin flops: a start_all[25] on that edge is a calendar fault below)
    always @(posedge clk or negedge rn[1])
        if(!rn[1])begin ma_v<=0;mb_v<=0;mo_v<=0;for(integer a=0;a<4;a=a+1)am[36*a+35]<=0;end
        else begin ma_v<=m_issue&&!start_all[29];mb_v<=ma_v&&!start_all[29];mo_v<=mb_v&&!start_all[29];
            for(integer a=0;a<4;a=a+1)am[36*a+35]<=mo_v;end
    always @(posedge clk)begin
        ma_h<=mh;mb_h<=ma_h;mo_h<=mb_h;
        for(integer a=0;a<4;a=a+1)ma_a[a]<=lany[4*a+mh];
        mb_x<={m23[31:0],m01[31:0]};mb_a<={m23[32],m01[32]};mo_data<=mfin[31:0];
        for(integer a=0;a<4;a=a+1)am[36*a+:35]<={1'b0,mo_h,mo_data};
    end
    always @(posedge clk or negedge rn[2])if(!rn[2])zh_iv<=0;else zh_iv<=start_all[28]?16'd0:{4{issue}};
    always @(posedge clk)begin zh_g<=0;zh_p<={4{pair_base}};end
    reg [255:0] zroot_q;
    always @(posedge clk)zroot_q<=zh_root;
    wire [15:0] return_enable_copy;
    wire return_enable_next=start_all[29]?(c_rra<=16'd1):n_rr;
    for(genvar c=0;c<16;c=c+1)begin:g_return_enable
        ot_ahub6_async_copy #(.ID(700+c)) u_ff(.ck(clk),.rn(rn[21]),.d(return_enable_next),.q(return_enable_copy[c]));
    end
    wire [31:0] rz[0:3];
    reg [3:0] rz_seen;
    for(genvar a=0;a<4;a=a+1)assign rz4[32*a+:32]=rz[a];
    // KV-AHUB7 10-19 (COORD 17:00): the tree-select leg gets a registered relay stage: rt_q[a] = q_rs[a] & root_a, one
    // 32-flop word beside each Z tree (its select flop drives only those 32 ANDs), rc_x = OR of the four words one edge
    // later; rc_v follows one edge later too (rc_vp), and RECIP_RETURN counts RS_RLY (dw).  MUT 5 bypasses the stage.
    reg [31:0] rt_q[0:3];
    always @(posedge clk)for(integer a=0;a<4;a=a+1)rt_q[a]<={32{q_rs[a]}}&zroot_q[64*a+:32];
    wire [31:0] rc_sel=({32{q_rs[0]}}&zroot_q[31:0])|({32{q_rs[1]}}&zroot_q[95:64])|
                       ({32{q_rs[2]}}&zroot_q[159:128])|({32{q_rs[3]}}&zroot_q[223:192]);
    wire [31:0] rc_rly=rt_q[0]|rt_q[1]|rt_q[2]|rt_q[3];
    reg rc_vp;
    always @(posedge clk or negedge rn[3])
        if(!rn[3])begin rc_v<=0;rc_vp<=0;rz_valid<=0;rz_publish<=0;rz_seen<=0;rz_epoch<=0;end
        else begin
            rc_vp<=recip_issue&&!start_all[29];
            rc_v<=(RS_RLY!=0)?rc_vp:(recip_issue&&!start_all[29]);rz_valid<=recip_return&&!start_all[29];
            rz_publish<=active && pub_hit && !start_all[29];
            rz_epoch<=epoch;
            if(start_all[25])rz_seen<=0;else if(recip_return)rz_seen[return_head]<=1;
        end
    always @(posedge clk)begin
        rc_x<=(RS_RLY!=0 && MUT!=5)?rc_rly:rc_sel;
        rz_head<=return_head;rz_data<=rc_y;
        // Data capture uses per-slice one-hot return selection above.
    end
    // KV-AHUBDW2 10-18 (gate a2b: u_core.fault D -77 ps, the stack checks of the W (ap0/1) and E (ap2/3) faces into one
    // flop): the fault terms are registered first -- one flop per stack (tq, beside that stack's ap pin flops), one for the
    // global terms (gq), the start_all[25]-edge value (sq) -- and fault replays the sealed core's fault update one edge later
    // (fault here == the sealed core's fault delayed by exactly one edge; hf +1 edge, fault reporting only).
    // KV-AHUBDW2 10-18 gate a2c: the single gq flop was one deep AND chain from the Z-tree zh_err_q flops (y~43) to the
    // core (y~485): -278.5 ps.  gq is now five flops, one per term group (same edge, gq == |gqv): gqv[1] (Z/recip
    // errors) sits by the trees, the others by the core; fault ORs five flop outputs (one gate level, no added edge).
    // KV-AHUB6 10-19 (route a5 TT -59.4: zh_err_q -> gqv[1], an OR of 16 bits from the four trees): the Z-tree error term
    // of gqv[1] is one flop per tree (gz[a] = |zh_err[4a+:4], beside that tree's zh_err_q); fault ORs gz with gqv / tq on
    // the same edge as before (gqv[1] | |gz == the former gqv[1]).
    reg [3:0] tq;reg [4:0] gqv;reg [3:0] gz;reg sq,start_q,act_q;
    always @(posedge clk or negedge rn[20])
        if(!rn[20])begin tq<=0;gqv<=0;gz<=0;sq<=0;start_q<=0;act_q<=0;end
        else begin
            for(integer a=0;a<4;a=a+1)gz[a]<=|zh_err[4*a+:4];
            start_q<=start_all[25];act_q<=active;
            sq<=(T==0)||(T>8192)||(active_layer_parity!=active_layer[0])||mo_v;
            gqv[0]<=active_layer_parity!=parity || active_layer!=layer || request_epoch!=epoch;
            gqv[1]<=rc_fault || (rc_vo!=recip_return);
            gqv[2]<=(m_issue && lm_seen!=16'hffff) ||
                ((|issue) && (done_seen!=4'hf || zseen[0][63:0]!=zmask || zseen[1][63:0]!=zmask ||
                    zseen[2][63:0]!=zmask || zseen[3][63:0]!=zmask));
            gqv[3]<=first_q && (LMAX_IN_AGE==0 || Z_IN_AGE==0 || LMAX_ISSUE_AGE<1 || Z_START_AGE<1 ||
                    RECIP_ISSUE_AGE<=Z_START_AGE+77+Z_RT || RECIP_RETURN_AGE<=RECIP_ISSUE_AGE || RZ_PUBLISH_AGE<RECIP_RETURN_AGE+4);
            gqv[4]<=pub_hit && rz_seen!=4'hf;
            for(integer a=0;a<4;a=a+1)
                tq[a]<=(si_valid[a]!=(lm_slot[a]||z_slot[a]||done_slot[a])) ||
                    (si_valid[a] && (si_epoch[16*a+:16]!=epoch || si_layer[6*a+:6]!=layer || si_g[a] ||
                    si_type[2*a+:2]!=(lm_slot[a]?0:z_slot[a]?1:2) ||
                    ((lm_slot[a]||z_slot[a]) && si_hh[2*a+:2]!=slot_h[2*a+:2]) ||
                    (z_slot[a] && si_k[4*a+:4]!=slot_k[4*a+:4])));
        end
    always @(posedge clk or negedge rn[3])
        if(!rn[3])fault<=0;
        else if(start_q)fault<=sq;
        else if(act_q && (|gqv || |gz || |tq))fault<=1;
    initial if(Z_LEVEL_GAP<10 || Z_IN_STRIDE<4)$fatal(1,"invalid static AHUB geometry");
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_async_copy #(parameter integer ID=0,INIT=0)(input wire ck,rn,d,output wire q);
    (* keep=1 *) reg value;
    always @(posedge ck or negedge rn) if(!rn)value<=INIT;else value<=d;
    assign q=value;
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_word #(parameter integer W=24,ID=0)(input wire ck,input wire [W-1:0] d,output wire [W-1:0] q);
    (* keep=1 *) reg [W-1:0] value;
    always @(posedge ck)value<=d;
    assign q=value;
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_lm_word #(parameter integer HEAD=0,ID=0)(input wire ck,rn,start,en,input wire [1:0] head,input wire [7:0] d,output wire [7:0] q);
    (* keep=1 *) reg local_en;
    (* keep=1 *) reg [1:0] local_head;
    always @(posedge ck or negedge rn)if(!rn)local_en<=0;else local_en<=en && !start;
    always @(posedge ck)local_head<=head;
    (* keep=1 *) reg [7:0] value;
    always @(posedge ck)if(local_en && local_head==2'(HEAD))value<=d;
    assign q=value;
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_rz_word #(parameter integer ID=0)(input wire ck,en,sel,input wire [7:0] d,output wire [7:0] q);
    (* keep=1 *) reg [7:0] value;
    always @(posedge ck)if(en && sel)value<=d;
    assign q=value;
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_max_bits #(parameter integer BASE=0,ID=0)(input wire [31:0] x,y,input wire ax,ay,output wire [7:0] q);
    wire greater=(y[31]!=x[31])?!y[31]:(!y[31]?(y[30:0]>x[30:0]):(y[30:0]<x[30:0]));
    wire choose_y=!ax || (ay && greater);
    assign q=choose_y?y[BASE+:8]:x[BASE+:8];
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_head_copy #(parameter integer ID=0)(input wire ck,start,input wire [1:0] first,next_head,output wire [3:0] q);
    (* keep=1 *) reg [3:0] value;
    always @(posedge ck)value<=4'd1<<(start?first:next_head);
    assign q=value;
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_async_word #(parameter integer W=4,ID=0)(input wire ck,rn,input wire [W-1:0] d,output wire [W-1:0] q);
    (* keep=1 *) reg [W-1:0] value;
    always @(posedge ck or negedge rn)if(!rn)value<=0;else value<=d;
    assign q=value;
endmodule

module ot_ahub6_reset_two #(parameter integer COPIES=24)(input wire ck,d,output wire [COPIES-1:0] q);
    // Match ot_rst_pipe: asynchronous assertion, two synchronizer stages,
    // then the two plain regional stages. The consumers keep the original age.
    (* keep=1, dont_touch=1 *) reg s0,s1;
    always @(posedge ck or negedge d)
        if(!d)begin s0<=0;s1<=0;end else begin s0<=1;s1<=s0;end
    wire first;
    ot_pl_land_field_copy_bit #(.ID(14000)) u_first(.ck(ck),.d(s1),.q(first));
    for(genvar c=0;c<COPIES;c=c+1)begin:g_copy
        ot_pl_land_field_copy_bit #(.ID(14001+c)) u_ff(.ck(ck),.d(first),.q(q[c]));
    end
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_seen_bits #(parameter integer HEAD=0,BASE=0,ID=0)(
    input wire ck,rn,clear,input wire [3:0] z,input wire [23:0] hk,output reg [15:0] q
);
    for(genvar j=0;j<16;j=j+1)begin:g_bit
        localparam integer A=(BASE+j)%4;
        always @(posedge ck or negedge rn)
            if(!rn)q[j]<=0;
            else if(clear)q[j]<=0;
            else if(z[A] && hk[16+2*A+:2]==2'(HEAD) && hk[4*A+:4]==4'((BASE+j)/4))q[j]<=1;
    end
endmodule

(* keep_hierarchy="yes" *)
module ot_ahub6_write_bits #(parameter integer HEAD=0,BASE=0,ID=0)(
    input wire ck,input wire [3:0] z,input wire [23:0] hk,output reg [15:0] q
);
    for(genvar j=0;j<16;j=j+1)begin:g_bit
        localparam integer A=(BASE+j)%4;
        always @(posedge ck)
            q[j]<=z[A] && hk[16+2*A+:2]==2'(HEAD) && hk[4*A+:4]==4'((BASE+j)/4);
    end
endmodule

module ot_ahub6_reset_pad #(parameter integer N=7,COPIES=4)(input wire ck,d,output wire [COPIES-1:0] q);
    wire prefix;
    ot_pl_pad #(.W(1),.N(N-1)) u_prefix(.ck(ck),.d(d),.q(prefix));
    for(genvar c=0;c<COPIES;c=c+1) begin:g_copy
        ot_pl_land_field_copy_bit #(.ID(12000+c)) u_ff(.ck(ck),.d(prefix),.q(q[c]));
    end
endmodule
