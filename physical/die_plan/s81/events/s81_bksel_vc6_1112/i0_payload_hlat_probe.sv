`timescale 1ns/1ps
`define OT_BKQ_FO8
`define OT_BKQ_R1C8
`define OT_BKQ_I0_OUT_HLAT
module ot_s81ph_hlk #(parameter integer W = 1, parameter integer EN = 0) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (EN != 0) begin : g_lat
        reg [W-1:0] l;
`ifdef OT_S81PH_HLK_MUT
        always_latch if (clk) l <= d;     // bench mutant: positive-level latch (the hop passes in the high phase)
`else
        always_latch if (!clk) l <= d;
`endif
        assign q = l;
`ifdef OT_S81PH_HLK_COV
        // bench coverage only: count q changes (each latch must toggle under the layer traffic)
        integer ntog = 0; reg [W-1:0] lq;
        always @(negedge clk) begin #0.001 if (l !== lq) ntog = ntog + 1; lq = l; end
        final $display("HLK_COV %m W %0d toggles %0d", W, ntog);
`endif
    end else begin : g_wire
        assign q = d;
    end endgenerate
endmodule
module i0_probe_hlk #(parameter integer W = 1, parameter integer EN = 0) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate if (EN != 0) begin : g_lat
        reg [W-1:0] l;
`ifdef OT_S81PH_HLK_MUT
        always_latch if (clk) l <= d;     // bench mutant: positive-level latch (the hop passes in the high phase)
`else
        `ifdef I0_OUT_STALE_MUT
        always @(posedge clk) l <= d; // extra-cycle mutant ONLY on new forwarding hop
`else
        always_latch if (!clk) l <= d;
`endif
`endif
        assign q = l;
`ifdef OT_S81PH_HLK_COV
        // bench coverage only: count q changes (each latch must toggle under the layer traffic)
        integer ntog = 0; reg [W-1:0] lq;
        always @(negedge clk) begin #0.001 if (l !== lq) ntog = ntog + 1; lq = l; end
        final $display("HLK_COV %m W %0d toggles %0d", W, ntog);
`endif
    end else begin : g_wire
        assign q = d;
    end endgenerate
endmodule
module i0_ref(input clk,rst_n,acc,rp_acc,in_last,t2_fl,input [15:0] in_lv,input [255:0] in_val,input [319:0] in_idx,input [63:0] in_sg,input [127:0] c_Tc,input [31:0] c_Btc,input [591:0] mem_rdata,output [591:0] lane_view,replay,output [255:0] key_view,output [31:0] sign_view,output [31:0] mask_view,output [143:0] cmp_view,output [4:0] controls);
 localparam integer W=16,IW=20,EW=37,MW=592,NG=22,GB=27,HLAT=1,MUT=0;
 genvar gl,gg;
 wire in_last_l=in_last;wire [15:0]in_lv_l=in_lv;wire [255:0]in_val_l=in_val;wire[319:0]in_idx_l=in_idx;
 wire [MW-1:0]r1_d;
    function automatic [15:0] kp(input [15:0] v);
        kp = v[15] ? ~v : {1'b1, v[14:0]};
    endfunction
    reg            i0_v, i0_last, i0_rp;
    reg [W-1:0]    i0_lv;
    reg [W*16-1:0] i0_val;
    reg [W*IW-1:0] i0_idx;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) i0_v <= 1'b0;
        else i0_v <= acc;
    end
    always @(posedge clk) begin
        i0_last <= in_last_l; i0_lv <= in_lv_l; i0_val <= in_val_l; i0_idx <= in_idx_l; i0_rp <= rp_acc;
    end

    // -- ingest: filter (CMP_RETIME, H8) ----------------------------------------------------------------------------
    wire [W-1:0]    i1_s_d, i1_fm_d;
    wire [W*16-1:0] i1_k_d;
    wire [W*EW-1:0] i0_lane;
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_i1
            // i1_k = fkey(i0_val): key' with the -0 override
            wire [15:0] v0  = i0_val[16*gl +: 16];
            wire        nz0 = (v0 == 16'h8000);
            assign i1_k_d[16*gl +: 16] = nz0 ? 16'h8000 : kp(v0);
            // compare nibbles on the edge in_val becomes i0_val (as the original CMP_RETIME): key' nibble n uses
            // sign copy n, the bound copy of the lane's 4-lane group; nz lanes take the 0x8000 results
            wire [15:0] vx  = in_val[16*gl +: 16];
`ifdef OT_BKQ_FO8
            wire [15:0] cT  = c_Tc[16*(gl / 2) +: 16];
