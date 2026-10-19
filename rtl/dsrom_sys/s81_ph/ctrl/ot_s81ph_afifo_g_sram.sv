`timescale 1ns/1ps
// Opt-in CTRL FIFO storage: real dual-clock SRAM, registered next-head prefetch.
// The Gray pointers/readiness/credit protocol is identical to ot_s81ph_afifo_g.
// A read is enabled only for a head already advertised by the two-stage write
// pointer synchronizer. This excludes speculative empty-slot reads, including
// same-address read/write collisions during the empty->nonempty transition.
// The downstream consumes the previous registered head at the pop edge; SRAM
// captures the next head at that same edge. No extra valid/data edge is added.
`default_nettype none
module ot_s81ph_afifo_g_sram #(
    parameter integer W=32, DEPTH=8, AF=2, G=32
) (
    input wire wclk, wrst_n, w_v,
    input wire [W-1:0] w_d,
    output reg w_rdy, w_credit, w_ovf,
    input wire rclk, rrst_n,
    output wire r_v,
    input wire r_pop,
    input wire [(W+G-1)/G-1:0] r_pop_g,
    output wire [W-1:0] r_d
);
    localparam integer AW=$clog2(DEPTH), PW=AW+1;
    initial begin
        if (W<1 || W>546 || DEPTH<2 || DEPTH>16 || (DEPTH&(DEPTH-1))!=0)
            $fatal(1,"SRAM FIFO requires W1..546 and power-of-two DEPTH2..16");
    end
    function automatic [PW-1:0] g2b(input [PW-1:0] g);
        integer j;
        begin
            g2b[PW-1]=g[PW-1];
            for(j=PW-2;j>=0;j=j-1) g2b[j]=g2b[j+1]^g[j];
        end
    endfunction
    reg [PW-1:0] wbin,wgray,rbin,rgray,cbin;
    (* async_reg="true" *) reg [PW-1:0] rg_w1,rg_w2,wg_r1,wg_r2;
    wire [PW-1:0] rbin_w=g2b(rg_w2);
    wire [PW-1:0] used=wbin-rbin_w;
    wire full=used[AW];
    wire wfire=w_v&&!full;
    wire [PW-1:0] wbin_n=wbin+{{(PW-1){1'b0}},wfire};
    wire [PW-1:0] used_n=wbin_n-rbin_w;
    always @(posedge wclk or negedge wrst_n)
        if(!wrst_n) begin
            wbin<=0; wgray<=0; rg_w1<=0; rg_w2<=0; cbin<=0;
            w_rdy<=0; w_credit<=0; w_ovf<=0;
        end else begin
            wbin<=wbin_n; wgray<=(wbin_n>>1)^wbin_n;
            rg_w1<=rgray; rg_w2<=rg_w1;
            w_rdy<=(DEPTH-32'(used_n))>=AF;
            w_credit<=cbin!=rbin_w;
            if(cbin!=rbin_w) cbin<=cbin+1'b1;
            if(w_v&&full) w_ovf<=1'b1;
        end
    reg empty;
    wire rfire=r_pop&&!empty;
    wire [PW-1:0] rbin_n=rbin+{{(PW-1){1'b0}},rfire};
    wire [PW-1:0] rgray_n=(rbin_n>>1)^rbin_n;
    wire have_next=rgray_n!=wg_r2;
    always @(posedge rclk or negedge rrst_n)
        if(!rrst_n) begin
            rbin<=0; rgray<=0; wg_r1<=0; wg_r2<=0; empty<=1;
        end else begin
            rbin<=rbin_n; rgray<=rgray_n;
            wg_r1<=wgray; wg_r2<=wg_r1; empty<=!have_next;
        end
    assign r_v=!empty;
`ifdef S81CTRL_SRAM_MUT_CURRENT
    wire [3:0] ra={{(4-AW){1'b0}},rbin[AW-1:0]};
`else
    wire [3:0] ra={{(4-AW){1'b0}},rbin_n[AW-1:0]};
`endif
    wire [3:0] wa={{(4-AW){1'b0}},wbin[AW-1:0]};
`ifdef S81CTRL_SRAM_MUT_EMPTYREAD
    wire re=rrst_n;
`else
    wire re=rrst_n&&have_next;
`endif
    wire we=wrst_n&&wfire;
    wire [545:0] q;
    // Unused physical rows/columns are paid capacity, not fabricated data lanes.
    ot_sram_1r1w2c_16x546_m1 u_mem (
        .wclk(wclk),.rclk(rclk),.r_ce_in(re),.r_addr_in(ra),.rd_out(q),
        .w_ce_in(we),.w_addr_in(wa),.wd_in({{(546-W){1'b0}},w_d}),
        .w_mask_in({546{1'b1}}));
    assign r_d=q[W-1:0];
`ifndef SYNTHESIS
    // Both active addresses must remain distinct at either physical clock edge.
    always @(posedge wclk or posedge rclk)
        if(wrst_n&&rrst_n&&re&&we&&ra==wa)
            $fatal(1,"CTRL_SRAM_FIFO_COLLISION address %0d",ra);
    integer k;
    always @(posedge rclk) if(rrst_n) begin
        for(k=0;k<(W+G-1)/G;k=k+1)
            if(r_pop_g[k]!==r_pop) $fatal(1,"CTRL_SRAM_FIFO_POP_COPY");
    end
`endif
endmodule
`default_nettype wire
