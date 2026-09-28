`timescale 1ns/1ps
module tb_v41x_coll_dma_gw4 #(parameter integer WORDS=266, parameter integer PIPE=0);
    localparam integer FW=512, WA=12, SRC=2000, DST=101;
    reg clk=0,rst_n=0,go=0,started=0;
    always #5 clk=~clk;
    integer cyc=0,sent=0,committed=0,read_words=0,held=0;
    wire busy,fault,vm_re,vm_we,o_ready,e_valid,e_last,e_mode;
    wire [WA-1:0] vm_raddr,vm_waddr;
    reg [FW-1:0] vm_rq=0;
    wire [FW-1:0] vm_wdata,e_data;
    wire [3:0] vm_we4;
    wire [4*WA-1:0] vm_waddr4;
    wire [4*FW-1:0] vm_wdata4;
    wire [31:0] words_out,words_in;
    wire [7:0] e_tag;
    wire vm_ready4=PIPE ? 1'b1 : (cyc%47)<34;
    wire o_valid=started && sent<WORDS;
    wire o_last=sent==WORDS-1;
    reg [4*FW-1:0] o_data;
    reg [3:0] p1_we=0,p2_we=0;
    reg [4*WA-1:0] p1_addr=0,p2_addr=0;
    reg [4*FW-1:0] p1_data=0,p2_data=0;
    reg [4095:0] seen=0;
    function automatic [FW-1:0] payload(input integer rank,input integer idx);
        reg [FW-1:0] p;
        begin
            for(integer k=0;k<FW/32;k=k+1)
                p[32*k+:32]=(32'(rank)<<24)|(32'(idx)<<8)|32'(k);
            return p;
        end
    endfunction
    always @(*) for(integer r=0;r<4;r=r+1) o_data[r*FW+:FW]=payload(r,sent);
    ot_chip_v41x_coll_dma #(.WA(WA),.FW(FW),.TAGW(8),.N(4),.GW(4),.VM_ALWAYS_READY(PIPE)) dut (
        .clk(clk),.rst_n(rst_n),.go(go),.mode(1'b1),.rnd(1'b0),.tag(8'd7),
        .src(WA'(SRC)),.n(WA'(WORDS)),.dst(WA'(DST)),
        .busy(busy),.fault(fault),.words_out(words_out),.words_in(words_in),
        .vm_re(vm_re),.vm_raddr(vm_raddr),.vm_rq(vm_rq),
        .vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),
        .vm_ready4(vm_ready4),.vm_we4(vm_we4),.vm_waddr4(vm_waddr4),.vm_wdata4(vm_wdata4),
        .e_valid(e_valid),.e_ready(1'b1),.e_data(e_data),.e_last(e_last),
        .e_mode(e_mode),.e_tag(e_tag),
        .o_valid(o_valid),.o_ready(o_ready),.o_data(o_data),.o_last(o_last),.o_rank(2'b00),
        .o_err(1'b0),.engine_fault(1'b0));
    always @(posedge clk) if(rst_n) begin : check
        integer a,rank,idx,wc;
        wc=0;cyc<=cyc+1;
        if(vm_re) vm_rq<=payload(0,integer'(vm_raddr)-SRC);
        if(e_valid) begin
            if(e_data!==payload(0,read_words)||e_last!=(read_words==WORDS-1))
                $fatal(1,"producer read mismatch %0d",read_words);
            read_words<=read_words+1;
        end
        if(o_valid&&o_ready) sent<=sent+1;
        if(o_valid&&!o_ready) held<=held+1;
        if(vm_we) $fatal(1,"GW4 gather used scalar VM write port");
        p1_we<=vm_we4;p1_addr<=vm_waddr4;p1_data<=vm_wdata4;
        p2_we<=p1_we;p2_addr<=p1_addr;p2_data<=p1_data;
        for(integer k=0;k<4;k=k+1) if(p2_we[k]) begin
            a=p2_addr[k*WA+:WA];rank=(a-DST)/WORDS;idx=(a-DST)%WORDS;
            if(a<DST||a>=DST+4*WORDS||rank<0||rank>3||idx<0||idx>=WORDS)
                $fatal(1,"VM address %0d",a);
            if(seen[a]||p2_data[k*FW+:FW]!==payload(rank,idx))
                $fatal(1,"VM data/duplicate rank=%0d idx=%0d",rank,idx);
            seen[a]<=1;wc=wc+1;
        end
        committed<=committed+wc;
    end
    initial begin
        repeat(5)@(negedge clk);rst_n=1;
        @(negedge clk);go=1;
        @(negedge clk);go=0;started=1;
        wait(!busy||fault);
        @(negedge clk);
        if(fault||sent!=WORDS||read_words!=WORDS||words_in!=4*WORDS||committed!=4*WORDS)
            $fatal(1,"DMA completion fault=%0d sent=%0d read=%0d words_in=%0d committed=%0d",
                   fault,sent,read_words,words_in,committed);
        for(integer r=0;r<4;r=r+1)
            for(integer k=0;k<WORDS;k=k+1)
                if(!seen[DST+r*WORDS+k])$fatal(1,"missing rank=%0d idx=%0d",r,k);
        if(!PIPE && held==0)$fatal(1,"DMA backpressure unexercised");
        $display("CDMA_GW4_PASS words=%0d committed=%0d held=%0d cycles=%0d",WORDS,committed,held,cyc);
        $finish;
    end
    initial begin #1000000;$fatal(1,"DMA timeout");end
endmodule
