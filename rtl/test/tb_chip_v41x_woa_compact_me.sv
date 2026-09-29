`timescale 1ns/1ps
// Two TP4 wo_a local groups against the source-pinned rank-0 ROM image.
// The runner supplies checkpoint ACC and raw FP32 pre-BF16 ZA as hex words.
module tb_chip_v41x_woa_compact_me;
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
    reg [79:0] compact [0:131072*8-1];
    reg [255:0] expanded [0:131072*8-1];
    reg[639:0]rom_q=0;wire[2047:0]compact_q;wire dfault;
    reg [8*MG*32-1:0] bp0=0, bp1=0;
    integer rows=16, op=0, checked=0, reads=0, cycles=0;
    integer fd, got_bytes;
    string dir;
    assign wb_q=$test$plusargs("COMPACT") ? compact_q : bp1;
    ot_chip_v41x_woa_compact_bank #(.AW(BAW)) bank(.clk(clk),.rst_n(rst_n),.wb_re(wb_re),.wb_addr(wb_addr),.rom_re(),.rom_addr(),.rom_q(rom_q),.wb_q(compact_q),.fault(dfault));

    ot_hdc_v41x_me_adapt #(.W(W),.G(G),.MG(MG),.AW(AW),.BAW(BAW),.KMAX(5120)) u_me (
        .clk(clk),.rst_n(rst_n),.go(go),.ready(ready),.idle(idle),
        .i_nout(16'(rows)),.i_tiles(16'(1)),.i_k(16'd4096),
        .i_wbase(AW'(op ? BASE1 : BASE0)),.i_xbase(AW'(op ? 4096 : 0)),
        .i_xjs(AW'(0)),.i_split(2'd0),.i_round(1'b1),
        .i_obase(AW'(op ? 64 : 0)),.i_ots(AW'(8)),.i_ojs(AW'(1)),
        .i_oen(1'b1),.i_amax(1'b0),.i_m(3'd1),
        .i_xps(AW'(0)),.i_ops(AW'(0)),.cfg_xs(4'd0),
        .wb_re(wb_re),.wb_addr(wb_addr),.wb_q(wb_q),
        .x_re(x_re),.x_addr(x_addr),.x_q(x_q),
        .ov(ov),.o_we(o_we),.o_addr(o_addr),.o_mask(o_mask),.o_data(o_data),
        .am_idx(),.am_val(),.am_any(),.fault(fault));

    initial begin
        if (!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR missing");
        if (!$value$plusargs("ROWS=%d",rows)) rows=16;
        if (rows < 1 || rows > 1024 || (rows % W)) $fatal(1,"bad ROWS %0d",rows);
        $readmemh({dir,"/acc.hex"},x);
        $readmemh({dir,"/za.hex"},y);
        $readmemh({dir,"/compact.hex"},compact);
        $readmemh({dir,"/expanded.hex"},expanded);
        repeat (5) @(negedge clk);
        rst_n=1;
        for (integer j=0;j<2;j++) begin
            op=j;
            @(negedge clk); go=1;
            @(negedge clk); go=0;
            wait(idle && checked == (j+1)*rows);
        end
        @(negedge clk);
        if (fault || dfault || checked!=2*rows || reads<2*rows*64 || reads>2*rows*64+64)
            $fatal(1,"WOA_FAIL checked=%0d reads=%0d fault=%0d",checked,reads,fault);
        $display("WOA_PASS rows_per_group=%0d exact_rows=%0d bank_reads=%0d cycles=%0d",
                 rows,checked,reads,cycles);
        $finish;
    end

    always @(posedge clk) if (rst_n) begin
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
            off=(wa-BASE0)*8+b;
            rom_q[b*80+:80]<=compact[off];
            for(integer u=0;u<MG;u++) bp0[(8*u+b)*32+:32]<=expanded[off][u*32+:32];
            reads<=reads+1;
        end
        bp1<=bp0;
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
