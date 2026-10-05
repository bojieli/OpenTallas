`timescale 1ns/1ps
module tb_chip_v41x_hbm_rsp_pipe;
    localparam integer NPC=8, TAGW=16, BEATW=4, DW=32, TOTAL=128;
    reg clk=0; always #1 clk=~clk;
    reg rst_n=0;
    reg [NPC-1:0] rv=0;
    wire [NPC-1:0] rr;
    reg [NPC*(TAGW+1)-1:0] rt='0;
    reg [NPC*BEATW-1:0] rb='0;
    reg [NPC*DW-1:0] rd='0;
    reg kr=0;
    wire kv;
    wire [TAGW-1:0] kt;
    wire [BEATW-1:0] kb;
    wire [DW-1:0] kd;
    ot_chip_v41x_hbm_rsp_pipe #(.NPC(NPC),.TAGW(TAGW),.BEATW(BEATW),.DW(DW)) dut (
        .clk(clk),.rst_n(rst_n),.r_v(rv),.r_rdy(rr),.r_tag(rt),.r_beat(rb),.r_data(rd),
        .b_rsp_rdy({NPC{1'b1}}),.k_rsp_v(kv),.k_rsp_rdy(kr),
        .k_rsp_tag(kt),.k_rsp_beat(kb),.k_rsp_data(kd));
    integer made[0:NPC-1], seen[0:NPC-1];
    integer c,p,id,seq,bad=0;
    initial begin
        for (p=0;p<NPC;p=p+1) begin made[p]=0; seen[p]=0; end
        repeat (3) @(negedge clk);
        rst_n=1;
        for (c=0;c<4000;c=c+1) begin
            @(negedge clk);
            kr=(c%7!=0 && c%11!=0);
            for (p=0;p<NPC;p=p+1) begin
                rv[p]=(p<4 && made[p]<TOTAL);
                rt[p*(TAGW+1)+:TAGW+1]={1'b1,TAGW'(p*TOTAL+made[p])};
                rb[p*BEATW+:BEATW]=BEATW'(made[p]);
                rd[p*DW+:DW]=DW'((p<<16)|made[p]);
            end
            @(posedge clk);
            for (p=0;p<4;p=p+1) if (rv[p] && rr[p]) made[p]=made[p]+1;
            if (kv && kr) begin
                id=kt/TOTAL; seq=kt%TOTAL;
                if (id<0 || id>=4 || seq!=seen[id] || kd!==DW'((id<<16)|seq) || kb!==BEATW'(seq)) begin
                    $display("BAD tag=%0d id=%0d seq=%0d data=%h beat=%0d",kt,id,seq,kd,kb);
                    bad=bad+1;
                end else seen[id]=seen[id]+1;
            end
            if (seen[0]==TOTAL && seen[1]==TOTAL && seen[2]==TOTAL && seen[3]==TOTAL) begin
                if (bad!=0) $fatal(1,"response mismatch count=%0d",bad);
                $display("PASS rsp_pipe cycles=%0d seen=%0d,%0d,%0d,%0d",c,seen[0],seen[1],seen[2],seen[3]);
                $finish;
            end
        end
        $fatal(1,"timeout seen=%0d,%0d,%0d,%0d",seen[0],seen[1],seen[2],seen[3]);
    end
endmodule
