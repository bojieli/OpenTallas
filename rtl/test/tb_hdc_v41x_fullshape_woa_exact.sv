`timescale 1ns/1ps
// Two TP4 wo_a local groups against the source-pinned rank-0 ROM image.
// The runner supplies checkpoint ACC and raw FP32 pre-BF16 ZA as hex words.
module tb_hdc_v41x_fullshape_woa_exact #(
    parameter integer XBANK=0,
    parameter integer RL=2,
    parameter integer SHARED=0
);
    localparam W=16, G=4, MG=8, AW=30, BAW=18;
    localparam BASE0=7680, BASE1=73216, IMAGE_BYTES=33554432;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, go=0;
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
    reg [31:0] x [0:8191];
    reg [31:0] y [0:2047];
    reg [7:0] image [0:IMAGE_BYTES-1];
    reg [8*MG*32-1:0] bp0=0, bp1=0, bp2=0, bp3=0;
    wire shared_wr_v;
    wire [0:0] shared_wr_p;
    wire [12:0] shared_wr_e;
    wire [G*16-1:0] shared_wr_d;
    wire [7:0] shared_rq_v;
    wire [8*14-1:0] shared_rq_q;
    wire [8*4-1:0] shared_rq_plg;
    wire [8*MG*16-1:0] shared_rd_x;
    reg [8*MG*16-1:0] shared_xr0=0;
    reg pre_in_v=0;
    reg [12:0] pre_in_e=0;
    reg [2047:0] pre_in_d=0;
    wire pre_out_v, pre_out_fault, pre_out_saturated;
    wire [1:0] pre_out_p;
    wire [12:0] pre_out_e;
    wire [1023:0] pre_out_d;
    integer preload_issues=0, preload_writes=0;
    integer rows=16, op=0, checked=0, reads=0, cycles=0;
    integer fd, got_bytes;
    string dir;
    assign wb_q=(RL==4) ? bp3 : ((RL==3) ? bp2 : bp1);

    generate if (SHARED != 0) begin : g_shared
        if (SHARED >= 2) begin : g_preload
            ot_hdc_v41x_fp32_bf16_preload64 u_cv (
                .clk(clk),.rst_n(rst_n),.in_v(pre_in_v),.in_p(2'd0),.in_e(pre_in_e),.in_d(pre_in_d),
                .out_v(pre_out_v),.out_p(pre_out_p),.out_e(pre_out_e),.out_d(pre_out_d),
                .out_fault(pre_out_fault),.out_saturated(pre_out_saturated));
        end else begin : g_no_preload
            assign pre_out_v=1'b0;
            assign pre_out_p=2'd0;
            assign pre_out_e=13'd0;
            assign pre_out_d=1024'd0;
            assign pre_out_fault=1'b0;
            assign pre_out_saturated=1'b0;
        end
        if (SHARED == 3) begin : g_inreg
            ot_hdc_v41x_me_xbank_macro_inreg #(.MG(MG),.MP(1),.G(G),.KMAX(5120),.NBW(14),.EW(13)) u_store (
                .clk(clk),.wr_v(1'b0),.wr_p(shared_wr_p),.wr_e(shared_wr_e),.wr_d(shared_wr_d),
                .pre_v(pre_out_v),.pre_p(pre_out_p[0]),.pre_e(pre_out_e),.pre_d(pre_out_d),
                .rd_rot(2'd2),.rq_v(shared_rq_v),.rq_q(shared_rq_q),
                .rq_plg(shared_rq_plg),.rd_x(shared_rd_x));
        end else begin : g_direct
            ot_hdc_v41x_me_xbank_macro #(.MG(MG),.MP(1),.G(G),.KMAX(5120),.NBW(14),.EW(13)) u_store (
                .clk(clk),.wr_v(SHARED==2 ? 1'b0 : shared_wr_v),.wr_p(shared_wr_p),
                .wr_e(shared_wr_e),.wr_d(shared_wr_d),
                .pre_v(pre_out_v),.pre_p(pre_out_p[0]),.pre_e(pre_out_e),.pre_d(pre_out_d),
                .rd_rot(SHARED==2 ? 2'd2 : 2'd0),
                .rq_v(shared_rq_v),.rq_q(shared_rq_q),.rq_plg(shared_rq_plg),.rd_x(shared_rd_x));
        end
        always @(posedge clk) shared_xr0 <= shared_rd_x;
    end endgenerate
    ot_hdc_v41x_me_adapt #(.W(W),.G(G),.MG(MG),.AW(AW),.BAW(BAW),.KMAX(5120),
                             .XBANK(XBANK),.RL(RL),.SHARED_XBANK(SHARED)) u_me (
        .clk(clk),.rst_n(rst_n),.go(go),.i_preloaded(SHARED>=2),.ready(ready),.idle(idle),
        .i_nout(16'(rows)),.i_tiles(16'(1)),.i_k(16'd4096),
        .i_wbase(AW'(op ? BASE1 : BASE0)),.i_xbase(AW'(op ? 4096 : 0)),
        .i_xjs(AW'(0)),.i_split(2'd0),.i_round(1'b1),
        .i_obase(AW'(op ? 64 : 0)),.i_ots(AW'(8)),.i_ojs(AW'(1)),
        .i_oen(1'b1),.i_amax(1'b0),.i_m(3'd1),
        .i_xps(AW'(0)),.i_ops(AW'(0)),.cfg_xs(4'd0),
        .wb_re(wb_re),.wb_addr(wb_addr),.wb_q(wb_q),
        .x_re(x_re),.x_addr(x_addr),.x_q(x_q),
        .shared_wr_v(shared_wr_v),.shared_wr_p(shared_wr_p),.shared_wr_e(shared_wr_e),
        .shared_wr_d(shared_wr_d),.shared_rq_v(shared_rq_v),.shared_rq_q(shared_rq_q),
        .shared_rq_plg(shared_rq_plg),.shared_xr0(shared_xr0),
        .ov(ov),.o_we(o_we),.o_addr(o_addr),.o_mask(o_mask),.o_data(o_data),
        .am_idx(),.am_val(),.am_any(),.fault(fault));

    initial begin
        if (!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR missing");
        if (!$value$plusargs("ROWS=%d",rows)) rows=16;
        if (rows < 1 || rows > 1024 || (rows % W)) $fatal(1,"bad ROWS %0d",rows);
        $readmemh({dir,"/acc.hex"},x);
        $readmemh({dir,"/za.hex"},y);
        fd=$fopen({dir,"/wo_a.me.bin"},"rb");
        if (!fd) $fatal(1,"wo_a.me.bin missing");
        got_bytes=$fread(image,fd);
        $fclose(fd);
        if (got_bytes!=IMAGE_BYTES) $fatal(1,"image bytes %0d",got_bytes);
        repeat (5) @(negedge clk);
        rst_n=1;
        for (integer j=0;j<2;j++) begin
            op=j;
            if (SHARED>=2) begin
                for(integer beat=0;beat<64;beat++) begin
                    @(negedge clk);
                    pre_in_v=1;
                    pre_in_e=beat*64;
                    // The real ACC base is 32 mod 64.  Four modulo-4 VM
                    // banks therefore return physical quarters 2,3,0,1.
                    // Keep this bank-major order through conversion and
                    // restore logical order only on the xbank read.
                    for(integer lane=0;lane<64;lane++)
                        pre_in_d[lane*32+:32]=x[j*4096+beat*64+
                            (((lane/16+2)%4)*16)+(lane%16)];
                    preload_issues=preload_issues+1;
                end
                @(negedge clk); pre_in_v=0;
                repeat(3) @(negedge clk);
                if(pre_out_fault) $fatal(1,"preload conversion fault");
            end
            @(negedge clk); go=1;
            @(negedge clk); go=0;
            wait(idle && checked == (j+1)*rows);
        end
        @(negedge clk);
        if (fault || checked!=2*rows || reads<2*rows*64 || reads>2*rows*64+64)
            $fatal(1,"WOA_FAIL checked=%0d reads=%0d fault=%0d",checked,reads,fault);
        $display("WOA_PASS rows_per_group=%0d exact_rows=%0d bank_reads=%0d cycles=%0d",
                 rows,checked,reads,cycles);
        $display("PRELOAD_PASS issue_cycles=%0d write_cycles=%0d",preload_issues,preload_writes);
        $finish;
    end

    always @(posedge clk) if (rst_n) begin
        if (pre_out_v) preload_writes<=preload_writes+1;
        cycles<=cycles+1;
        if (cycles>300000) $fatal(1,"wo_a timeout checked=%0d op=%0d",checked,op);
        for (integer p=0;p<G;p++) if (x_re[p]) begin
            if (x_addr[p*AW+:AW]>=8192) $fatal(1,"x address %0d",x_addr[p*AW+:AW]);
            x_q[p*32+:32]<=x[x_addr[p*AW+:AW]];
        end
        for (integer b=0;b<8;b++) if (wb_re[b]) begin
            integer wa, off;
            wa=wb_addr[b*BAW+:BAW];
            if (!((wa>=BASE0 && wa<BASE0+rows*64) ||
                  (wa>=BASE1 && wa<BASE1+rows*64)))
                $fatal(1,"weight address %0d op=%0d",wa,op);
            off=(wa-BASE0)*MG*8*4;
            for (integer u=0;u<MG;u++) begin
                integer ix;
                ix=off+(8*u+b)*4;
                bp0[(8*u+b)*32+:32]<={image[ix+3],image[ix+2],image[ix+1],image[ix]};
            end
            reads<=reads+1;
        end
        bp1<=bp0;
        bp2<=bp1;
        bp3<=bp2;
        if (ov) for (integer p=0;p<G;p++) if (o_we[p]) begin
            integer addr;
            addr=o_addr[p*AW+:AW];
            if (addr < (op ? 64 : 0) || addr >= (op ? 64 : 0)+rows/W)
                $fatal(1,"output address %0d op=%0d",addr,op);
            for (integer l=0;l<W;l++) if (o_mask[p*W+l]) begin
                integer row;
                row=(addr-(op ? 64 : 0))*W+l;
                if (o_data[(p*W+l)*32+:32] !== y[op*1024+row])
                    $fatal(1,"row %0d op=%0d got=%h expected=%h",row,op,
                        o_data[(p*W+l)*32+:32],y[op*1024+row]);
                checked=checked+1;
            end
        end
    end
endmodule
