`timescale 1ns/1ps
// HF-5c 10-18: the attention SM front ot_hbm_sm_attn_front_static SPLIT into its two independent halves, so the landed
// parent ot_hbm_accel_smh_attn_flat_lp has no cross-region loop (front -> tiles -> BE -> q chain -> front):
//   ot_hbm_sm_attn_front_launch  = ot_hbm_sm_attn_front_static minus the result path (request, schedule_fault, rl/rr/bl/br);
//                                  its ot_smh_static_front is ot_smh_static_front_launch (lines 1-120 of the static front)
//   ot_smh_static_front_result   = ot_smh_static_front's result path (ql/qr lane landing, deskew, result_valid, rv /
//                                  rrow / rdata / fault pins), verbatim.  In the static front NOTHING on the launch side reads
//                                  ql / qr (rl / rr / bl / br / expected_request / schedule_fault come from feed + fc_*), and the
//                                  attention front's fault IS the static front's fault (result_fault sticky), so the split is exact.
//   ot_hbm_sm_attn_becmd         = ot_hbm_accel_smh_attn's be_cmd register (command[111:83]) as a soft glue child.
// Text is copied from the closed sources (they stay byte-identical); equivalence: tb_smh_attn_flat_eq (random lockstep
// vs ot_hbm_accel_smh_attn) + sm_elem_bench --flat (golden protocol bench on the flat parent).
// The static halves keep the static front's implicit-net default (no `default_nettype none), as their source.
module ot_smh_static_front_launch(
 input wire clk,rst_n,input wire [82:0] command,input wire [1098:0] packet,
 output wire [42:0] expected_request,output wire schedule_fault,
 input wire xw_en,input wire [6:0] xw_addr,xw_grp,input wire [2047:0] xw_data,
 output wire [4*818-1:0] rl,rr,output wire [2*2069-1:0] bl,br
);
 localparam integer SUB=4,LBS=2,LSB=16,NC=8,IL=8,RMAX=4096,XD=128,
   RPT=2,PIO=2,PT4=1,RESULT_VALID=1,SW=3,RW=12,XW=7,TAGW=16,
   CW=22,RBW=818,BBW=2069,NBEAT=13,QLW=46,NL=4,NR=4,NH=4;
 wire [818-1:0] fi_row0,r3a,fi_row3,r0a_e,r3a_e;
 wire [2068:0] fx_b,xw_w,xw_e,xr_w,xr_e;
 wire [1081:0] lt0,lt1;wire [569:0] lb0,lb1,lbr0,lbr1;
 wire [11:0] fm;wire [2:0] fmr0,fmr1;
 ot_smh_static_feed u_feed(.clk(clk),.rst_n(rst_n),.command(command),.packet(packet),
   .expected_request(expected_request),.fault(schedule_fault),.lt0(lt0),.lt1(lt1),.lb0(lb0),.lb1(lb1),.fm(fm));
    // ---------------- x-write beat at the pins (sm_pq's w0): wl, wm, w0 as in m2 ----------------
    reg              w0_en;
    reg [XW-1:0]     w0_addr;
    reg [NBEAT-1:0]  w0_oh;
    reg [2047:0]     w0_data;
    integer gq;
    reg              wl_en, wm_en;
    reg [XW-1:0]     wl_addr, wm_addr;
    reg [6:0]        wl_grp, wm_grp;
    reg [2047:0]     wl_data, wm_data;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wl_en <= 1'b0; wm_en <= 1'b0; w0_en <= 1'b0; end
        else begin wl_en <= xw_en; wm_en <= wl_en; w0_en <= wm_en; end
    always @(posedge clk) begin
        wl_addr <= xw_addr; wl_grp <= xw_grp; wl_data <= xw_data;
        wm_addr <= wl_addr; wm_grp <= wl_grp; wm_data <= wl_data;
        w0_addr <= wm_addr; w0_data <= wm_data;
        for (gq = 0; gq < NBEAT; gq = gq + 1) w0_oh[gq] <= (wm_grp == 7'(gq));
    end
    wire [BBW-1:0] w0_b = {w0_en, w0_addr, w0_oh, w0_data};
    // tile row 1's beat: its m2 A stage, launched at the south face
    ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_fxv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(w0_b[BBW-1]),
        .q(fx_b[BBW-1]));
    ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_fxd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(w0_b[BBW-2:0]),
        .q(fx_b[BBW-2:0]));
    // tile row 0's beat: A, M, O per side (m2)
    genvar sd;
    wire [2*BBW-1:0] o_b;
    generate for (sd = 0; sd < 2; sd = sd + 1) begin : g_side
        wire [BBW-1:0] a_b, m_b;
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bav (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(w0_b[BBW-1]),
            .q(a_b[BBW-1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bad (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(w0_b[BBW-2:0]),
            .q(a_b[BBW-2:0]));
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bmv (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(a_b[BBW-1]),
            .q(m_b[BBW-1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bmd (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(a_b[BBW-2:0]),
            .q(m_b[BBW-2:0]));
        ot_hbm_accel_smh_kreg #(.W(1), .RST(1)) u_bov (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(m_b[BBW-1]),
            .q(o_b[sd*BBW + BBW - 1]));
        ot_hbm_accel_smh_kreg #(.W(BBW-1)) u_bod (.clk(clk), .rst_n(rst_n), .en(1'b1), .d(m_b[BBW-2:0]),
            .q(o_b[sd*BBW +: BBW-1]));
    end endgenerate
    assign bl[0+:BBW] = o_b[0 +: BBW];
    assign br[0+:BBW] = o_b[BBW +: BBW];
    // row 0's bundle: landed in one copy PER SIDE (hbm-blocks 2026-10-07: m3f u_rl -> u_ol -108.56 ps / 5 levels, one
    // south-face copy feeding both edge registers; each copy now sits between the face and its side, 0 cycles), then
    // the O register per side at its pins
    wire [RBW-1:0] r0l_l, r0l_r;
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW), .K(1)) u_rl (.clk(clk), .rst_n(rst_n),
        .d(fi_row0), .q(r0l_l));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW), .K(1)) u_rr (.clk(clk), .rst_n(rst_n),
        .d(fi_row0), .q(r0l_r));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_ol (.clk(clk), .rst_n(rst_n),
        .d(r0l_l), .q(rl[0+:RBW]));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_or (.clk(clk), .rst_n(rst_n),
        .d(r0l_r), .q(rr[0+:RBW]));
