`timescale 1ns/1ps
`default_nettype none
// COL8: hard two-head regions. Arithmetic/query/head delays are copied from COL7;
// only reset online release is one edge later. Four RID masters preserve global
// head-delay offsets. Query N and key S replace the failed all-N ingress mesh.
`ifndef OT_IDX_FAN32_SAFE
`ifdef SYNTHESIS
`define OT_IDX_FAN32_SAFE 1
`else
`define OT_IDX_FAN32_SAFE 0
`endif
`endif
module ot_hidx_score_pair8 #(parameter integer RID=0)(
 input wire clk,rst_n,qv_b,input wire [567:0] q_b,input wire [543:0] key,
 input wire [15:0] hid,input wire [31:0] cs_in,input wire cf_in,
 output wire [31:0] cs_out,output wire cf_out,output wire prdy);
 localparam integer NB=4,FPL=7,FML=5,QL=5,KW=544,QW=568,SW=560,QG=14,NQG=40;
 wire [31:0] cs[0:2]; wire cf[0:2]; genvar hh,bb,k;
 assign cs[0]=cs_in; assign cf[0]=cf_in;
        localparam integer NRS = 1 + 2 * NB;
        wire [NRS-1:0] srr; wire rs = srr[0];
        ot_rst_relay_l #(.REGIONS(NRS),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rl_pair
            (.clk(clk),.rst_n_in(rst_n),.rst_n(srr));
        reg rn_p, onl;
        always @(posedge clk) rn_p <= rs;
        always @(posedge clk or negedge rs) if (!rs) onl <= 1'b0; else onl <= rs && rn_p;
        assign prdy = onl;
        // region pin registers, kept per region (equal D across the 4 regions: opt_merge would fold them into one)
        // HBM-IDXSQ8 native32 (col7 census: key_p 1,408 drivers <= 74 loads): the key pin registers are per HEAD (key_h) plus
        // a per-head copy of the code bits (key_h2) for the dot's shift fields; same edge, each key pin drives 16 flops.
        (* keep *) reg qv_p; (* keep *) reg [QW-1:0] q_p;
        always @(posedge clk) begin qv_p <= qv_b && rn_p; q_p <= q_b; end
        wire [7:0] qh_p = q_p[QW-1 -: 8];
        for (hh = 0; hh < 2; hh = hh + 1) begin : g_h
            localparam integer H = 2 * RID + hh;
            // two kept head-id copies: each compare feeds 20 of the 40 enable copies (one compare -> 40 loads otherwise)
            (* keep *) reg [7:0] hid_pa; (* keep *) reg [7:0] hid_pb;
            always @(posedge clk) begin hid_pa <= hid[8*hh +: 8]; hid_pb <= hid[8*hh +: 8]; end
            // ---- (a) query store: own head written one edge after the compare; 40 kept enable copies
            wire q_eqa = qv_p && rn_p && (qh_p == hid_pa);
            wire q_eqb = qv_p && rn_p && (qh_p == hid_pb);
            (* keep *) reg [KW-1:0] key_h; (* keep *) reg [NB*128-1:0] key_h2;
            always @(posedge clk) begin key_h <= key; key_h2 <= key[NB*128-1:0]; end
            reg [SW-1:0] q2; reg [SW-1:0] qst; reg [NB*128-1:0] qst2;   // qst2: the code bits again (dot shift fields)
            always @(posedge clk) q2 <= q_p[QW-9:0];
            for (k = 0; k < NQG; k = k + 1) begin : g_we
                (* keep *) reg we;
                always @(posedge clk) we <= (k < NQG / 2) ? q_eqa : q_eqb;
                always @(posedge clk) if (we) qst[k*QG +: QG] <= q2[k*QG +: QG];
                if (k*QG + QG > 48) begin : g_c2                  // groups holding code bits (qst[559:48])
                    localparam integer L2 = (k*QG < 48) ? 48 : k*QG;
                    always @(posedge clk) if (we) qst2[k*QG + QG - 1 - 48 : L2 - 48] <= q2[k*QG + QG - 1 : L2];
                end
            end
            wire [NB*128-1:0] qc = qst[SW-1 -: NB*128];
            wire [NB*8-1:0]   qs = qst[47:16];
            wire [15:0]       qw = qst[15:0];
            // ---- (c) block dots now, partials delayed FPL*(bb-1)
            wire [NB*32-1:0] acc; wire [NB-1:0] afault;
            for (bb = 0; bb < NB; bb = bb + 1) begin : g_blk
                localparam integer DS = (bb == 0) ? 0 : FPL * (bb - 1);
                wire [31:0] bv0; wire bo0; wire [31:0] bv; wire bo;
                (* keep_hierarchy *) ot_hdc_v41x_q4dot_n #(.QL(QL)) u_d (.clk(clk), .a(qc[bb*128 +: 128]), .b(key_h[128*bb +: 128]),
                    .a2(qst2[bb*128 +: 128]), .b2(key_h2[128*bb +: 128]),
                    .ua(qs[bb*8 +: 8]), .ub(key_h[NB*128 + 8*bb +: 8]), .y(bv0), .ovf(bo0));
                ot_hdc_delay_rf32 #(.W(33), .D(DS)) u_bd (.clk(clk), .d({bo0, bv0}), .q({bo, bv}));
                if (bb == 0) begin : g_first
                    assign acc[31:0] = bv; assign afault[0] = bo;
                end else begin : g_add
                    wire [1:0] err; wire vo_unused; wire pf, bo_d;
                    ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(clk), .rst_n(1'b1), .d(afault[bb-1]), .q(pf));
                    (* keep_hierarchy *) ot_hdc_fp32_add_lat_fan32 #(.LAT(FPL), .DRST(0), .SAFE_DIST(`OT_IDX_FAN32_SAFE)) u_a (
                        .clk(clk), .rst_n(srr[1 + hh * NB + bb]), .valid_in(1'b1),
                        .a(acc[32*(bb-1) +: 32]), .b(bv), .y(acc[32*bb +: 32]), .err(err), .valid_out(vo_unused));
                    ot_hdc_delay #(.W(1), .D(FPL)) u_bf (.clk(clk), .rst_n(1'b1), .d(bo), .q(bo_d));
                    assign afault[bb] = pf || bo_d || (err != 2'd0);
                end
            end
            wire [15:0] sc16; wire sco;
            ot_hdc_v41x_bf16 u_sb (.x(acc[32*(NB-1) +: 32]), .y(sc16), .ovf(sco));
            reg [15:0] rsc; reg rscf;
            always @(posedge clk) begin rsc <= sc16; rscf <= afault[NB-1] || sco; end
            wire [15:0] tm0; wire tmo, rscf_d;
            (* keep_hierarchy *) ot_hdc_v41x_bmul_n u_m (.clk(clk), .a(rsc), .w(qw), .y(tm0), .ovf(tmo));
            ot_hdc_delay #(.W(1), .D(FML)) u_tf (.clk(clk), .rst_n(1'b1), .d(rscf), .q(rscf_d));
            // ---- (b) the head term waits 9h edges
            wire [15:0] tm; wire tf;
            ot_hdc_delay_rf32 #(.W(17), .D((FPL + 2) * H)) u_td (.clk(clk), .d({rscf_d || tmo, tm0}), .q({tf, tm}));
            reg [31:0] csi_p; reg cfi_p; reg [31:0] cs_o; reg cf_o;
`ifdef OT_IDX_RT_MUT_SEAM
            if (H == 2) begin : g_mseam          // mutant: the region seam between regions 0 and 1 one edge late
                reg [31:0] cs_x; reg cf_x;
                always @(posedge clk) begin cs_x <= cs[hh]; cf_x <= cf[hh]; csi_p <= cs_x; cfi_p <= cf_x; end
            end else begin : g_nseam
                always @(posedge clk) begin csi_p <= cs[hh]; cfi_p <= cf[hh]; end
            end
`else
            always @(posedge clk) begin csi_p <= cs[hh]; cfi_p <= cf[hh]; end
`endif
            if (H == 0) begin : g_seed
                wire [32:0] seed_d;
                ot_hdc_delay_rf32 #(.W(33), .D(FPL)) u_sd (.clk(clk),
                    .d({tf, (tm[14:0] == 15'd0) ? 32'd0 : {tm, 16'd0}}), .q(seed_d));
                always @(posedge clk) begin cs_o <= seed_d[31:0]; cf_o <= seed_d[32]; end
            end else begin : g_sum
                wire [1:0] err; wire vo_unused; wire [31:0] sum; wire pf;
                // HBM-ELEM13/IDX 10-21 native32: the 16 zero pad bits of b were ONE hilomap -singleton TIELO
                // feeding 172 dont_touch native-adder pins (repair_tie_fanout skips dont_touch loads at
                // floorplan). One kept TIELO per pad bit -> <= 6 loads each. Logic value unchanged (0).
                wire [15:0] zpad;
`ifdef SYNTHESIS
                if (`OT_IDX_FAN32_SAFE != 0) begin : g_zt
                    for (k = 0; k < 16; k = k + 1) begin : g_z
                        (* keep = 1, dont_touch = 1 *) TIELOx1_ASAP7_75t_R u_tlo (.L(zpad[k]));
                    end
                end else begin : g_zc
                    assign zpad = 16'd0;
                end
`else
                assign zpad = 16'd0;
`endif
                (* keep_hierarchy *) ot_hdc_fp32_add_lat_fan32 #(.LAT(FPL), .DRST(0), .SAFE_DIST(`OT_IDX_FAN32_SAFE)) u_a (
                    .clk(clk), .rst_n(srr[1 + hh * NB]), .valid_in(1'b1),
                    .a(csi_p), .b({tm, zpad}), .y(sum), .err(err), .valid_out(vo_unused));
                ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(clk), .rst_n(1'b1), .d(cfi_p || tf), .q(pf));
                always @(posedge clk) begin cs_o <= sum; cf_o <= pf || (err != 2'd0); end
            end
            assign cs[hh + 1] = cs_o; assign cf[hh + 1] = cf_o;
        end
 assign cs_out=cs[2];assign cf_out=cf[2];
endmodule
module ot_hidx_score_pair8_r0(input wire clk,rst_n,qv_b,input wire [567:0] q_b,
 input wire [543:0] key,input wire [15:0] hid,
 output wire [31:0] cs_out,output wire cf_out,output wire prdy);
 ot_hidx_score_pair8 #(.RID(0)) u_pair(.clk(clk),.rst_n(rst_n),.qv_b(qv_b),.q_b(q_b),.key(key),.hid(hid),
 .cs_in(32'd0),.cf_in(1'b0),.cs_out(cs_out),.cf_out(cf_out),.prdy(prdy));
endmodule
module ot_hidx_score_pair8_r1(input wire clk,rst_n,qv_b,input wire [567:0] q_b,
 input wire [543:0] key,input wire [15:0] hid,input wire [31:0] cs_in,input wire cf_in,
 output wire [31:0] cs_out,output wire cf_out,output wire prdy);
 ot_hidx_score_pair8 #(.RID(1)) u_pair(.clk(clk),.rst_n(rst_n),.qv_b(qv_b),.q_b(q_b),.key(key),.hid(hid),
 .cs_in(cs_in),.cf_in(cf_in),.cs_out(cs_out),.cf_out(cf_out),.prdy(prdy));
endmodule
module ot_hidx_score_pair8_r2(input wire clk,rst_n,qv_b,input wire [567:0] q_b,
 input wire [543:0] key,input wire [15:0] hid,input wire [31:0] cs_in,input wire cf_in,
 output wire [31:0] cs_out,output wire cf_out,output wire prdy);
 ot_hidx_score_pair8 #(.RID(2)) u_pair(.clk(clk),.rst_n(rst_n),.qv_b(qv_b),.q_b(q_b),.key(key),.hid(hid),
 .cs_in(cs_in),.cf_in(cf_in),.cs_out(cs_out),.cf_out(cf_out),.prdy(prdy));
endmodule
module ot_hidx_score_pair8_r3(input wire clk,rst_n,qv_b,input wire [567:0] q_b,
 input wire [543:0] key,input wire [15:0] hid,input wire [31:0] cs_in,input wire cf_in,
 output wire [31:0] cs_out,output wire cf_out,output wire prdy);
 ot_hidx_score_pair8 #(.RID(3)) u_pair(.clk(clk),.rst_n(rst_n),.qv_b(qv_b),.q_b(q_b),.key(key),.hid(hid),
 .cs_in(cs_in),.cf_in(cf_in),.cs_out(cs_out),.cf_out(cf_out),.prdy(prdy));
