`timescale 1ns/1ps
// An actual streamer descriptor consumes a booted K tail word through the
// vector bank port; no behavioral KV array feeds the matrix read output.
module tb_hdc_qwen_kv_system_tail;
    parameter integer SW=8;
    parameter integer V_MODE=0;
    localparam AW=24,G=4,W=16,LWIN=4,NPC=2,BK=4,TAGW=1+LWIN+$clog2(G)+3,LBK=$clog2(BK);
    reg clk=0,rst_n=0,boot_v=0,kvd_v=0,kv_re=0;
    always #5 clk=~clk;
    reg [AW-1:0] boot_word=0;
    reg [127:0] boot_data=0;
    reg [SW-1:0] kv_we=0;
    reg [SW*AW-1:0] kv_waddr=0;
    reg [SW*32-1:0] kv_wdata=0;
    wire [G*W*32-1:0] kv_q;
    wire kv_ok,drained,fault;
    wire [G-1:0] win_we;
    wire [G*LWIN-1:0] win_waddr;
    wire [G*W*16-1:0] win_wdata;
    wire win_re;
    wire [LWIN-1:0] win_raddr;
    reg [G*W*16-1:0] win_q=0;
    reg [W*16-1:0] win_mem [0:G-1][0:(1<<LWIN)-1];
    wire [2*SW-1:0] bank_we,bank_re;
    wire [2*SW*AW-1:0] bank_wrow,bank_rrow;
    wire [2*SW*16-1:0] bank_wmask;
    wire [2*SW*128-1:0] bank_wdata;
    reg [2*SW*128-1:0] bank_q=0;
    reg [127:0] bank_mem [0:2*SW-1][0:15];
    wire h_req_v,h_req_we;
    wire [AW-1:0] h_req_sector;
    wire [LBK:0] h_req_len;
    wire [TAGW-1:0] h_req_tag;
    wire [255:0] h_req_data;
    wire [NPC-1:0] h_rsp_ready;
    reg [NPC-1:0] h_rsp_v=0;
    reg [NPC*TAGW-1:0] h_rsp_tag=0;
    reg [NPC*LBK-1:0] h_rsp_beat=0;
    reg [NPC*256-1:0] h_rsp_data=0;
    reg [255:0] h_mem [0:511];
    integer b,r;
    ot_hdc_qwen_kv_system #(.W(W),.G(G),.SW(SW),.AW(AW),.LWIN(LWIN),
                             .NPC(NPC),.BK(BK),.LOG_HD(4),.LOG_TW(2),.LLG(3),.V0_WORD(512)) dut (
        .clk(clk),.rst_n(rst_n),.tok_start(1'b0),.tok_pos(16'd0),.cfg_lead(16'd0),
        .kvd_v(kvd_v),.kvd_wbase(V_MODE ? 24'd512 : 24'd0),
        .kvd_ts(V_MODE ? 24'd1 : 24'd16),.kvd_ks(24'd1),.kvd_js(24'd16),
        .kvd_jsh(3'd3),.kvd_tiles(16'd1),.kvd_k(16'd1),.kvd_nout(16'd16),
        .kvd_pos(16'd0),.kvd_kindk(!V_MODE),.kv_ok(kv_ok),
        .kv_re(kv_re),.kv_raddr(V_MODE ? {{((G-1)*AW){1'b0}},24'd512} : '0),.kv_q(kv_q),
        .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),
        .kv_write_flush(1'b1),.kv_write_drained(drained),
        .boot_v(boot_v),.boot_word(boot_word),.boot_data(boot_data),
        .win_we(win_we),.win_waddr(win_waddr),.win_wdata(win_wdata),
        .win_re(win_re),.win_raddr(win_raddr),.win_q(win_q),
        .bank_we(bank_we),.bank_re(bank_re),.bank_wrow(bank_wrow),.bank_rrow(bank_rrow),
        .bank_wmask(bank_wmask),.bank_wdata(bank_wdata),.bank_q(bank_q),
        .h_req_v(h_req_v),.h_req_ready(1'b1),.h_req_we(h_req_we),
        .h_req_sector(h_req_sector),.h_req_len(h_req_len),.h_req_tag(h_req_tag),.h_req_data(h_req_data),
        .h_rsp_v(h_rsp_v),.h_rsp_ready(h_rsp_ready),.h_rsp_tag(h_rsp_tag),
        .h_rsp_beat(h_rsp_beat),.h_rsp_data(h_rsp_data),
        .fault(fault));
    always @(posedge clk) begin
        h_rsp_v <= 0;
        if (h_req_v) begin
            if (h_req_we) h_mem[h_req_sector] <= h_req_data;
            else begin
                h_rsp_v[0] <= 1;
                h_rsp_tag[0 +: TAGW] <= h_req_tag;
                h_rsp_beat[0 +: LBK] <= 0;
                h_rsp_data[0 +: 256] <= h_mem[h_req_sector];
            end
        end
        for (integer g=0;g<G;g=g+1) begin
            if (win_re) win_q[g*W*16 +: W*16] <= win_mem[g][win_raddr];
            if (win_we[g]) win_mem[g][win_waddr[g*LWIN +: LWIN]] <= win_wdata[g*W*16 +: W*16];
        end
        for (integer i=0;i<2*SW;i=i+1) begin
            if (bank_re[i]) bank_q[i*128 +: 128] <= bank_mem[i][bank_rrow[i*AW +: AW]];
            if (bank_we[i])
                for (integer j=0;j<16;j=j+1)
                    if (bank_wmask[i*16+j]) bank_mem[i][bank_wrow[i*AW +: AW]][j*8 +: 8] <=
                        bank_wdata[i*128+j*8 +: 8];
        end
    end
    initial begin
        for (b=0;b<2*SW;b=b+1)
            for (r=0;r<16;r=r+1) bank_mem[b][r]=0;
        for (b=0;b<512;b=b+1) h_mem[b]=0;
        for (b=0;b<G;b=b+1)
            for (r=0;r<(1<<LWIN);r=r+1) win_mem[b][r]=0;
        repeat(2) @(negedge clk); rst_n=1; boot_v=1;
        // The KV descriptor arrives with a vector K write. The system must
        // hold the descriptor until that write retires to the physical bank.
        @(negedge clk); boot_v=0; kvd_v=1;
        kv_we[0]=1; kv_waddr[0 +: AW]=V_MODE ? 8192 : 0; kv_wdata[0 +: 32]=32'h3f800000;
        @(negedge clk); kvd_v=0; kv_we=0;
        for (integer n=0;n<300 && !kv_ok;n=n+1) @(negedge clk);
        if (!kv_ok || !drained || fault) $fatal(1,"descriptor did not become ready");
        kv_re=1;
        @(posedge clk); #1;
        if (kv_q[31:0] !== 32'h3f800000 || fault || (!V_MODE && h_req_v))
            $fatal(1,"KV physical read mismatch SW=%0d V=%0d got=%h fault=%b hq=%b",SW,V_MODE,kv_q[31:0],fault,h_req_v);
        $display("PASS QWEN_KV_SYSTEM_%s SW=%0d",V_MODE ? "V_SECTOR" : "TAIL",SW); $finish;
    end
endmodule
