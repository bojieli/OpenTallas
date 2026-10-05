`timescale 1ns/1ps
module tb_hdc_qwen_fullshape_decode;
    localparam integer W=16, G=4, SW=16, AW=24, NW=18, PAW=12;
    parameter integer EMB_BASE=0;
    reg clk=0, rst_n=0, start=0;
    always #5 clk=~clk;
    reg [1023:0] prog [0:1];
    reg [G*W*8-1:0] codes [0:8191];
    reg [15:0] scales [0:4095];
    reg [31:0] expected [0:127];
    reg [31:0] vm [0:4095];
    reg [1023:0] dir;
    wire prog_re; wire [PAW-1:0] prog_addr; reg [1023:0] prog_q;
    wire embed_code_re, embed_scale_re;
    wire [AW-1:0] embed_code_addr; wire [NW-1:0] embed_scale_addr;
    reg [G*W*8-1:0] embed_code_q;
    reg [15:0] embed_scale_q;
    wire [SW-1:0] vw_su_we; wire [SW*AW-1:0] vw_su_addr;
    wire [SW*32-1:0] vw_su_data;
    wire done, fault;
    wire [NW-1:0] next_token;
    wire [31:0] next_val, cycles;
    wire [SW-1:0] va_re; wire [SW*AW-1:0] va_addr;
    wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr;
    wire [SW-1:0] vb_re, vc_re; wire [SW*AW-1:0] vb_addr, vc_addr;
    wire [SW-1:0] crom_re; wire [SW*AW-1:0] crom_addr;
    wire [G-1:0] vw_me_we; wire [G*AW-1:0] vw_me_addr;
    wire [G*W-1:0] vw_me_mask; wire [G*W*32-1:0] vw_me_data;
    wire vw_rd_we; wire [AW-1:0] vw_rd_addr; wire [31:0] vw_rd_data;
    wire wrom_re, int8_wrom_re, scale_re; wire [AW-1:0] wrom_addr, int8_wrom_addr;
    wire [G*AW-1:0] scale_addr;
    wire kv_re; wire [G*AW-1:0] kv_raddr; wire [SW-1:0] kv_we;
    wire [SW*AW-1:0] kv_waddr; wire [SW*32-1:0] kv_wdata;
    ot_hdc_core_vector_weight #(.W(W),.G(G),.SW(SW),.SU_VEC(1),.AW(AW),.NW(NW),.PAW(PAW),
                                .INT8_EMBED(1),.QWEN_FULLSHAPE(1),.HID(128),.EMB_CODE_LANES(G*W),.EMB_ADDR_BASE(EMB_BASE)) dut (
        .clk(clk),.rst_n(rst_n),.start(start),.token(18'd151935),.pos(18'd0),
        .done(done),.next_token(next_token),.next_val(next_val),.cycles(cycles),.fault(fault),
        .prog_re(prog_re),.prog_addr(prog_addr),.prog_q(prog_q),
        .wrom_re(wrom_re),.wrom_addr(wrom_addr),.wrom_q({G*W*16{1'b0}}),
        .int8_wrom_re(int8_wrom_re),.int8_wrom_addr(int8_wrom_addr),.int8_wrom_q({G*W*8{1'b0}}),
        .scale_re(scale_re),.scale_addr(scale_addr),.scale_q({G*W*16{1'b0}}),
        .embed_code_re(embed_code_re),.embed_code_addr(embed_code_addr),.embed_code_q(embed_code_q),
        .embed_scale_re(embed_scale_re),.embed_scale_addr(embed_scale_addr),.embed_scale_q(embed_scale_q),
        .crom_re(crom_re),.crom_addr(crom_addr),.crom_q({SW*64{1'b0}}),
        .kv_re(kv_re),.kv_raddr(kv_raddr),.kv_q({G*W*32{1'b0}}),
        .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),
        .kv_write_drained(1'b1),.vx_re(vx_re),.vx_addr(vx_addr),.vx_q({G*32{1'b0}}),
        .va_re(va_re),.va_addr(va_addr),.va_q({SW*32{1'b0}}),
        .vb_re(vb_re),.vb_addr(vb_addr),.vb_q({SW*32{1'b0}}),
        .vc_re(vc_re),.vc_addr(vc_addr),.vc_q({SW*32{1'b0}}),
        .vw_me_we(vw_me_we),.vw_me_addr(vw_me_addr),.vw_me_mask(vw_me_mask),.vw_me_data(vw_me_data),
        .vw_su_we(vw_su_we),.vw_su_addr(vw_su_addr),.vw_su_data(vw_su_data),
        .vw_rd_we(vw_rd_we),.vw_rd_addr(vw_rd_addr),.vw_rd_data(vw_rd_data),
        .w_ok(1'b1),.emb_ok(1'b1),.kv_ok(1'b1));
    integer i, cycle, bad, writes, code_reads, scale_reads;
    reg [AW-1:0] first_code_addr;
    reg saw_row0;
    always @(negedge clk) if (rst_n && dut.me_row0 == 18'h12345) saw_row0 <= 1'b1;
    always @(posedge clk) begin
        if (prog_re) prog_q <= prog[prog_addr];
        if (embed_code_re) embed_code_q <= 0;
        if (embed_scale_re) embed_scale_q <= 16'h3f80;
        if (rst_n) begin
            if (embed_code_re) begin
                if (code_reads == 0) first_code_addr <= embed_code_addr;
                code_reads <= code_reads+1;
            end
            if (embed_scale_re) scale_reads <= scale_reads+1;
            for (integer j=0;j<SW;j=j+1) if (vw_su_we[j]) begin
                vm[vw_su_addr[j*AW +: AW]] <= vw_su_data[j*32 +: 32];
                writes = writes+1;
            end
        end
    end
    initial begin
        if (!$value$plusargs("DIR=%s",dir)) $fatal(1,"missing DIR");
        $readmemh({dir,"/program.hex"},prog);
        code_reads=0; scale_reads=0; writes=0; saw_row0=0;
        repeat(5) @(negedge clk);
        rst_n=1;
        @(negedge clk); start=1;
        @(negedge clk); start=0;
        cycle=0;
        while (code_reads == 0 && cycle < 1000) begin @(posedge clk); cycle=cycle+1; end
        if (code_reads == 0) $fatal(1,"no embedding request");
        if (first_code_addr !== 24'd303870)
            $fatal(1,"high token code address got=%0d expected=303870",first_code_addr);
        if (!saw_row0)
            $fatal(1,"high instruction row0 never decoded");
        if (embed_scale_addr !== 18'd151935)
            $fatal(1,"high token scale address got=%0d",embed_scale_addr);
        $display("QWEN_FULLSHAPE_DECODE code_addr=%0d scale_addr=%0d row0=12345",first_code_addr,embed_scale_addr);
        $finish;
    end
endmodule
