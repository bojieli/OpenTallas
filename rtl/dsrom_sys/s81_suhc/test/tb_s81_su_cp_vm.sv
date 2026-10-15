`timescale 1ns/1ps
module tb_s81_su_cp_vm;
    parameter integer MUT=0, LATE=0;
    reg clk=0;always #0.416667 clk=~clk;
    reg rst_n=0,start=0;reg[511:0] desc=0;
    wire[1:0]rqv;wire[27:0]rqa;wire[1:0]rsv;wire[1023:0]rsd;
    wire wv,dn,flt;wire[13:0]wa;wire[511:0]wd;wire[15:0]wm,sch;
    ot_s81_su_cp_vm #(.MUT(MUT)) dut(
        .clk(clk),.ck_cp_ctl(clk),.ck_cp_mem({2{clk}}),.ck_cp_lane({4{clk}}),
        .rst_n(rst_n),.start(start),.descriptor(desc),.rq_v(rqv),.rq_row(rqa),.rs_v(rsv),.rs_d(rsd),
        .wq_v(wv),.wq_row(wa),.wq_d(wd),.wq_mask(wm),.done(dn),.fault(flt),.scheduled_cycles(sch));
    reg[255:0]inp[0:255];reg[127:0]exp[0:127];
    reg[511:0]mem[0:1023];
    localparam integer LAT=11;
    integer late=LATE;
    reg[1:0]vpipe[0:LAT-1];reg[1023:0]dpipe[0:LAT-1];integer p;
    assign rsv=vpipe[late?10:9];assign rsd=dpipe[late?10:9];
    always @(posedge clk)begin
        vpipe[0]<=rst_n?rqv:0;
        dpipe[0]<={mem[rqa[14+:14]],mem[rqa[0+:14]]};
        for(p=1;p<LAT;p=p+1)begin vpipe[p]<=rst_n?vpipe[p-1]:0;dpipe[p]<=dpipe[p-1];end
    end
    integer errors=0,nout=0,nreq=0,slot,t,j,k,first=-1,last=-1;
    string dir;
    initial begin
        if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR required");
        if($value$plusargs("LATE=%d",late))begin end
        $readmemh({dir,"/in.mem"},inp);$readmemh({dir,"/expected.mem"},exp);
        for(j=0;j<1024;j=j+1)mem[j]=0;
        for(slot=0;slot<2;slot=slot+1)
            for(j=0;j<32;j=j+1)for(k=0;k<4;k=k+1)begin
                mem[100+300*slot+j][128*k+:128]=inp[128*slot+4*j+k][0+:128];
                mem[200+300*slot+j][128*k+:128]=inp[128*slot+4*j+k][128+:128];
            end
        repeat(8)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
        for(slot=0;slot<2;slot=slot+1)begin
            desc=0;desc[0+:32]=700;desc[32+:32]=100+300*slot;desc[64+:32]=512;
            desc[96+:32]=200+300*slot;desc[128+:32]=32'h10002;desc[160+:32]=slot?3:0;
            start=1;@(negedge clk);start=0;
            for(t=1;t<=300;t=t+1)begin
                @(negedge clk);
                if(wv)begin
                    if(slot!=1 || nout>=32)errors=errors+1;
                    else if(wa!=700+nout || wm!=16'hffff || wd!=={exp[4*nout+3],exp[4*nout+2],exp[4*nout+1],exp[4*nout]})begin
                        errors=errors+1;
                        if(errors<5)$display("BAD row%0d address%0d got%h",nout,wa,wd);
                    end
                    nout=nout+1;if(first<0)first=t;last=t;
                end
                if(dn)begin
                    $display("CP_VM_DONE slot%0d cycles%0d scheduled%0d fault%0d rows%0d",slot,t,sch,flt,nout);
                    if(t!=(slot?272:139))errors=errors+1;
                    break;
                end
            end
            if(!dn || flt)errors=errors+1;
            @(negedge clk);@(negedge clk);
        end
        if(nout!=32)errors=errors+1;
        $display("CP_VM_RESULT errors%0d rows%0d first%0d last%0d",errors,nout,first,last);
        if(errors)$fatal(1,"CP_VM FAIL");
        $display("CP_VM PASS");$finish;
    end
endmodule