wire [817:0] r0a;
    ot_hbm_accel_smh_fc_xl #(.TAGW(TAGW)) u_xl (.clk(clk), .rst_a(rst_n), .fx_b(fx_b), .xw_w(xw_w), .xw_e(xw_e), .r0a(r0a),
        .fo_row0(fi_row0));
    ot_hbm_accel_smh_fc_t #(.ENABLE_INT8(0),.TAGW(TAGW)) u_tw (.clk(clk), .rst_a(rst_n), .li(lt0), .fi(fm[2:0]), .rout(rl[RBW+:RBW]), .r0a(r0a));
    ot_hbm_accel_smh_fc_t #(.ENABLE_INT8(0),.TAGW(TAGW)) u_te (.clk(clk), .rst_a(rst_n), .li(lt1), .fi(fm[8:6]), .rout(rr[RBW+:RBW]), .r0a(r0a_e));
    ot_hbm_accel_smh_fc_xr #(.TAGW(TAGW)) u_rw (.clk(clk), .rst_a(rst_n), .xi(xw_w), .xo(xr_w), .li(lb0), .lo(lbr0), .fi(fm[5:3]), .fo(fmr0));
    ot_hbm_accel_smh_fc_xr #(.TAGW(TAGW)) u_re (.clk(clk), .rst_a(rst_n), .xi(xw_e), .xo(xr_e), .li(lb1), .lo(lbr1), .fi(fm[11:9]), .fo(fmr1));
    ot_hbm_accel_smh_fc_b #(.ENABLE_INT8(0),.TAGW(TAGW)) u_bw (.clk(clk), .rst_a(rst_n), .li(lbr0), .fi(fmr0), .xi(xr_w), .bout(bl[BBW+:BBW]),
        .rout(rl[2*RBW+:RBW]), .r3a(r3a));
    ot_hbm_accel_smh_fc_b #(.ENABLE_INT8(0),.TAGW(TAGW)) u_be (.clk(clk), .rst_a(rst_n), .li(lbr1), .fi(fmr1), .xi(xr_e), .bout(br[BBW+:BBW]),
        .rout(rr[2*RBW+:RBW]), .r3a(r3a_e));