endmodule
module ot_hidx_score_col8(input wire clk,rst_n,qv_b,input wire [567:0] q_b,
 input wire [543:0] key,input wire [63:0] hid,output wire [31:0] cs_out,
 output wire cf_out,output wire [3:0] prdy);
 // Two face synchronizers, then pair-local two-stage synchronizers and regional
 // copies. Boot +1 vs COL7; reset assertion is asynchronous throughout.
 (* async_reg="true",keep="true",dont_touch="true" *) reg [1:0] sync_q;
 always @(posedge clk or negedge rst_n) if(!rst_n)sync_q<=0;else sync_q<={sync_q[0],1'b1};
 wire [31:0] cs[0:4];wire cf[0:4];assign cs[0]=0;assign cf[0]=0;
 ot_hidx_score_pair8_r0 u_pair0(.clk(clk),.rst_n(sync_q[1]),.qv_b(qv_b),.q_b(q_b),.key(key),
 .hid(hid[0+:16]),.cs_out(cs[1]),.cf_out(cf[1]),.prdy(prdy[0]));
 ot_hidx_score_pair8_r1 u_pair1(.clk(clk),.rst_n(sync_q[1]),.qv_b(qv_b),.q_b(q_b),.key(key),
 .hid(hid[16+:16]),.cs_in(cs[1]),.cf_in(cf[1]),.cs_out(cs[2]),.cf_out(cf[2]),.prdy(prdy[1]));
 ot_hidx_score_pair8_r2 u_pair2(.clk(clk),.rst_n(sync_q[1]),.qv_b(qv_b),.q_b(q_b),.key(key),
 .hid(hid[32+:16]),.cs_in(cs[2]),.cf_in(cf[2]),.cs_out(cs[3]),.cf_out(cf[3]),.prdy(prdy[2]));
 ot_hidx_score_pair8_r3 u_pair3(.clk(clk),.rst_n(sync_q[1]),.qv_b(qv_b),.q_b(q_b),.key(key),
 .hid(hid[48+:16]),.cs_in(cs[3]),.cf_in(cf[3]),.cs_out(cs[4]),.cf_out(cf[4]),.prdy(prdy[3]));
assign cs_out=cs[4];assign cf_out=cf[4];
endmodule
`default_nettype wire
