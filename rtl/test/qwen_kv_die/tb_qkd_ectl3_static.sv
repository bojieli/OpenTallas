`timescale 1ns/1ps
// Control/mapped-SRAM proof at the native TP8 QK shape; head arithmetic is a separate owner proof.
module tb_qkd_ectl3_static;
    parameter integer MUT=0;
    reg ck=0,rst_n=0;
    always #0.5 ck=~ck;
    reg [633:0] si=0;
    reg [1024:0] rs=0;
    wire [424:0] so;
    wire [16:0] rq;
    wire [1558:0] t0,t1;
    qkd_ectl3_epoch_direct_s #(.STATIC_QK(1),.QK_ISSUE_AGE(34),.ROW_RETURN_LAT(9)) dut (
        .ck({3{ck}}),.rst_n(rst_n),.cfg(5'b01101),.e0(),.e1(),.e2(),.e3(),
        .s0(34'd0),.s1(34'd0),.s2(34'd0),.s3(34'd0),.t0(t0),.t1(t1),.rq(rq),.rs(rs),.si(si),.so(so));
    function automatic [1023:0] rowf(input integer n);
        for(integer j=0;j<32;j=j+1) rowf[j*32+:32]=32'h42000000 ^ (n*32'h10203) ^ j;
    endfunction
    reg [1023:0] response[0:1023];
    reg rv[0:1023];
    integer cyc,nreq=0,nconsume=0,startcyc=-1,firstreq=-1,firstconsume=-1;
    integer idx,pidx,tp;
    initial begin
        for(integer j=0;j<1024;j=j+1) begin rv[j]=0;response[j]=0;end
        repeat(6) @(negedge ck);rst_n=1;
        repeat(80) @(negedge ck);
        for(cyc=0;cyc<500;cyc=cyc+1) begin
            si=0;si[14:1]=8192;si[17:15]=cyc%8;
            if(cyc==0)si[0]=1;
            if(cyc>=1&&cyc<=32)begin si[18]=1;si[24:19]=cyc-1;end
            if(MUT==3&&cyc==17)si[24:19]=0;
            rs={response[cyc],rv[cyc]};
            if(MUT==1&&cyc==20)rs[0]=0;
            if(MUT==2&&cyc==20)begin rs[0]=0;rv[cyc+1]=1;response[cyc+1]=response[cyc];end
            @(posedge ck);
            if(dut.u_c.u.start)startcyc=cyc;
            if(cyc<16 && (rq[0] || dut.u_a.u.u.row_slot || dut.u_c.u.start))
                $display("TRACE c%0d localstart%0d rq%0d rs%0d captured%0d slot%0d",cyc,dut.u_c.u.start,rq[0],rs[0],dut.u_a.u.u.rsp_valid,dut.u_a.u.u.row_slot);
            if(rq[0])begin
                if(firstreq<0)firstreq=cyc;
                if(nreq>=256||cyc!=firstreq+nreq)$fatal(1,"request slot %0d at %0d",nreq,cyc);
                idx=3+8*nreq;pidx=((idx>>11)&1)*2048+((idx>>6)&15)*128+((idx>>10)&1)*64+(idx&63);
                tp=((pidx>>7)<<9)+(1<<7)+(pidx&127);
                if(rq[15:3]!=tp||rq[2:1]!=0)$fatal(1,"request tag %0d t%0d expected%0d",nreq,rq[15:3],tp);
                rv[cyc+4]=1;response[cyc+4]=rowf(nreq);nreq=nreq+1;
            end
            if(dut.u_a.u.u.k_issue!==dut.u_b.u.k_issue||dut.u_a.u.u.k_issue!==dut.u_c.u.k_issue)$fatal(1,"copies diverged");
            if(dut.u_a.u.u.k_issue)begin
                if(firstconsume<0)firstconsume=cyc;
                if(cyc!=startcyc+34+nconsume)$fatal(1,"consume slot %0d at %0d S%0d",nconsume,cyc,startcyc);
                if(MUT==0 && {dut.u_b.u.row,dut.u_a.u.u.row}!==rowf(nconsume))$fatal(1,"SRAM row mismatch %0d at%0d got%h expected%h",nconsume,cyc,dut.u_a.u.u.row[31:0],rowf(nconsume));
                nconsume=nconsume+1;
            end
            @(negedge ck);
        end
        if(nreq!=256||nconsume!=256||!so[422])$fatal(1,"shape req%0d consume%0d done%0d",nreq,nconsume,so[422]);
        if((MUT==0 && so[424])||(MUT!=0 && !so[424]))$fatal(1,"fault MUT%0d fault%0d",MUT,so[424]);
        $display("ECTL_STATIC PASS mutant=%0d req=%0d consume=%0d firstreq=%0d localstart=%0d firstconsume=%0d fault=%0d",MUT,nreq,nconsume,firstreq,startcyc,firstconsume,so[424]);$finish;
    end
endmodule