ot_hbm_accel_smh_bundle_reg #(.W(818),.V(20),.NV(2),.X(7)) u_m3(.clk(clk),.rst_n(rst_n),.d(r3a),.q(fi_row3));
    // row 3's bundle: landed at the north face, O per side at its pins
    wire [RBW-1:0] r3l;
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_r3l (.clk(clk), .rst_n(rst_n),
        .d(fi_row3), .q(r3l));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_o3l (.clk(clk), .rst_n(rst_n),
        .d(r3l), .q(rl[3*RBW+:RBW]));
    ot_hbm_accel_smh_bundle_reg #(.W(RBW), .V(CW-2), .NV(2), .X(XW)) u_o3r (.clk(clk), .rst_n(rst_n),
        .d(r3l), .q(rr[3*RBW+:RBW]));
endmodule

module ot_smh_static_front_result(
 input wire clk,rst_n,
 input wire [4*46-1:0] ql,qr,output wire rv,output wire [11:0] rrow,
 output wire [255:0] rdata,output wire fault
);
 localparam integer NC=8,RW=12,QLW=46,NL=4,NR=4,NH=4,PT4=1,RESULT_VALID=1,PIO=2;
 genvar sd;
    // ---------------- results: lane landing, deskew, pins (m2, unchanged) ----------------
    // el1013-smh-r14 OT_SMH_PINREG: the gated tile lands rin / bin in its own pin registers (+1 row-bundle register per
    // tile hop), so a column's results arrive 1 more cycle per hop: the deskew is (5 + PT4 + PINR) a hop
    // OT_SMH_MUT_PINR_DESKEW (bench mutant only): the front keeps the 5 + PT4 deskew against pin-registered tiles
    localparam integer PINR =
`ifdef OT_SMH_MUT_PINR_DESKEW
        0;
`elsif OT_SMH_PINREG
        1;
`else
        0;
`endif
    wire fsv;
    wire [NC*QLW-1:0] al;
    genvar ln;
    generate for (sd = 0; sd < 2; sd = sd + 1) begin : g_qs
        for (ln = 0; ln < NH; ln = ln + 1) begin : g_ln
            localparam integer COLN = (sd == 0) ? NL - 1 - ln : NL + ln;
            if (COLN >= 0 && COLN < NC && ((sd == 0 && ln < NL) || (sd == 1 && ln < NR))) begin : g_use
                wire [QLW-1:0] lin = (sd == 0) ? ql[ln*QLW +: QLW] : qr[ln*QLW +: QLW];
                wire [QLW-1:0] land;
                ot_hbm_accel_smh_kreg #(.W(2), .RST(1)) u_lv (.clk(clk), .rst_n(rst_n), .en(1'b1),
                    .d(lin[QLW-1 -: 2]), .q(land[QLW-1 -: 2]));
                ot_hbm_accel_smh_kreg #(.W(QLW-2)) u_ld (.clk(clk), .rst_n(rst_n), .en(1'b1),
                    .d(lin[QLW-3:0]), .q(land[QLW-3:0]));
                ot_hbm_accel_smv_chain #(.W(2), .D((5+PT4+PINR)*(NH-1-ln)), .RST(1)) u_dv (.clk(clk), .rst_n(rst_n),
                    .d(land[QLW-1 -: 2]), .q(al[COLN*QLW + QLW - 2 +: 2]));
                ot_hbm_accel_smv_chain #(.W(QLW-2), .D((5+PT4+PINR)*(NH-1-ln)), .RST(0)) u_dd (.clk(clk), .rst_n(rst_n),
                    .d(land[QLW-3:0]), .q(al[COLN*QLW +: QLW-2]));
            end
        end
    end endgenerate
    wire [NC-1:0]    cf_a;
    wire [NC-1:0]    cv_a;
    wire result_v, result_fault;
    wire [NC*32-1:0] cy_a;
    genvar cc;
    generate for (cc = 0; cc < NC; cc = cc + 1) begin : g_al
        assign cf_a[cc] = al[cc*QLW + QLW - 2];
        assign cv_a[cc] = al[cc*QLW + QLW - 1];
        assign cy_a[32*cc +: 32] = al[cc*QLW + RW +: 32];
    end endgenerate
    ot_hbm_accel_smh_result_valid #(.NC(NC), .ENABLE(RESULT_VALID)) u_result_valid (
        .valids(cv_a), .faults(cf_a), .row_valid(result_v), .fault_event(result_fault));
    // retire: stage 1 of m2's three, at the north face (front_c lands it and adds the third beside the issue)
    ot_hbm_accel_smv_chain #(.W(1), .D(1), .RST(1)) u_sv (.clk(clk), .rst_n(rst_n), .d(result_v), .q(fsv));
    reg fault_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_q <= 1'b0;
        else fault_q <= fault_q | result_fault
            ;
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO), .RST(1)) u_prv_o (.clk(clk), .rst_n(rst_n), .d(result_v), .q(rv));
    ot_hbm_accel_smv_chain #(.W(1), .D(PIO), .RST(1)) u_pfo (.clk(clk), .rst_n(rst_n), .d(fault_q), .q(fault));
    ot_hbm_accel_smv_chain #(.W(RW + NC*32), .D(PIO), .RST(0)) u_prd_o (.clk(clk), .rst_n(rst_n),
        .d({al[RW-1:0], cy_a}), .q({rrow, rdata}));