`else
            wire [15:0] cT  = c_Tc[16*(gl / 4) +: 16];
`endif
            wire [7:0]  cB  = c_Btc[8*(gl / 4) +: 8];
            wire        nzx = (vx == 16'h8000);
            wire [15:0] ik;
            assign ik[15]   = ~in_sg[4*gl + 3];
            assign ik[14:12] = vx[14:12] ^ {3{in_sg[4*gl + 3]}};
            assign ik[11:8] = vx[11:8] ^ {4{in_sg[4*gl + 2]}};
            assign ik[7:4]  = vx[7:4]  ^ {4{in_sg[4*gl + 1]}};
            assign ik[3:0]  = vx[3:0]  ^ {4{in_sg[4*gl + 0]}};
            reg [3:0] cmp_gt, cmp_eq;
            reg hi_match;
            integer nib;
            always @(posedge clk) begin
                for (nib = 0; nib < 4; nib = nib + 1) begin
                    cmp_gt[nib] <= nzx ? ((nib == 3) ? (4'h8 > cT[15:12]) : 1'b0) : (ik[4*nib +: 4] > cT[4*nib +: 4]);
                    cmp_eq[nib] <= nzx ? ((nib == 3) ? (cT[15:12] == 4'h8) : (cT[4*nib +: 4] == 4'h0))
                                       : (ik[4*nib +: 4] == cT[4*nib +: 4]);
                end
                hi_match <= nzx ? (cB == 8'h80) : (ik[15:8] == cB);
            end
            wire ge_lo = cmp_gt[1] || (cmp_eq[1] && (cmp_gt[0] || cmp_eq[0]));
            wire ge = cmp_gt[3] || (cmp_eq[3] && cmp_gt[2]) || (cmp_eq[3] && cmp_eq[2] && ge_lo);
            assign i1_s_d[gl] = i0_lv[gl] && ge;
            assign i1_fm_d[gl] = i0_lv[gl] && ge && hi_match;
            assign i0_lane[EW*gl +: EW] = {i0_lv[gl], i0_val[16*gl +: 16], i0_idx[IW*gl +: IW]};
        end
    endgenerate
    reg            i1_v, i1_fl;
    reg [W-1:0]    i1_fm;
    reg [W*16-1:0] i1_k;
    reg [W*EW-1:0] i1_p;
    wire i_ing = i0_v && !i0_rp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin i1_v <= 1'b0; i1_fl <= 1'b0; end
        else begin i1_v <= i_ing; i1_fl <= i_ing && i0_last; end
    end
    always @(posedge clk) begin i1_fm <= i1_fm_d; i1_k <= i1_k_d; end

    wire rpd = acc && rp_acc;                    // rp_beat on the next edge
    wire mbd = !rpd && !t2_fl;                   // memory line on the next edge (tq_fl = t3_fl <= t2_fl)
    wire [NG-1:0] rpb_v, memb_v;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_r1
        localparam integer LO = gg * GB;
        localparam integer SW = (MW - LO < GB) ? (MW - LO) : GB;
        (* keep = "true" *) reg rpb, memb;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin rpb <= 1'b0; memb <= 1'b1; end
            else begin rpb <= rpd; memb <= (MUT == 1 && gg == 7) ? 1'b0 : mbd; end
        assign rpb_v[gg] = rpb; assign memb_v[gg] = memb;
        reg [SW-1:0] q;
        wire rpb_l, memb_l;   // HLAT: rpb / memb -> q through one lockup latch
        ot_s81ph_hlk #(.W(2), .EN(HLAT)) u_fl_r1s (.clk(clk), .d({rpb, memb}), .q({rpb_l, memb_l}));
`ifdef OT_BKQ_R1C8
        // Same-cycle H2 control copies: each kept pair owns at most eight payload bits.
        // The original rpb/memb pair still owns the sign sideband (rpb_v/memb_v).
        // Every copy samples the identical rpd/mbd edge and retains the launch-side HLAT.
        for (genvar rs = 0; rs < (SW+7)/8; rs = rs + 1) begin : g_cp8
            localparam integer RL = rs*8;
            localparam integer RW = (SW-RL < 8) ? SW-RL : 8;
            (* keep = "true" *) reg rp8, mb8;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin rp8 <= 1'b0; mb8 <= 1'b1; end
                else begin
`ifdef OT_BKQ_R1C8_MUT
                    rp8 <= (gg == 5 && rs == 2) ? !rpd : rpd;
`else
                    rp8 <= rpd;
`endif
                    mb8 <= (MUT == 1 && gg == 7) ? 1'b0 : mbd;
                end
            wire rp8_l, mb8_l;
            ot_s81ph_hlk #(.W(2), .EN(HLAT)) u_fl_r1s (.clk(clk), .d({rp8, mb8}), .q({rp8_l, mb8_l}));
            always @(posedge clk) q[RL +: RW] <= (i0_lane[LO+RL +: RW] & {RW{rp8_l}}) | (mem_rdata[LO+RL +: RW] & {RW{mb8_l}});
        end
`else
        always @(posedge clk) q <= (i0_lane[LO +: SW] & {SW{rpb_l}}) | (mem_rdata[LO +: SW] & {SW{memb_l}});
`endif
        assign r1_d[LO +: SW] = q;
    end endgenerate

    wire [W*2-1:0] r1sg;
    generate for (gl = 0; gl < W; gl = gl + 1) begin : g_r1sg
        localparam integer SB = EW*gl + IW + 15;
        localparam integer GS = SB / GB;
        localparam integer GO = SB - GS * GB;
        (* keep = "true" *) reg [1:0] r;
        always @(posedge clk) r <= {2{(i0_lane[SB] & rpb_v[GS]) | (mem_rdata[SB] & memb_v[GS])}};
        assign r1sg[2*gl +: 2] = r;
    end endgenerate

 reg[15:0]s_hcr;always @(posedge clk)s_hcr<=i1_s_d;
 assign lane_view=i0_lane;assign replay=r1_d;assign key_view=i1_k;assign sign_view=r1sg;assign mask_view={i1_fm,s_hcr};assign controls={i0_v,i0_rp,i0_last,i1_v,i1_fl};
 for(genvar cg=0;cg<16;cg=cg+1)begin:obs
 assign cmp_view[9*cg+:9]={g_i1[cg].cmp_gt,g_i1[cg].cmp_eq,g_i1[cg].hi_match};end
endmodule

module i0_new(input clk,rst_n,acc,rp_acc,in_last,t2_fl,input [15:0] in_lv,input [255:0] in_val,input [319:0] in_idx,input [63:0] in_sg,input [127:0] c_Tc,input [31:0] c_Btc,input [591:0] mem_rdata,output [591:0] lane_view,replay,output [255:0] key_view,output [31:0] sign_view,output [31:0] mask_view,output [143:0] cmp_view,output [4:0] controls);
 localparam integer W=16,IW=20,EW=37,MW=592,NG=22,GB=27,HLAT=1,MUT=0;
 genvar gl,gg;
 wire in_last_l=in_last;wire [15:0]in_lv_l=in_lv;wire [255:0]in_val_l=in_val;wire[319:0]in_idx_l=in_idx;
 wire [MW-1:0]r1_d;
    function automatic [15:0] kp(input [15:0] v);
        kp = v[15] ? ~v : {1'b1, v[14:0]};
    endfunction
    reg            i0_v, i0_last, i0_rp;
    reg [W-1:0]    i0_lv;
    reg [W*16-1:0] i0_val;
    reg [W*IW-1:0] i0_idx;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) i0_v <= 1'b0;
        else i0_v <= acc;
    end
    always @(posedge clk) begin
        i0_last <= in_last_l; i0_lv <= in_lv_l; i0_val <= in_val_l; i0_idx <= in_idx_l; i0_rp <= rp_acc;
    end

    // Optional zero-cycle forwarding of the complete registered i0 payload.
    // Data consumers sample the same value on each receiving posedge; raw
    // in_val/in_sg H8 compare inputs and every i0 control edge stay unchanged.
    wire [W-1:0] i0_lv_f;
    wire [W*16-1:0] i0_val_f;
    wire [W*IW-1:0] i0_idx_f;
`ifdef OT_BKQ_I0_OUT_HLAT
    i0_probe_hlk #(.W(W*(17+IW)), .EN(HLAT)) u_fl_i0out (
        .clk(clk), .d({i0_lv, i0_val, i0_idx}), .q({i0_lv_f, i0_val_f, i0_idx_f}));
`else
    assign {i0_lv_f, i0_val_f, i0_idx_f} = {i0_lv, i0_val, i0_idx};
`endif

    // -- ingest: filter (CMP_RETIME, H8) ----------------------------------------------------------------------------
    wire [W-1:0]    i1_s_d, i1_fm_d;
    wire [W*16-1:0] i1_k_d;
    wire [W*EW-1:0] i0_lane;
    generate
        for (gl = 0; gl < W; gl = gl + 1) begin : g_i1
            // i1_k = fkey(i0_val): key' with the -0 override
            wire [15:0] v0  = i0_val_f[16*gl +: 16];
            wire        nz0 = (v0 == 16'h8000);
            assign i1_k_d[16*gl +: 16] = nz0 ? 16'h8000 : kp(v0);
            // compare nibbles on the edge in_val becomes i0_val (as the original CMP_RETIME): key' nibble n uses
            // sign copy n, the bound copy of the lane's 4-lane group; nz lanes take the 0x8000 results
            wire [15:0] vx  = in_val[16*gl +: 16];
`ifdef OT_BKQ_FO8
            wire [15:0] cT  = c_Tc[16*(gl / 2) +: 16];
`else
            wire [15:0] cT  = c_Tc[16*(gl / 4) +: 16];
`endif
            wire [7:0]  cB  = c_Btc[8*(gl / 4) +: 8];
            wire        nzx = (vx == 16'h8000);
            wire [15:0] ik;
            assign ik[15]   = ~in_sg[4*gl + 3];
            assign ik[14:12] = vx[14:12] ^ {3{in_sg[4*gl + 3]}};
            assign ik[11:8] = vx[11:8] ^ {4{in_sg[4*gl + 2]}};
            assign ik[7:4]  = vx[7:4]  ^ {4{in_sg[4*gl + 1]}};
            assign ik[3:0]  = vx[3:0]  ^ {4{in_sg[4*gl + 0]}};
            reg [3:0] cmp_gt, cmp_eq;
            reg hi_match;
            integer nib;
            always @(posedge clk) begin
                for (nib = 0; nib < 4; nib = nib + 1) begin
                    cmp_gt[nib] <= nzx ? ((nib == 3) ? (4'h8 > cT[15:12]) : 1'b0) : (ik[4*nib +: 4] > cT[4*nib +: 4]);
                    cmp_eq[nib] <= nzx ? ((nib == 3) ? (cT[15:12] == 4'h8) : (cT[4*nib +: 4] == 4'h0))
                                       : (ik[4*nib +: 4] == cT[4*nib +: 4]);
                end
                hi_match <= nzx ? (cB == 8'h80) : (ik[15:8] == cB);
            end
            wire ge_lo = cmp_gt[1] || (cmp_eq[1] && (cmp_gt[0] || cmp_eq[0]));
            wire ge = cmp_gt[3] || (cmp_eq[3] && cmp_gt[2]) || (cmp_eq[3] && cmp_eq[2] && ge_lo);
            assign i1_s_d[gl] = i0_lv_f[gl] && ge;
            assign i1_fm_d[gl] = i0_lv_f[gl] && ge && hi_match;
            assign i0_lane[EW*gl +: EW] = {i0_lv_f[gl], i0_val_f[16*gl +: 16], i0_idx_f[IW*gl +: IW]};
        end
    endgenerate
    reg            i1_v, i1_fl;
    reg [W-1:0]    i1_fm;
    reg [W*16-1:0] i1_k;
    reg [W*EW-1:0] i1_p;
    wire i_ing = i0_v && !i0_rp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin i1_v <= 1'b0; i1_fl <= 1'b0; end
        else begin i1_v <= i_ing; i1_fl <= i_ing && i0_last; end
    end
    always @(posedge clk) begin i1_fm <= i1_fm_d; i1_k <= i1_k_d; end

    wire rpd = acc && rp_acc;                    // rp_beat on the next edge
    wire mbd = !rpd && !t2_fl;                   // memory line on the next edge (tq_fl = t3_fl <= t2_fl)
    wire [NG-1:0] rpb_v, memb_v;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_r1
        localparam integer LO = gg * GB;
        localparam integer SW = (MW - LO < GB) ? (MW - LO) : GB;
        (* keep = "true" *) reg rpb, memb;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin rpb <= 1'b0; memb <= 1'b1; end
            else begin rpb <= rpd; memb <= (MUT == 1 && gg == 7) ? 1'b0 : mbd; end
        assign rpb_v[gg] = rpb; assign memb_v[gg] = memb;
        reg [SW-1:0] q;
        wire rpb_l, memb_l;   // HLAT: rpb / memb -> q through one lockup latch
        ot_s81ph_hlk #(.W(2), .EN(HLAT)) u_fl_r1s (.clk(clk), .d({rpb, memb}), .q({rpb_l, memb_l}));
`ifdef OT_BKQ_R1C8
        // Same-cycle H2 control copies: each kept pair owns at most eight payload bits.
        // The original rpb/memb pair still owns the sign sideband (rpb_v/memb_v).
        // Every copy samples the identical rpd/mbd edge and retains the launch-side HLAT.
        for (genvar rs = 0; rs < (SW+7)/8; rs = rs + 1) begin : g_cp8
            localparam integer RL = rs*8;
            localparam integer RW = (SW-RL < 8) ? SW-RL : 8;
            (* keep = "true" *) reg rp8, mb8;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin rp8 <= 1'b0; mb8 <= 1'b1; end
                else begin
`ifdef OT_BKQ_R1C8_MUT
                    rp8 <= (gg == 5 && rs == 2) ? !rpd : rpd;
`else
                    rp8 <= rpd;
`endif
                    mb8 <= (MUT == 1 && gg == 7) ? 1'b0 : mbd;
                end
            wire rp8_l, mb8_l;
            ot_s81ph_hlk #(.W(2), .EN(HLAT)) u_fl_r1s (.clk(clk), .d({rp8, mb8}), .q({rp8_l, mb8_l}));
            always @(posedge clk) q[RL +: RW] <= (i0_lane[LO+RL +: RW] & {RW{rp8_l}}) | (mem_rdata[LO+RL +: RW] & {RW{mb8_l}});
        end
`else
        always @(posedge clk) q <= (i0_lane[LO +: SW] & {SW{rpb_l}}) | (mem_rdata[LO +: SW] & {SW{memb_l}});
`endif
        assign r1_d[LO +: SW] = q;
    end endgenerate

    wire [W*2-1:0] r1sg;
    generate for (gl = 0; gl < W; gl = gl + 1) begin : g_r1sg
        localparam integer SB = EW*gl + IW + 15;
        localparam integer GS = SB / GB;
        localparam integer GO = SB - GS * GB;
        (* keep = "true" *) reg [1:0] r;
        always @(posedge clk) r <= {2{(i0_lane[SB] & rpb_v[GS]) | (mem_rdata[SB] & memb_v[GS])}};
        assign r1sg[2*gl +: 2] = r;
    end endgenerate

 reg[15:0]s_hcr;always @(posedge clk)s_hcr<=i1_s_d;
 assign lane_view=i0_lane;assign replay=r1_d;assign key_view=i1_k;assign sign_view=r1sg;assign mask_view={i1_fm,s_hcr};assign controls={i0_v,i0_rp,i0_last,i1_v,i1_fl};
 for(genvar cg=0;cg<16;cg=cg+1)begin:obs
 assign cmp_view[9*cg+:9]={g_i1[cg].cmp_gt,g_i1[cg].cmp_eq,g_i1[cg].hi_match};end
endmodule


module tb;
 reg clk=0,rst_n=0,acc=0,rp_acc=0,in_last=0,t2_fl=0;always #5 clk=~clk;
 reg[15:0]lv=0;reg[255:0]val=0;reg[319:0]idx=0;reg[63:0]sg=0;reg[127:0]th=0;reg[31:0]bt=0;reg[591:0]mem=0;
 wire[591:0]lane_a,lane_b,r_a,r_b;wire[255:0]key_a,key_b;wire[31:0]sign_a,sign_b,mask_a,mask_b;wire[143:0]cmp_a,cmp_b;wire[4:0]ctl_a,ctl_b;
 i0_ref a(clk,rst_n,acc,rp_acc,in_last,t2_fl,lv,val,idx,sg,th,bt,mem,lane_a,r_a,key_a,sign_a,mask_a,cmp_a,ctl_a);
 i0_new b(clk,rst_n,acc,rp_acc,in_last,t2_fl,lv,val,idx,sg,th,bt,mem,lane_b,r_b,key_b,sign_b,mask_b,cmp_b,ctl_b);
 reg[31:0]seed=32'h9110fa5d;integer i,j,g,checks=0,lane_errors=0,receive_errors=0,compare_errors=0,control_errors=0,resets=0,replays=0,negzero=0;
 function automatic[31:0]rng(input[31:0]x);reg[31:0]t;begin t=x^(x<<13);t=t^(t>>17);rng=t^(t<<5);end endfunction
 always @(posedge clk)begin
  if(i>6 && rst_n)begin
   checks=checks+1;
   // Actual receiving edge, before source NBA updates.
   if(lane_a!==lane_b)lane_errors=lane_errors+1;
   #1;
   if({r_a,key_a,sign_a,mask_a}!=={r_b,key_b,sign_b,mask_b})receive_errors=receive_errors+1;
   if(cmp_a!==cmp_b)compare_errors=compare_errors+1;
   if(ctl_a!==ctl_b)control_errors=control_errors+1;
  end
 end
 initial begin
  for(i=0;i<4096;i=i+1)begin
   @(negedge clk);#1;rst_n=(i>3 && i%251!=0);if(!rst_n)resets=resets+1;
   seed=rng(seed);{acc,rp_acc,in_last,t2_fl}=seed[3:0];if(acc&&rp_acc)replays=replays+1;lv=seed[31:16];
   for(g=0;g<16;g=g+1)begin
    seed=rng(seed);val[16*g+:16]=seed[15:0];
    if(i%32==0)begin val[16*g+:16]=16'h8000;negzero=negzero+1;end
    if(i%32==1)val[16*g+:16]=16'hff80;
    sg[4*g+:4]={4{val[16*g+15]}};
    seed=rng(seed);idx[20*g+:20]=seed[19:0];
   end
   for(j=0;j<128;j=j+1)begin seed=rng(seed);th[j]=seed[0];end
   for(j=0;j<32;j=j+1)begin seed=rng(seed);bt[j]=seed[0];end
   for(j=0;j<592;j=j+1)begin seed=rng(seed);mem[j]=seed[0];end
   @(posedge clk);#2;
  end
  if(checks<4000 || replays==0 || negzero==0 || resets<2)$fatal(1,"missing coverage");
  if(compare_errors!=0 || control_errors!=0)$fatal(1,"untouched H8/control path changed");
`ifdef I0_OUT_STALE_MUT
  if(lane_errors==0 || receive_errors==0)$fatal(1,"new-hop stale mutant survived");
  $display("I0_OUT_HLAT_MUTANT_KILLED checks=%0d lane_errors=%0d receive_errors=%0d H8_errors=%0d control_errors=%0d",checks,lane_errors,receive_errors,compare_errors,control_errors);
`else
  if(lane_errors!=0 || receive_errors!=0)$fatal(1,"forwarding exactness failed");
  $display("I0_OUT_HLAT_EXACT_PASS checks=%0d payload_bits=592 replays=%0d negative_zero_lanes=%0d resets=%0d H8_errors=0 control_errors=0 cycle_delta=0",checks,replays,negzero,resets);
`endif
  $finish;
 end
endmodule
