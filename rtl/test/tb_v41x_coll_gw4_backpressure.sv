`timescale 1ns/1ps
// Same-cycle remote inputs isolate the GW4 output ready/valid contract.
// Adopted link timing is covered by rtl_v41_collective_gw4_campaign.py.
module tb_v41x_coll_gw4_backpressure #(parameter integer WORDS = 266);
    localparam integer FW=512, TAGW=8, PW=FW+TAGW+3, WA=12, DST=101;
    reg clk=0, rst_n=0, start=0, started=0, par=0;
    always #5 clk=~clk;
    integer cyc=0, sent=0, accepted=0, written=0, input_hold=0, output_hold=0;
    reg [4*FW-1:0] input_words;
    reg [FW-1:0] vm [0:2047];
    reg [2047:0] seen=0;
    wire e_ready, e_valid, e_last, e_err, e_fault;
    wire [4*FW-1:0] e_data;
    wire [1:0] e_rank;
    wire [2:0] e_fault_code;
    wire [3:0] tx_valid, rx_valid, relay_valid;
    wire [PW-1:0] tx_rec;
    wire [4*PW-1:0] rx_rec, relay_rec;
    wire [7:0] cr_out;
    wire tr_ready, tr_valid, tr_last, tr_done, tr_fault;
    wire [3:0] tr_we;
    wire [4*WA-1:0] tr_addr;
    wire [4*FW-1:0] tr_data;
    wire bank_ready=(cyc%47)<34;
    wire src_valid=started && sent<WORDS;
    wire fire=src_valid && e_ready;
    wire src_last=sent==WORDS-1;

    function automatic [FW-1:0] payload(input integer rank, input integer idx);
        reg [FW-1:0] p;
        begin
            for (integer k=0;k<FW/32;k=k+1)
                p[32*k+:32]=(32'(rank)<<24)|(32'(idx)<<8)|32'(k);
            return p;
        end
    endfunction
    always @(*) for (integer r=0;r<4;r=r+1)
        input_words[r*FW+:FW]=payload(r,sent);
    assign rx_valid={fire,fire,fire,1'b0};
    assign rx_rec[0+:PW]={PW{1'b0}};
    for (genvar r=1;r<4;r=r+1) begin : g_remote
        assign rx_rec[r*PW+:PW]={TAGW'(7),1'b1,src_last,par,input_words[r*FW+:FW]};
    end
    ot_rom_oneshot_die_px #(.N(4),.RANK(0),.LANES(16),.TAGW(TAGW),.DEPTH(16),
                             .RELAY(0),.ADD_LAT(3),.PAIRWISE(1),.GW(4),.OUT_BP(1)) u_eng (
        .clk(clk),.rst_n(rst_n),.in_valid(src_valid),.in_ready(e_ready),
        .in_data(input_words[0+:FW]),.in_last(src_last),.in_mode(1'b1),.in_tag(TAGW'(7)),
        .tx_valid(tx_valid),.tx_rec(tx_rec),.tx_ready(4'b1111),.cr_in(cr_out),
        .rx_valid(rx_valid),.rx_rec(rx_rec),.cr_out(cr_out),
        .rl_tx_valid(relay_valid),.rl_tx_rec(relay_rec),
        .rl_rx_valid(4'b0000),.rl_rx_rec({4*PW{1'b0}}),
        .out_valid(e_valid),.out_ready(tr_ready),.out_data(e_data),
        .out_last(e_last),.out_rank(e_rank),.out_err(e_err),
        .fault(e_fault),.fault_code(e_fault_code));
    ot_chip_v41x_coll_transpose #(.WA(WA),.FW(FW)) u_tr (
        .clk(clk),.rst_n(rst_n),.start(start),.dst(WA'(DST)),.n(WA'(WORDS)),
        .in_ready(tr_ready),.in_valid(e_valid),.in_data(e_data),.in_last(e_last),
        .out_ready(bank_ready),.out_valid(tr_valid),.out_we(tr_we),
        .out_addr(tr_addr),.out_data(tr_data),.out_last(tr_last),
        .done(tr_done),.fault(tr_fault));
    always @(posedge clk) if (rst_n) begin : check
        integer a, rank, idx, wc;
        wc=0;cyc<=cyc+1;
        if (fire) begin sent<=sent+1;par<=src_last?1'b0:~par;end
        if (src_valid&&!e_ready) input_hold<=input_hold+1;
        if (e_valid&&!tr_ready) output_hold<=output_hold+1;
        if (e_valid&&tr_ready) begin
            if(e_rank!=0||e_last!=(accepted==WORDS-1))
                $fatal(1,"engine rank/last mismatch at %0d",accepted);
            accepted<=accepted+1;
        end
        for(integer k=0;k<4;k=k+1) if(tr_we[k]) begin
            a=tr_addr[k*WA+:WA];rank=(a-DST)/WORDS;idx=(a-DST)%WORDS;
            if(a<DST||a>=DST+4*WORDS||rank<0||rank>3||idx<0||idx>=WORDS)
                $fatal(1,"write address %0d",a);
            if(seen[a]||tr_data[k*FW+:FW]!==payload(rank,idx))
                $fatal(1,"write data/duplicate rank=%0d idx=%0d",rank,idx);
            seen[a]<=1;vm[a]<=tr_data[k*FW+:FW];wc=wc+1;
        end
        written<=written+wc;
    end
    initial begin
        repeat(5) @(negedge clk);rst_n=1;
        @(negedge clk);start=1;
        @(negedge clk);start=0;started=1;
        wait(tr_done||tr_fault||e_fault);
        @(negedge clk);
        if(tr_fault||e_fault||e_err)$fatal(1,"engine/transpose fault %0d %0d",e_fault,tr_fault);
        if(sent!=WORDS||accepted!=WORDS||written!=4*WORDS)
            $fatal(1,"counts sent=%0d accepted=%0d written=%0d",sent,accepted,written);
        for(integer r=0;r<4;r=r+1)
            for(integer k=0;k<WORDS;k=k+1)
                if(!seen[DST+r*WORDS+k]||vm[DST+r*WORDS+k]!==payload(r,k))
                    $fatal(1,"final VM rank=%0d index=%0d",r,k);
        if(input_hold==0||output_hold==0)$fatal(1,"backpressure not exercised");
        $display("GW4_BACKPRESSURE_PASS words=%0d writes=%0d in_hold=%0d out_hold=%0d cycles=%0d",WORDS,written,input_hold,output_hold,cyc);
        $finish;
    end
    initial begin #1000000;$fatal(1,"timeout");end
endmodule
