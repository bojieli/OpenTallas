`timescale 1ns/1ps
module tb_s81sl_rstd_release;
    localparam [127:0] LUT=128'h866f166f5f3b9a00888a3e0050029d55;
    reg clk=0;always #0.5 clk=~clk;
    reg rst_n=0,iv=0;reg[3:0]sid=0;reg[31:0]id=0;
    wire ov,bad,bv,bb;wire[31:0]od,bd;
    ot_s81sl_rstd_release #(.DELAYS(LUT)) dut(.clk(clk),.rst_n(rst_n),.sid(sid),.i_v(iv),.i_d(id),.o_v(ov),.o_d(od),.fault(bad));
    ot_s81sl_rstd_release bypass(.clk(clk),.rst_n(rst_n),.sid(sid),.i_v(iv),.i_d(id),.o_v(bv),.o_d(bd),.fault(bb));
    reg cv=0;reg[31:0]cd=0;
    always @(posedge clk) if(!rst_n)cv<=0;else begin cv<=ov;cd<=od;end
    reg sv[0:11999],ev[0:11999];reg[3:0]ss[0:11999];reg[31:0]sd[0:11999],ed[0:11999];
    integer i,j,k,pos=0,delay,nc,cy,err=0,nout=0,nsent=0;
    task reset_dut;begin
        @(negedge clk);rst_n=0;iv=0;repeat(3)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);
    end endtask
    initial begin
        for(i=0;i<12000;i=i+1)begin sv[i]=0;ev[i]=0;ss[i]=0;sd[i]=0;ed[i]=0;end
        for(k=0;k<16;k=k+1)begin
            delay=LUT[8*k +:8];
            for(j=0;j<3;j=j+1)begin
                sv[pos]=1;sd[pos]=32'h98b40000^(k<<12)^(j<<3)^pos;
                ev[pos+delay]=1;ed[pos+delay]=sd[pos];nsent=nsent+1;
                for(i=pos;i<pos+delay+4;i=i+1)ss[i]=k;
                pos=pos+delay+4;
            end
        end
        nc=pos+4;reset_dut();
        for(cy=0;cy<nc;cy=cy+1)begin
            @(negedge clk);sid=ss[cy];iv=sv[cy];id=sd[cy];
            @(posedge clk);#0.01;
            if(cv!==ev[cy] || (cv&&cd!==ed[cy]))begin err=err+1;if(err<6)$display("QREL mismatch cycle%0d sid%0d valid%b/%b data%h/%h",cy,sid,cv,ev[cy],cd,ed[cy]);end
            if(bv!==iv || bd!==id || bb!==0 || bad!==0)err=err+1;
            if(cv)nout=nout+1;
        end
        if(nout!=nsent)err=err+1;
        $display("QREL legal sid16 words%0d received%0d cycles%0d err%0d",nsent,nout,nc,err);
        // Busy overlap is a strict fault and must not overwrite the first word.
        reset_dut();nout=0;
        for(cy=0;cy<154;cy=cy+1)begin
            @(negedge clk);sid=6;iv=(cy<2);id=(cy==0)?32'h12345678:32'hbadbadba;
            @(posedge clk);#0.01;if(cv)begin nout=nout+1;if(cd!==32'h12345678)err=err+1;end
        end
        if(!bad||nout!=1)err=err+1;
        // Reset cancels the held valid; data need not reset.
        reset_dut();@(negedge clk);sid=6;iv=1;id=32'hfedcba98;
        @(negedge clk);iv=0;repeat(8)@(negedge clk);reset_dut();
        for(cy=0;cy<152;cy=cy+1)begin @(posedge clk);#0.01;if(cv||bad)err=err+1;end
        // The sid strap cannot change while a word is being held.
        reset_dut();@(negedge clk);sid=6;iv=1;
        @(negedge clk);sid=7;iv=0;repeat(4)@(negedge clk);if(!bad)err=err+1;
        $display("QREL final err%0d",err);
        if(err==0)$display("PASS QREL");else $display("FAIL QREL");
        $finish;
    end
endmodule
