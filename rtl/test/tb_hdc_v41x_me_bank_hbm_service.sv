`timescale 1ns/1ps
module tb_hdc_v41x_me_bank_hbm_service #(
    parameter integer WORDS=1024,
    parameter integer ROM_BASE=7680,
    parameter integer HBM_BASE=28'h100000,
    parameter integer BAD_RESPONSE=0
);
    localparam integer AW=18,HAW=28,MG=8,WINDOW=64;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0,start=0,op_started=0;
    reg [255:0] sectors [0:8*WORDS-1];
    wire ready,fault;
    wire [3:0] fault_why;
    wire [7:0] hq_v,hr_rdy,hr_v,mb_re;
    wire [8*HAW-1:0] hq_addr;
    wire [8*AW-1:0] hq_tag,hr_tag,mb_addr;
    wire [8*256-1:0] hr_data;
    wire [8*MG*32-1:0] mb_q;
    wire [8*(AW+1)-1:0] issued,consumed;
    wire [31:0] responses;
    reg [7:0] vpipe [0:9];
    reg [8*AW-1:0] tpipe [0:9];
    reg [255:0] expected0 [0:7], expected1 [0:7];
    reg [7:0] ev0=0,ev1=0;
    integer cyc=0, op_cyc=0, start_cyc=0, ready_cyc=0, checks=0, max_credit=0;
    integer c,l,p,delta;
    initial $readmemh("sectors.hex",sectors);
    generate for (genvar g=0;g<8;g=g+1) begin : g_bank
        assign hr_v[g] = vpipe[7+(g%3)][g];
        assign hr_tag[g*AW +: AW] = (BAD_RESPONSE && g==0 &&
            tpipe[7][g*AW +: AW]==0) ? AW'(WORDS+1) :
            tpipe[7+(g%3)][g*AW +: AW];
        assign hr_data[g*256 +: 256] = sectors[g*WORDS+
            tpipe[7+(g%3)][g*AW +: AW]];
        assign mb_re[g] = op_started && op_cyc >= 3*g && op_cyc-3*g < WORDS;
        assign mb_addr[g*AW +: AW] = AW'(ROM_BASE + op_cyc-3*g);
    end endgenerate
    wire [8*HAW-1:0] bases;
    generate for (genvar g=0;g<8;g=g+1) begin : g_base
        assign bases[g*HAW +: HAW] = HAW'(HBM_BASE+g*WORDS);
    end endgenerate
    ot_hdc_v41x_me_bank_hbm_service #(.AW(AW),.HAW(HAW),.MG(MG),
        .WINDOW(WINDOW),.LEAD(32)) dut (
        .clk(clk),.rst_n(rst_n),.start(start),.release_window(1'b0),
        .rom_base(AW'(ROM_BASE)),.nwords((AW+1)'(WORDS)),
        .bank_sector_base(bases),.ready(ready),.fault(fault),.fault_why(fault_why),
        .hq_v(hq_v),.hq_rdy(8'hff),.hq_addr(hq_addr),.hq_tag(hq_tag),
        .hr_v(hr_v),.hr_rdy(hr_rdy),.hr_tag(hr_tag),.hr_data(hr_data),
        .mb_re(mb_re),.mb_addr(mb_addr),.mb_q(mb_q),
        .issued_words(issued),.consumed_words(consumed),.response_sectors(responses));
    initial begin
        repeat(3) @(negedge clk);
        rst_n=1; start=1; start_cyc=cyc;
        @(negedge clk); start=0;
        wait(ready);
        @(negedge clk); ready_cyc=cyc; op_started=1;
    end
    always @(posedge clk) begin
        cyc <= cyc+1;
        if (op_started) op_cyc <= op_cyc+1;
        if (!rst_n) begin
            for (p=0;p<10;p=p+1) begin vpipe[p] <= 0; tpipe[p] <= 0; end
        end else begin
            vpipe[0] <= hq_v;
            tpipe[0] <= hq_tag;
            for (p=1;p<10;p=p+1) begin vpipe[p] <= vpipe[p-1]; tpipe[p] <= tpipe[p-1]; end
        end
        for (c=0;c<8;c=c+1) begin
            if (hq_v[c] && hq_addr[c*HAW +: HAW] !== HBM_BASE+c*WORDS+hq_tag[c*AW +: AW])
                $fatal(1,"HBM address mismatch bank=%0d",c);
            delta=issued[c*(AW+1) +: AW+1]-consumed[c*(AW+1) +: AW+1];
            if (delta>max_credit) max_credit <= delta;
            if (delta>WINDOW) $fatal(1,"request credit exceeded bank=%0d delta=%0d",c,delta);
            ev0[c] <= mb_re[c]; ev1[c] <= ev0[c];
            if (mb_re[c]) expected0[c] <= sectors[c*WORDS+(mb_addr[c*AW +: AW]-ROM_BASE)];
            expected1[c] <= expected0[c];
        end
        if (fault) begin
            if (BAD_RESPONSE && fault_why==4'h2) begin
                $display("ME_HBM_FAULT_PASS reason=%0h cycle=%0d",fault_why,cyc);
                $finish;
            end
            $fatal(1,"ME HBM service fault=%0h cycle=%0d",fault_why,cyc);
        end
        #1;
        for (c=0;c<8;c=c+1) if (ev1[c]) begin
            for (l=0;l<MG;l=l+1)
                if (mb_q[(8*l+c)*32 +: 32] !== expected1[c][l*32 +: 32])
                    $fatal(1,"ME bank mismatch bank=%0d lane=%0d cycle=%0d",c,l,cyc);
            checks=checks+1;
        end
        if (checks==8*WORDS) begin
            if (responses!==8*WORDS) $fatal(1,"response count %0d",responses);
            $display("ME_HBM_PASS bank_reads=%0d fp32_values=%0d requests=%0d responses=%0d first_ready=%0d service_cycles=%0d max_credit=%0d",
                     checks,checks*MG,8*WORDS,responses,ready_cyc-start_cyc,cyc-start_cyc,max_credit);
            $finish;
        end
        if (cyc>20000) $fatal(1,"timeout checks=%0d/%0d",checks,8*WORDS);
    end
endmodule
