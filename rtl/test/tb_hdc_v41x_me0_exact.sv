`timescale 1ns/1ps
// Reduced real L0.router instruction: ME bank 0 from a timed HBM window,
// other seven banks from the independent bank image, exact ISA row check.
module tb_hdc_v41x_me0_exact;
    localparam W=16, G=4, MG=8, AW=24, BAW=17;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, go=0, start=0, release_window=0;
    wire ready, idle, ov, fault;
    wire [7:0] wb_re;
    wire [8*BAW-1:0] wb_addr;
    wire [8*MG*32-1:0] wb_q;
    wire [G-1:0] x_re;
    wire [G*AW-1:0] x_addr;
    reg [G*32-1:0] x_q=0;
    wire [G-1:0] o_we;
    wire [G*AW-1:0] o_addr;
    wire [G*W-1:0] o_mask;
    wire [G*W*32-1:0] o_data;
    reg [31:0] x [0:159];
    reg [31:0] y [0:11];
    reg [31:0] bank [0:36*64-1];
    reg [8*MG*32-1:0] bp0=0, bp1=0;
    reg [MG*32-1:0] m0_p1=0;
    wire [MG*32-1:0] m0_q;
    wire m0_ready, m0_fault;
    wire [3:0] m0_why;
    wire [31:0] sectors;
    integer reads=0, checked=0, cycles=0;
    reg check_v=0;
    reg [255:0] expected_m0=0;
    wire hq_v, hq_rdy;
    wire [23:0] hq_addr;
    wire [3:0] hq_len;
    wire [5:0] hq_tag;
    wire [3:0] hr_v, hr_rdy;
    wire [23:0] hr_tag;
    wire [3:0] hr_beat;
    wire [1023:0] hr_data;
    wire [6:0] fetched;
    wire rd=wb_re[0];
    wire use_rom=$test$plusargs("ROM_ONLY");
    genvar lane;
    generate for (lane=0;lane<8*MG;lane=lane+1) begin : g_wb
        assign wb_q[lane*32+:32]=(!use_rom && lane%8==0) ? m0_p1[(lane/8)*32+:32] : bp1[lane*32+:32];
    end endgenerate

    ot_hdc_v41x_me_adapt #(.W(W),.G(G),.MG(MG),.BAW(BAW)) u_me (
        .clk(clk),.rst_n(rst_n),.go(go),.ready(ready),.idle(idle),
        .i_nout(16'd12),.i_tiles(16'd1),.i_k(16'd40),
        .i_wbase(24'd10100),.i_xbase(24'd0),.i_xjs(24'd0),
        .i_split(2'd2),.i_round(1'b1),.i_obase(24'd1174),
        .i_ots(24'd8),.i_ojs(24'd1),.i_oen(1'b1),.i_amax(1'b0),
        .i_m(3'd1),.i_xps(24'd0),.i_ops(24'd0),.cfg_xs(4'd0),
        .wb_re(wb_re),.wb_addr(wb_addr),.wb_q(wb_q),
        .x_re(x_re),.x_addr(x_addr),.x_q(x_q),
        .ov(ov),.o_we(o_we),.o_addr(o_addr),.o_mask(o_mask),.o_data(o_data),
        .am_idx(),.am_val(),.am_any(),.fault(fault));
    ot_hdc_v41x_weight_window #(.WB(256),.SB(256),.WORDS(64),.AW(BAW),.HAW(24),.NPC(4)) u_win (
        .clk(clk),.rst_n(rst_n),.start(start),.release_window(release_window),
        .rom_base(BAW'(10100)),.hbm_base(24'd0),.nwords(7'd36),.ready(m0_ready),
        .hq_v(hq_v),.hq_rdy(hq_rdy),.hq_addr(hq_addr),.hq_len(hq_len),.hq_tag(hq_tag),
        .hr_v(hr_v),.hr_rdy(hr_rdy),.hr_tag(hr_tag),.hr_beat(hr_beat),.hr_data(hr_data),
        .rom_re(rd),.rom_addr(wb_addr[0+:BAW]),.rom_q(m0_q),
        .fault(m0_fault),.fault_why(m0_why),.fetched_words(fetched),.received_sectors(sectors));
    ot_hdc_hbm_model #(.NPC(4),.AW(24),.DW(256),.MEM_WORDS(64),
        .TAGW(6),.LENW(4),.BEATW(1),.QD(32),.RQD(16),.CLK_PS(1000),.PC_RDY(0)) u_hbm (
        .clk(clk),.rst_n(rst_n),.req_v(hq_v),.req_rdy(hq_rdy),.pc_room(),
        .req_we(1'b0),.req_addr(hq_addr),.req_len(hq_len),.req_tag(hq_tag),.req_wdata(256'd0),
        .rsp_v(hr_v),.rsp_rdy(hr_rdy),.rsp_tag(hr_tag),.rsp_beat(hr_beat),.rsp_data(hr_data));
    initial begin
        string dir;
        if (!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR missing");
        $readmemh({dir,"/x.hex"},x);
        $readmemh({dir,"/y.hex"},y);
        $readmemh({dir,"/mbank_slice.hex"},bank);
        for (integer a=0;a<36;a++)
            for (integer u=0;u<MG;u++)
                u_hbm.mem[a][u*32+:32]=bank[a*64+8*u];
        repeat (5) @(negedge clk);
        rst_n=1;
        @(negedge clk); start=1;
        @(negedge clk); start=0;
        wait (m0_ready);
        @(negedge clk); go=1;
        @(negedge clk); go=0;
        wait (idle && checked==12);
        @(negedge clk);
        if (fault || m0_fault || checked!=12 || reads==0 || sectors!=36)
            $fatal(1,"ME0_FAIL checked=%0d reads=%0d sectors=%0d fault=%0d m0_fault=%0d why=%0d",
                   checked,reads,sectors,fault,m0_fault,m0_why);
        $display("ME0_PASS exact_rows=%0d rom_reads=%0d hbm_sectors=%0d cycles=%0d",checked,reads,sectors,cycles);
        $finish;
    end
    always @(posedge clk) if (rst_n) begin
        if (check_v && m0_q!==expected_m0)
            $fatal(1,"weight read mismatch addr=%0d got=%h expected=%h",wb_addr[0+:BAW],m0_q,expected_m0);
        check_v<=rd;
        if (rd) for (integer u=0;u<MG;u++)
            expected_m0[u*32+:32]<=bank[(wb_addr[0+:BAW]-10100)*64+8*u];
        cycles<=cycles+1;
        if (cycles>200000) $fatal(1,"ME0 timeout checked=%0d",checked);
        for (integer p=0;p<G;p++) if (x_re[p]) begin
            if (x_addr[p*AW+:AW]>=160) $fatal(1,"x address %0d",x_addr[p*AW+:AW]);
            x_q[p*32+:32]<=x[x_addr[p*AW+:AW]];
        end
        for (integer b=0;b<8;b++) if (wb_re[b]) begin
            if (wb_addr[b*BAW+:BAW]<10100 || wb_addr[b*BAW+:BAW]>=10136)
                $fatal(1,"weight address %0d",wb_addr[b*BAW+:BAW]);
            for (integer u=0;u<MG;u++)
                bp0[(8*u+b)*32+:32]<=bank[(wb_addr[b*BAW+:BAW]-10100)*64+8*u+b];
        end
        bp1<=bp0;
        m0_p1<=m0_q;
        if (rd) reads<=reads+1;
        if (ov) for (integer p=0;p<G;p++) if (o_we[p]) begin
            if (o_addr[p*AW+:AW]!=1174) $fatal(1,"output address %0d",o_addr[p*AW+:AW]);
            for (integer l=0;l<W;l++) if (o_mask[p*W+l]) begin
                if (l>=12 || o_data[(p*W+l)*32+:32]!==y[l])
                    $fatal(1,"row %0d got=%h expected=%h",l,o_data[(p*W+l)*32+:32],y[l]);
                checked=checked+1;
            end
        end
    end
endmodule
