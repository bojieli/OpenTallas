`timescale 1ns/1ps
module tb_qwen_xline_roots;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0,start=0; reg [378:0] ib=0;
    wire busy,fault,sv; wire [8:0] si;
    reg [9:0] w[0:2], e[0:4];
    wire [507:0] wd,ed;
    function automatic [127:0] px(input integer id,input integer root);
        px={32'hdeadbeef ^ id, 32'h1234abcd ^ root,32'habcd0123 ^ id,32'hffeedd00 ^ id};
    endfunction
    ot_qwen_xline_roots dut(clk,rst_n,start,ib,busy,fault,sv,si,w[2][9],w[2][8:0],px(w[2][8:0],0),e[4][9],e[4][8:0],px(e[4][8:0],1),wd,ed);
    integer i,cyc=0,first=-1,nw=0,ne=0,wx=-1,ex=-1;
    always @(posedge clk) begin
        cyc<=cyc+1;
        if(!rst_n) begin for(i=0;i<3;i=i+1) w[i]<=0; for(i=0;i<5;i=i+1) e[i]<=0; end
        else begin
            w[0]<={sv,si}; e[0]<={sv,si};
            for(i=1;i<3;i=i+1) w[i]<=w[i-1];
            for(i=1;i<5;i=i+1) e[i]<=e[i-1];
            if(sv && first<0) first=cyc;
            if(wd[0]) begin if(nw!=512 || wd[379:1]!==ib) $fatal(1,"bad W EXEC"); wx=cyc; end
            else if(wd[379]) begin if(wd[9:1]!==9'(nw) || wd[507:380]!==px(nw,0)) $fatal(1,"bad W LOAD"); nw=nw+1; end
            if(ed[0]) begin if(ne!=512 || ed[379:1]!==ib) $fatal(1,"bad E EXEC"); ex=cyc; end
            else if(ed[379]) begin if(ed[9:1]!==9'(ne) || ed[507:380]!==px(ne,1)) $fatal(1,"bad E LOAD"); ne=ne+1; end
        end
    end
    initial begin
        repeat(3) @(negedge clk); rst_n=1; ib={379{1'b1}}; start=1;
        @(negedge clk); start=0;
        wait(!busy); @(negedge clk);
        if(fault || wx-first!=515 || ex-first!=517) $fatal(1,"root timing fault w=%0d e=%0d",wx-first,ex-first);
        $display("PASS root_requests=512 W_select=3 E_select=5 W_EXEC=515 E_EXEC=517 from first request edge");
        $finish;
    end
endmodule