endmodule

`default_nettype none
module ot_hbm_sm_attn_front_launch #(parameter integer KVMUT = 0)(   // KVMUT: bench negative control only (ot_hbm_sm_kv_line MUT)
    input wire clk,rst_n,
    input wire [191:0] command,
    input wire [63:0] kv_desc,
    input wire [1098:0] packet,
    input wire xw_en,input wire [6:0] xw_addr,xw_grp,input wire [2047:0] xw_data,
    output wire [42:0] request,
    output wire [3271:0] rl,rr,
    output wire [4137:0] bl,br,
    output reg schedule_fault
);
    wire [2:0] mode=command[183:181];
    wire attention=mode[2];
    wire h128=command[180];
    wire configure=attention && command[179];
    wire consume=attention && command[152];
    wire arithmetic_v=attention && command[25];
    wire pv=mode[1];
    wire [3271:0] normal_l,normal_r;
    wire [42:0] normal_request;
    wire normal_schedule_fault;
    ot_smh_static_front_launch u_normal(.clk(clk),.rst_n(rst_n),
        .command(attention?83'd0:command[82:0]),.packet(attention?1099'd0:packet),
        .expected_request(normal_request),.schedule_fault(normal_schedule_fault),
        .xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
        .rl(normal_l),.rr(normal_r),.bl(bl),.br(br));
    wire request_v;
    wire [31:0] request_addr;
    wire [9:0] request_tag;
    wire descriptor_fault;
    // r2: one contiguous line-run descriptor (canonical packed rows); command[115] = load, command[82] = next line
    ot_hbm_sm_kv_desc_static u_desc(.clk(clk),.rst_n(rst_n),.kv_desc(kv_desc),
        .load(attention&&command[115]),.request_v(attention&&command[82]),
        .request_tag(command[49:40]),.req_v(request_v),.req_addr(request_addr),
        .req_tag(request_tag),.fault(descriptor_fault));
    reg attention_q;
    reg [42:0] expected_q;
    always @(posedge clk)expected_q<=command[82:40];
    always @(posedge clk or negedge rst_n)
        if(!rst_n)attention_q<=0;else attention_q<=attention;
    assign request=attention_q?{request_v,request_addr,request_tag}:normal_request;
    wire converter_ready,b_valid,b_last,b_wend,converter_busy,converter_fault;
    wire [1023:0] b_data;
    wire [2:0] b_slot,b_step;
    ot_hbm_sm_kv_line #(.MUT(KVMUT)) u_converter(.clk(clk),.rst_n(rst_n),.cfg_v(configure),
        .cfg_qk(!pv),.cfg_kv4(mode[0]),.cfg_n8(command[165:153]),.cfg_h128(h128),.cfg_rows(command[178:166]),
        .s_valid(attention&&packet[1098]),.s_ready(converter_ready),.s_data(packet[1087:0]),
        .m_valid(b_valid),.m_ready(consume),.m_data(b_data),.m_slot(b_slot),.m_step(b_step),
        .m_wend(b_wend),.m_last(b_last),.busy(converter_busy),.fault(converter_fault));
    wire p_v,p_fault;
    wire [127:0] p_data;
    ot_hbm_sm_attn_pstore u_p(.clk(clk),.rst_n(rst_n),.clear_v(attention&&command[145]),
        .xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
        .read_v(attention&&command[144]),.read_addr(command[143:137]),
        .p_v(p_v),.p_data(p_data),.fault(p_fault));
    reg [531:0] metadata;
    always @(*)begin
        metadata=0;metadata[127:0]=p_data;
        metadata[130:128]=mode;metadata[131]=h128;
        metadata[132]=command[136];metadata[133]=command[135];
        metadata[134]=command[134];metadata[136:135]=command[133:132];metadata[137]=consume;
        // r2 in-SM PV stream fold (head dim 128): command[131] fold, [130:128] entry a, [127:125] entry b
        metadata[138]=attention&&command[131];metadata[141:139]=command[130:128];metadata[144:142]=command[127:125];
        metadata[145]=command[124];                    // folded publication (head dim 128)
    end
    wire [15:0] tag={command[22:11],command[10],command[9:7]};
    wire [21:0] control={1'b0,(arithmetic_v || (attention&&(command[134]||command[131]))),command[24],command[23],1'b1,1'b1,tag};
    wire [3271:0] a_rows;
    genvar j;
    generate for(j=0;j<4;j=j+1)begin:g_row
        ot_hbm_sm_attn_row_launch u_row(.clk(clk),.rst_n(rst_n),
            .d({control,b_data[256*j+:256],metadata,arithmetic_v&&!pv,command[6:0]}),
            .q(a_rows[818*j+:818]));
        assign rl[818*j+:818]=attention_q?a_rows[818*j+:818]:normal_l[818*j+:818];
        assign rr[818*j+:818]=attention_q?a_rows[818*j+:818]:normal_r[818*j+:818];
    end endgenerate
    always @(posedge clk or negedge rst_n)
        if(!rst_n)schedule_fault<=0;
        else begin
            if(command!=0 && (command[191:184]!=8'ha2 || |command[123:116] || |command[114:112] || command[111]))schedule_fault<=1;
            if(!attention && mode==3)schedule_fault<=1;
            if(attention_q && (request[42]!=expected_q[42] || (request[42] && request!=expected_q)))schedule_fault<=1;
            if(!attention && command[25] && converter_busy)schedule_fault<=1;
            if(!attention && command[28] && command[27:26]!=mode[1:0])schedule_fault<=1;
            if(attention)begin
                if(packet[1098]!=command[29] || (command[29] && packet[1097:1088]!=command[39:30]))schedule_fault<=1;
                if(packet[1098] && !converter_ready)schedule_fault<=1;
                if(consume!=arithmetic_v || (consume && (!b_valid || b_slot!=command[151:149] || b_step!=command[148:146])))schedule_fault<=1;
                if(consume && pv && !p_v)schedule_fault<=1;
                if(configure && (converter_busy || command[178:166]==0 || (h128 && mode[0])))schedule_fault<=1;
            end
            if(descriptor_fault || converter_fault || p_fault || normal_schedule_fault)schedule_fault<=1;
        end
endmodule


module ot_hbm_sm_attn_becmd(
    input wire clk,rst_n,
    input wire [28:0] d,
    output reg [28:0] q
);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 29'd0; else q <= d;
endmodule
`default_nettype wire
