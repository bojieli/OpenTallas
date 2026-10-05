`timescale 1ns/1ps
// Exact ROM-image byte comparison for a two-word V4.1 full-shape weight
// window. The same three ROM addresses are read in both arms. HBM responses
// arrive with requests and beats reversed to exercise tag/segment assembly.
module tb_hdc_v41x_weight_window_fullshape #(
    parameter integer SW=66,
    parameter integer NPC=4,
    parameter integer WORDS=2,
    parameter integer HBM_BASE=28'h0100000,
    parameter integer BURST=(SW<32)?SW:32,
    parameter integer SEGMENTS=(SW+BURST-1)/BURST,
    parameter integer SGW=(SEGMENTS>1)?$clog2(SEGMENTS):0,
    parameter integer RTW=1+SGW,
    parameter integer BW=(BURST>1)?$clog2(BURST):1,
    parameter integer NREQ=WORDS*SEGMENTS
);
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, start=0, rom_re=0;
    reg [7:0] rom_addr=0;
    localparam [7:0] ROM_BASE=8'h24;
    reg [255:0] sectors [0:WORDS*SW-1];
    reg [SW*256-1:0] rom_words [0:WORDS-1];
    wire [SW*256-1:0] hbm_q;
    wire ready, fault, hq_v;
    wire [3:0] fault_why;
    wire [27:0] hq_addr;
    wire [5:0] hq_len;
    wire [RTW-1:0] hq_tag;
    reg [NPC-1:0] hr_v=0;
    wire [NPC-1:0] hr_rdy;
    reg [NPC*RTW-1:0] hr_tag=0;
    reg [NPC*BW-1:0] hr_beat=0;
    reg [NPC*256-1:0] hr_data=0;
    wire [1:0] fetched_words;
    wire [31:0] received;
    integer cyc=0, start_cycle=0, req_count=0, responses=0;
    reg [27:0] req_addr [0:NREQ-1];
    reg [5:0] req_len [0:NREQ-1];
    reg [RTW-1:0] req_tag [0:NREQ-1];
    integer w,s,p,r,b,idx,read_checks=0;

    initial begin
        $readmemh("sectors.hex", sectors);
        for (w=0; w<WORDS; w=w+1)
            for (s=0; s<SW; s=s+1)
                rom_words[w][s*256 +: 256] = sectors[w*SW+s];
    end
    ot_hdc_v41x_weight_window #(
        .WB(SW*256), .SB(256), .WORDS(WORDS), .AW(8), .HAW(28),
        .NPC(NPC), .LENW(6), .BURST_MAX(BURST)
    ) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .release_window(1'b0),
        .rom_base(ROM_BASE), .hbm_base(28'(HBM_BASE)), .nwords(2'd2),
        .ready(ready), .hq_v(hq_v), .hq_rdy(1'b1),
        .hq_addr(hq_addr), .hq_len(hq_len), .hq_tag(hq_tag),
        .hr_v(hr_v), .hr_rdy(hr_rdy), .hr_tag(hr_tag),
        .hr_beat(hr_beat), .hr_data(hr_data),
        .rom_re(rom_re), .rom_addr(rom_addr), .rom_q(hbm_q),
        .fault(fault), .fault_why(fault_why),
        .fetched_words(fetched_words), .received_sectors(received)
    );
    always @(posedge clk) begin
        cyc <= cyc+1;
        if (hq_v) begin
            if (req_count >= NREQ || hq_addr !== HBM_BASE + (req_count/SEGMENTS)*SW +
                (req_count%SEGMENTS)*BURST ||
                hq_len !== (((req_count%SEGMENTS)==SEGMENTS-1) ?
                           SW-(SEGMENTS-1)*BURST : BURST) ||
                hq_tag !== req_count/SEGMENTS*(1<<SGW)+(req_count%SEGMENTS))
                $fatal(1,"request mismatch %0d addr=%0d len=%0d tag=%0d",req_count,hq_addr,hq_len,hq_tag);
            req_addr[req_count] <= hq_addr;
            req_len[req_count] <= hq_len;
            req_tag[req_count] <= hq_tag;
            req_count <= req_count+1;
        end
    end
    task automatic read_compare(input integer word_index);
        begin
            @(negedge clk);
            rom_re=1;
            rom_addr=ROM_BASE+word_index;
            @(posedge clk); #1;
            if (hbm_q !== rom_words[word_index])
                $fatal(1,"ROM/HBM word %0d mismatch",word_index);
            read_checks=read_checks+1;
        end
    endtask
    initial begin
        repeat (3) @(negedge clk);
        rst_n=1;
        start=1;
        start_cycle=cyc;
        @(negedge clk); start=0;
        wait(req_count == NREQ);
        @(negedge clk);
        if (fetched_words !== WORDS || ready) $fatal(1,"issued/ready before responses");
        // Deliver every request in reverse order, with beats reversed inside
        // each burst. Up to NPC sectors return per cycle.
        r=NREQ-1; b=req_len[r]-1;
        while (r>=0) begin
            hr_v=0;
            for (p=0;p<NPC;p=p+1) begin
                if (r>=0) begin
                    idx=req_addr[r]-HBM_BASE+b;
                    hr_v[p]=1;
                    hr_tag[p*RTW +: RTW]=req_tag[r];
                    hr_beat[p*BW +: BW]=b;
                    hr_data[p*256 +: 256]=sectors[idx];
                    responses=responses+1;
                    b=b-1;
                    if (b<0) begin
                        r=r-1;
                        if (r>=0) b=req_len[r]-1;
                    end
                end
            end
            @(posedge clk); #1;
            @(negedge clk);
        end
        hr_v=0;
        #1;
        if (!ready || fault || received !== WORDS*SW || responses != WORDS*SW)
            $fatal(1,"window incomplete fault=%0d why=%0h received=%0d",fault,fault_why,received);
        read_compare(1);
        read_compare(0);
        read_compare(1);
        @(negedge clk); rom_re=0;
        $display("FULLSHAPE_WEIGHT_PASS sectors_per_word=%0d npc=%0d requests=%0d sectors=%0d reads=%0d wait_cycles=%0d",
                 SW,NPC,req_count,received,read_checks,cyc-start_cycle);
        $finish;
    end
    initial begin
        repeat (10000) @(posedge clk);
        $fatal(1,"timeout");
    end
endmodule
