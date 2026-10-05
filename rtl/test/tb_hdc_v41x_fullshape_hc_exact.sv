`timescale 1ns/1ps
// Checkpoint layer-0 HC attention projection through the full-depth HE adapter.
module tb_hdc_v41x_fullshape_hc_exact;
    localparam AW=30, BAW=16, HW=8, IMAGE_BYTES=1966080;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, go=0;
    wire ready, idle, fault, o_we;
    wire [7:0] w_re, x_re;
    wire [8*BAW-1:0] w_addr;
    reg [8*HW*32-1:0] w_data=0;
    wire [8*AW-1:0] x_addr;
    reg [8*32-1:0] x_q=0;
    wire [AW-1:0] o_addr;
    wire [31:0] o_mask;
    wire [1023:0] o_data;
    reg [31:0] x [0:20479];
    reg [31:0] y [0:23];
    reg [7:0] image [0:IMAGE_BYTES-1];
    integer fd, got_bytes, checked=0, reads=0, cycles=0;
    string dir;

    ot_hdc_v41x_he_adapt #(.HW(HW),.BAW(BAW),.AW(AW),.NW(21),.KCMAX(2560),.PMAX(2)) dut (
        .clk(clk),.rst_n(rst_n),.go(go),.ready(ready),.idle(idle),
        .i_nout(21'd24),.i_k(21'd2560),.i_wbase(AW'(0)),
        .i_xbase(AW'(0)),.i_obase(AW'(0)),.i_m(3'd1),
        .i_xps(AW'(0)),.i_ops(AW'(0)),
        .w_re(w_re),.w_addr(w_addr),.w_data(w_data),
        .x_re(x_re),.x_addr(x_addr),.x_q(x_q),
        .o_we(o_we),.o_addr(o_addr),.o_mask(o_mask),.o_data(o_data),.fault(fault));

    initial begin
        if (!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR missing");
        $readmemh({dir,"/x.hex"},x);
        $readmemh({dir,"/y.hex"},y);
        fd=$fopen({dir,"/hc_attn_fn.he.bin"},"rb");
        if (!fd) $fatal(1,"HC image missing");
        got_bytes=$fread(image,fd);
        $fclose(fd);
        if (got_bytes!=IMAGE_BYTES) $fatal(1,"HC image bytes %0d",got_bytes);
        repeat (5) @(negedge clk);
        rst_n=1;
        @(negedge clk); go=1;
        @(negedge clk); go=0;
        wait(idle && checked==24);
        @(negedge clk);
        if (fault || checked!=24 || reads<24*320)
            $fatal(1,"HC_FAIL checked=%0d reads=%0d fault=%0d",checked,reads,fault);
        $display("HC_PASS exact_rows=%0d bank_read_cycles=%0d cycles=%0d",checked,reads,cycles);
        $finish;
    end

    always @(posedge clk) if (rst_n) begin
        cycles<=cycles+1;
        if (cycles>30000) $fatal(1,"HC timeout checked=%0d",checked);
        for (integer b=0;b<8;b++) if (x_re[b]) begin
            if (x_addr[b*AW+:AW]>=20480) $fatal(1,"HC x address %0d",x_addr[b*AW+:AW]);
            x_q[b*32+:32]<=x[x_addr[b*AW+:AW]];
        end
        for (integer b=0;b<8;b++) if (w_re[b]) begin
            integer wa, off;
            wa=w_addr[b*BAW+:BAW];
            if (wa>=7680) $fatal(1,"HC weight address %0d",wa);
            off=wa*8*HW*4;
            for (integer l=0;l<HW;l++) begin
                integer ix;
                ix=off+(b*HW+l)*4;
                w_data[(b*HW+l)*32+:32]<={image[ix+3],image[ix+2],image[ix+1],image[ix]};
            end
            reads<=reads+1;
        end
        if (o_we) begin
            if (o_addr>=24 || o_mask!==32'd1 || o_data[31:0]!==y[o_addr])
                $fatal(1,"HC row %0d got=%h expected=%h mask=%h",o_addr,o_data[31:0],y[o_addr],o_mask);
            checked=checked+1;
        end
    end
endmodule
