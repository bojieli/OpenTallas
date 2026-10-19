`timescale 1ns/1ps
// Namespace-only copy of gated reference ff0368257. Default Qwen lanes untouched.
// G180: clocks physically pulse once every four parent cycles; clocks below
// must be declared from these actual ICG pins, never from a fictitious phase clock.
(* keep_hierarchy = "yes" *)
module ot_coll_b4_bank_gate (input wire ck, en, output wire gclk);
    ot_hdc_cg u_cg (.clk(ck), .en(en), .gclk(gclk));
endmodule

(* keep_hierarchy = "yes" *)
module ot_coll_b4_gated_region #(parameter integer W = 16) (
    input wire [3:0] wclk, rclk,
    input wire ck, rs, rs_landed, warm, ready,
    input wire [3:0] readsel,
    input wire [W-1:0] i,
    output reg [W-1:0] o
);
    reg [W-1:0] b0,b1,b2,b3;
    reg [W-1:0] r0,r1,r2,r3;
    always @(posedge wclk[0]) b0 <= i;
    always @(posedge wclk[1]) b1 <= i;
    always @(posedge wclk[2]) b2 <= i;
    always @(posedge wclk[3]) b3 <= i;
    // Complementary capture avoids an inverter on the inter-root bank path;
    // the receiver-root mux restores the data representation locally.
    always @(posedge rclk[0]) r0 <= ~b0;
    always @(posedge rclk[1]) r1 <= ~b1;
    always @(posedge rclk[2]) r2 <= ~b2;
    always @(posedge rclk[3]) r3 <= ~b3;
    (* keep = "true", dont_touch = "true" *) reg [3:0] sel_q;
    reg reset_face;
    always @(posedge ck or negedge rs_landed)
        if (!rs_landed) reset_face <= 1'b0; else reset_face <= 1'b1;
    // These four local kept flops each drive <=16 data loads. warm/ready each
    // drive one local cone per kept region, rather than a single wide fanout.
    always @(posedge ck) sel_q <= readsel & {4{warm && ready}};
`ifdef OT_QFD_LAND_MUT_NAIVE
    always @(posedge ck) o <= i;
`else
    always @(posedge ck)
        o <= !reset_face ? {W{1'b0}} :
              (({W{sel_q[0]}} & ~r0) | ({W{sel_q[1]}} & ~r1)
             | ({W{sel_q[2]}} & ~r2) | ({W{sel_q[3]}} & ~r3));
`endif
endmodule

module ot_coll_b4_land_gated #(
    parameter integer W=180, D=4, FIRST=0, AW=2
) (
    input wire ckf, ea, input wire [W-1:0] i,
    input wire ck, rs, input wire [AW:0] k,
    output wire [W-1:0] o, output reg fault
);
    wire wck, we;
    generate if (FIRST != 0) begin : g_hop0
        reg en_q;
`ifdef OT_QFD_LAND_MUT_ENCOMB
        always @(*) en_q=ea;
`else
        always @(posedge ckf or negedge ea)
            if (!ea) en_q<=1'b0; else en_q<=1'b1;
`endif
        ot_qfd_fwd0 u_fwd0 (.ck(ckf),.en(en_q),.cko(wck));
        assign we=en_q;
    end else begin : g_lane
        assign wck=ckf; assign we=ea;
    end endgenerate
    reg meta_we;
    always @(posedge wck or negedge we)
        if (!we) meta_we<=1'b0; else meta_we<=1'b1;
    reg rs0,rs1;
    always @(posedge ck or negedge rs)
        if (!rs) begin rs0<=1'b0;rs1<=1'b0;end
        else begin rs0<=1'b1;rs1<=rs0;end
    reg [2:0] k_q, wc,rc;
    always @(posedge ck) k_q<=k;
    reg [3:0] wslot_q;
    wire [3:0] wslot={wslot_q[3:1],~wslot_q[0]};
    always @(posedge wck or negedge meta_we)
        if (!meta_we) begin wc<=3'b0;wslot_q<=4'b0;end
        else begin
            wc<=wc+1'b1;
`ifdef OT_QFD_LAND_MUT_WSEL
            wslot_q<={wslot[0],wslot[3:2],~wslot[1]};
