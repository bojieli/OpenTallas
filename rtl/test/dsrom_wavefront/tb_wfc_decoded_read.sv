`timescale 1ns/1ps
module decoded_case #(parameter N=32)(output reg done=0);
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, we=0, rwe=0, wek=0, wef=0;
    reg [4:0] rd_lo=0,wlo=0;
    reg [2:0] rd_slot=0,rslot=0;
    reg [80:0] wrec=0;
    reg [20:0] rdata=0;
    wire [80:0] a_rec,b_rec;
    wire [20:0] a_ring,b_ring;
    wire a_k,a_f,b_k,b_f;
    wire [4:0] a_kl,a_fl,b_kl,b_fl;
    ot_rom_pkg_ctrl_wfc_grp #(.RW(81),.NW(21),.N(N)) a
      (clk,rst_n,rd_lo,rd_slot,a_rec,a_ring,we,wlo,wrec,wek,wef,rwe,rslot,rdata,a_k,a_f,a_kl,a_fl);
    ot_rom_pkg_ctrl_wfc_grp #(.DECODED_READ(1),.RW(81),.NW(21),.N(N)) b
      (clk,rst_n,rd_lo,rd_slot,b_rec,b_ring,we,wlo,wrec,wek,wef,rwe,rslot,rdata,b_k,b_f,b_kl,b_fl);
    integer u,s,c;
    reg checking=0;
    always @(posedge clk) begin
        #1;
        if (checking && {a_rec,a_ring,a_k,a_f,a_kl,a_fl} !==
                        {b_rec,b_ring,b_k,b_f,b_kl,b_fl})
            $fatal(1,"decoded read mismatch N=%0d cycle=%0d address=%0d slot=%0d",N,c,rd_lo,rd_slot);
    end
    initial begin
        repeat(3) @(negedge clk); rst_n=1;
        // Initialize every stored word before comparing four-state reads.
        for(u=0;u<N;u=u+1) for(s=0;s<8;s=s+1) begin
            @(negedge clk); we=1;rwe=1;wlo=u;rslot=s;
            wrec={32'(u+1),32'(u*37),17'(u*13+1)};
            rdata=u*101+s;wek=u%2;wef=u%3==0;
        end
        @(negedge clk);we=0;rwe=0;
        repeat(3) @(negedge clk); checking=1;
        // All addresses, all slots, invalid users, and simultaneous reads/writes.
        for(c=0;c<8192;c=c+1) begin
            @(negedge clk);rd_lo=c%32;rd_slot=(c/32)%8;
            wlo=(c*13)%32;rslot=c%8;we=c%3==0;rwe=c%5==0;
            wrec={32'(c*97),32'(c*31),17'(c*7+1)};
            rdata=c*29;wek=c%7==0;wef=c%11==0;
            if(c==4096)rst_n=0;
            if(c==4100)rst_n=1;
        end
        @(negedge clk);done=1;
    end
endmodule
module tb_wfc_decoded_read;
    wire d1,d27,d32;
    decoded_case #(.N(1)) a(d1);
    decoded_case #(.N(27)) b(d27);
    decoded_case #(.N(32)) c(d32);
    initial begin
        wait(d1&&d27&&d32);
        $display("DECODED_READ PASS N=1,27,32 24576 exact read/write/reset cycles");
        $finish;
    end
endmodule
