`timescale 1ns/1ps
// Full-shape address and activation-depth boundary, zero-weight arithmetic.
module tb_hdc_v41x_fullshape_depths;
    localparam AW=30, NW=21, BAW=18, HBAW=16, G=4, W=16, MG=8;
    reg clk=0;
    always #1 clk=~clk;
    reg rst_n=0, me_go=0, he_go=0;
    wire me_ready, me_idle, me_ov, me_fault;
    wire [7:0] mb_re, hb_re;
    wire [8*BAW-1:0] mb_addr;
    wire [8*HBAW-1:0] hb_addr;
    reg [8*MG*32-1:0] mb_q=0;
    reg [8*8*32-1:0] hb_q=0;
    wire [G-1:0] mx_re, mw_we;
    wire [G*AW-1:0] mx_addr, mw_addr;
    wire [G*W-1:0] mw_mask;
    wire [G*W*32-1:0] mw_data;
    reg [G*32-1:0] mx_q={G{32'h3f800000}};
    wire [7:0] hx_re;
    wire [8*AW-1:0] hx_addr;
    reg [8*32-1:0] hx_q={8{32'h3f800000}};
    wire he_ready, he_idle, he_fault, hw_we;
    wire [AW-1:0] hw_addr;
    wire [31:0] hw_mask;
    wire [1023:0] hw_data;
    integer cycles=0, me_reads=0, he_reads=0, me_rows=0, he_rows=0;
    integer max_me_addr=0, max_he_addr=0;

    ot_hdc_v41x_me_adapt #(.W(W),.G(G),.MG(MG),.AW(AW),.NW(NW),.BAW(BAW),.KMAX(5120)) me (
        .clk(clk),.rst_n(rst_n),.go(me_go),.ready(me_ready),.idle(me_idle),
        .i_nout(21'd1),.i_tiles(21'd1),.i_k(21'd5120),
        .i_wbase(30'd131100),.i_xbase(30'd0),.i_xjs(30'd0),
        .i_split(2'd0),.i_round(1'b1),.i_obase(30'd0),
        .i_ots(30'd1),.i_ojs(30'd1),.i_oen(1'b1),.i_amax(1'b0),
        .i_m(3'd1),.i_xps(30'd0),.i_ops(30'd0),.cfg_xs(4'd0),
        .wb_re(mb_re),.wb_addr(mb_addr),.wb_q(mb_q),
        .x_re(mx_re),.x_addr(mx_addr),.x_q(mx_q),
        .ov(me_ov),.o_we(mw_we),.o_addr(mw_addr),.o_mask(mw_mask),.o_data(mw_data),
        .am_idx(),.am_val(),.am_any(),.fault(me_fault));
    ot_hdc_v41x_he_adapt #(.HW(8),.BAW(HBAW),.AW(AW),.NW(NW),.KCMAX(2560),.PMAX(2)) he (
        .clk(clk),.rst_n(rst_n),.go(he_go),.ready(he_ready),.idle(he_idle),
        .i_nout(21'd1),.i_k(21'd2560),.i_wbase(30'd10000),.i_xbase(30'd0),
        .i_obase(30'd0),.i_m(3'd1),.i_xps(30'd0),.i_ops(30'd0),
        .w_re(hb_re),.w_addr(hb_addr),.w_data(hb_q),
        .x_re(hx_re),.x_addr(hx_addr),.x_q(hx_q),
        .o_we(hw_we),.o_addr(hw_addr),.o_mask(hw_mask),.o_data(hw_data),.fault(he_fault));

    initial begin
        repeat (5) @(negedge clk);
        rst_n=1;
        @(negedge clk); me_go=1; he_go=1;
        @(negedge clk); me_go=0; he_go=0;
    end
    always @(posedge clk) if (rst_n) begin
        cycles <= cycles+1;
        if (cycles > 100000) $fatal(1,"full-depth timeout me=%0d he=%0d",me_rows,he_rows);
        if (|mx_re) mx_q <= {G{32'h3f800000}};
        if (|hx_re) hx_q <= {8{32'h3f800000}};
        if (|mb_re) mb_q <= '0;
        if (|hb_re) hb_q <= '0;
        for (integer b=0;b<8;b++) begin
            if (mb_re[b]) begin
                if (mb_addr[b*BAW+:BAW] < 18'd131100 || mb_addr[b*BAW+:BAW] >= 18'd131740)
                    $fatal(1,"ME bank address %0d",mb_addr[b*BAW+:BAW]);
                if (mb_addr[b*BAW+:BAW] > max_me_addr) max_me_addr=mb_addr[b*BAW+:BAW];
                me_reads++;
            end
            if (hb_re[b]) begin
                if (hb_addr[b*HBAW+:HBAW] < 16'd10000 || hb_addr[b*HBAW+:HBAW] >= 16'd10320)
                    $fatal(1,"HE bank address %0d",hb_addr[b*HBAW+:HBAW]);
                if (hb_addr[b*HBAW+:HBAW] > max_he_addr) max_he_addr=hb_addr[b*HBAW+:HBAW];
                he_reads++;
            end
        end
        for (integer p=0;p<G;p++) if (mw_we[p])
            for (integer l=0;l<W;l++) if (mw_mask[p*W+l]) begin
                if (mw_addr[p*AW+:AW] !== 0 || mw_data[(p*W+l)*32+:32] !== 0)
                    $fatal(1,"ME zero result mismatch");
                me_rows++;
            end
        if (hw_we) begin
            if (hw_addr !== 0 || hw_mask !== 1 || hw_data[31:0] !== 0)
                $fatal(1,"HE zero result mismatch");
            he_rows++;
        end
        if (me_idle && he_idle && me_rows==1 && he_rows==1) begin
            if (me_fault || he_fault || me_reads==0 || he_reads==0 ||
                max_me_addr < 131072 || max_he_addr < 10000)
                $fatal(1,"full-depth coverage/fault failure");
            $display("PASS fullshape depths me_k=5120 he_k=2560 me_reads=%0d he_reads=%0d max_me_addr=%0d max_he_addr=%0d cycles=%0d",
                     me_reads,he_reads,max_me_addr,max_he_addr,cycles);
            $finish;
        end
    end
endmodule