`else
            wslot_q<={wslot[2:0],~wslot[3]};
`endif
        end
    // Fixed startup qualification, not occupancy/credit flow control: after
    // exactly four writes all slots are initialized. The two receiving reset
    // stages release once, and no normal-operation data can stall this tile.
    reg [2:0] fill;
    reg full_w;
    always @(posedge wck or negedge meta_we)
        if (!meta_we) begin fill<=3'b0;full_w<=1'b0;end
        else if (!full_w) begin
            fill<=fill+1'b1;
            if (fill==3'd3) full_w<=1'b1;
        end
    wire ready_reset_n=rs1 && full_w;
    reg ready0,ready1;
    always @(posedge ck or negedge ready_reset_n)
        if (!ready_reset_n) begin ready0<=1'b0;ready1<=1'b0;end
        else begin ready0<=1'b1;ready1<=ready0;end
    reg warm;
    reg [3:0] readsel;
    wire [2:0] seed_exp=-k_q;
    wire [2:0] next_exp=rc+1'b1-k_q;
    always @(posedge ck)
        if (!rs1) readsel<=4'b0001<<seed_exp[1:0];
`ifdef OT_QFD_LAND_MUT_RSEL
        else readsel<=4'b0001<<(next_exp[1:0]+2'd1);
`else
        else readsel<=4'b0001<<next_exp[1:0];
`endif
    always @(posedge ck or negedge rs1)
        if (!rs1) begin rc<=3'b0;warm<=1'b0;end
        else begin rc<=rc+1'b1;if (rc==k_q-1'b1) warm<=1'b1;end
    wire read_run=warm && ready1;
    wire [3:0] wbank_clk,rbank_clk;
    ot_coll_b4_bank_gate u_wbank0(.ck(wck),.en(meta_we&&wslot[0]),.gclk(wbank_clk[0]));
    ot_coll_b4_bank_gate u_wbank1(.ck(wck),.en(meta_we&&wslot[1]),.gclk(wbank_clk[1]));
    ot_coll_b4_bank_gate u_wbank2(.ck(wck),.en(meta_we&&wslot[2]),.gclk(wbank_clk[2]));
    ot_coll_b4_bank_gate u_wbank3(.ck(wck),.en(meta_we&&wslot[3]),.gclk(wbank_clk[3]));
    ot_coll_b4_bank_gate u_rbank0(.ck(ck),.en(read_run&&readsel[0]),.gclk(rbank_clk[0]));
    ot_coll_b4_bank_gate u_rbank1(.ck(ck),.en(read_run&&readsel[1]),.gclk(rbank_clk[1]));
    ot_coll_b4_bank_gate u_rbank2(.ck(ck),.en(read_run&&readsel[2]),.gclk(rbank_clk[2]));
    ot_coll_b4_bank_gate u_rbank3(.ck(ck),.en(read_run&&readsel[3]),.gclk(rbank_clk[3]));
    genvar c;
    generate for(c=0;c<(W+15)/16;c=c+1) begin : g_region
        localparam integer LO=c*16,N=(W-LO<16)?W-LO:16;
        ot_coll_b4_gated_region #(.W(N)) u_region (
            .wclk(wbank_clk),.rclk(rbank_clk),.ck(ck),.rs(rs),.rs_landed(rs1),
            .warm(warm),.ready(ready1),.readsel(readsel),.i(i[LO+:N]),.o(o[LO+:N]));
    end endgenerate
    // All metadata crosses through the same physically gated bank clocks as
    // its payload. Compare on the following receiver edge, aligned with o.
    reg [2:0] ep0,ep1,ep2,ep3,er0,er1,er2,er3;
    always @(posedge wbank_clk[0]) ep0<=wc;
    always @(posedge wbank_clk[1]) ep1<=wc;
    always @(posedge wbank_clk[2]) ep2<=wc;
    always @(posedge wbank_clk[3]) ep3<=wc;
    always @(posedge rbank_clk[0]) er0<=~ep0;
    always @(posedge rbank_clk[1]) er1<=~ep1;
    always @(posedge rbank_clk[2]) er2<=~ep2;
    always @(posedge rbank_clk[3]) er3<=~ep3;
    reg [2:0] exp_d;
    reg [1:0] sel_d;
    reg run_d;
`ifdef OT_QFD_LAND_MUT_SEL
    wire [2:0] expected=rc-k_q+1'b1;
`else
    wire [2:0] expected=rc-k_q;
`endif
    always @(posedge ck) begin exp_d<=expected;sel_d<=expected[1:0];run_d<=read_run;end
    wire [2:0] got=(sel_d==0)?er0:(sel_d==1)?er1:(sel_d==2)?er2:er3;
    always @(posedge ck or negedge rs1)
        if (!rs1) fault<=1'b0;
        else if (run_d && got!=~exp_d) fault<=1'b1;
`ifndef SYNTHESIS
    initial if (D!=4 || AW!=2 || W>180) $fatal(1,"gated landing: D4,AW2,W<=180 required");
`endif
endmodule
