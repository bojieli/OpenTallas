`timescale 1ns/1ps
// Minimum real hctl -> descriptor tap -> native CP arithmetic/SRAM seam.
// Other SU engines are absent. VM/previous FIELD operands are declared fixtures.
module tb_s81_su_cp_endpoint;
    parameter integer MUT=0;
    reg clk=0;always #0.416667 clk=~clk;
    reg rst_n=0,cmd_v=0;reg [83:0] cmd=0;
    wire ready,done,ctl_fault,busy;wire [7:0]tag;wire [3:0]fcode;wire[31:0]jobs;
    wire dn_st;wire[3:0]dn_kind;wire[1:0]gsel;wire fp4;wire[7:0]jid;
    wire[15:0]ctl_rq,rv;wire[223:0]ctl_rows;wire[479:0]fields;
    wire[1:0]cp_rq,cp_rv;wire[27:0]cp_rows;
    wire[15:0]rq=ctl_rq|{14'd0,cp_rq};
    wire[223:0]rows={ctl_rows[223:28],cp_rq[1]?cp_rows[27:14]:ctl_rows[27:14],cp_rq[0]?cp_rows[13:0]:ctl_rows[13:0]};
    wire[8191:0]rd;
    wire cp_start,cp_done,tap_fault,cp_fault,wv;wire[511:0]descriptor,wd;
    wire[13:0]wa;wire[15:0]wm,scheduled;
    ot_s81_su_hctl u_ctl(.clk(clk),.rst_n(rst_n),.e_cmd_v(cmd_v),.e_cmd_d(cmd),.e_cmd_ready(ready),
        .e_done_v(done),.e_done_tag(tag),.rq_v(ctl_rq),.rq_row(ctl_rows),.rs_v(rv),.rs_f(fields),
        .busy(busy),.fault(ctl_fault),.fault_code(fcode),.st_jobs(jobs),.dn_st(dn_st),.dn_kind(dn_kind),
        .dn_gsel(gsel),.dn_fp4(fp4),.dn_jid(jid),.up_v({15'd0,wv}),.up_fu(tap_fault|cp_fault),
        .up_fo(1'b0),.up_alive(1'b1),.up_den(1'b1),.up_rdy(1'b1),.up_rjid(8'd0),.up_cp_done(cp_done));
    ot_s81_su_cpt u_tap(.clk(clk),.rst_n(rst_n),.dn_st(dn_st),.dn_kind(dn_kind),.dn_v(rv),.dn_d(rd[511:0]),
        .cp_done(cp_done),.start(cp_start),.descriptor(descriptor),.cp_rs_v(cp_rv),.fault(tap_fault));
    ot_s81_su_cp_vm #(.MUT(MUT)) u_cp(.clk(clk),.ck_cp_ctl(clk),.ck_cp_mem({2{clk}}),.ck_cp_lane({4{clk}}),
        .rst_n(rst_n),.start(cp_start),.descriptor(descriptor),.rq_v(cp_rq),.rq_row(cp_rows),
        .rs_v(cp_rv),.rs_d(rd[1023:0]),.wq_v(wv),.wq_row(wa),.wq_d(wd),.wq_mask(wm),
        .done(cp_done),.fault(cp_fault),.scheduled_cycles(scheduled));
    reg[511:0]mem[0:16383];reg[127:0]expected[0:127];
    reg[15:0]vp[0:10];reg[8191:0]dp[0:10];integer late=0,i,k;
    assign rv=vp[late?10:9];assign rd=dp[late?10:9];
    genvar n;generate for(n=0;n<16;n=n+1)begin:g_fields
        assign fields[30*n+:30]={rd[512*n+64+:16],rd[512*n+32+:14]};
    end endgenerate
    always @(posedge clk)begin
        vp[0]<=rst_n?rq:0;
        for(i=0;i<16;i=i+1)dp[0][512*i+:512]<=mem[rows[14*i+:14]];
        for(i=1;i<11;i=i+1)begin vp[i]<=rst_n?vp[i-1]:0;dp[i]<=dp[i-1];end
    end
    integer d0,d1,slot,t,errors=0,nout=0,first=-1,last=-1,request_rows=0;
    string dir,vmfile;
    initial begin
        if(!$value$plusargs("DIR=%s",dir)||!$value$plusargs("VM=%s",vmfile)||
           !$value$plusargs("D0=%d",d0)||!$value$plusargs("D1=%d",d1))$fatal(1,"actual builder fixture required");
        if($value$plusargs("LATE=%d",late))begin end
        $readmemh(vmfile,mem);$readmemh({dir,"/expected.mem"},expected);
        repeat(8)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
        for(slot=0;slot<2;slot=slot+1)begin
            if(!ready)$fatal(1,"controller not ready before compiled command");
            cmd=0;cmd[30:7]=(14<<20)|(slot?d1:d0);cmd[6:0]=slot;
            cmd_v=1;@(negedge clk);cmd_v=0;request_rows=0;
            for(t=1;t<400;t=t+1)begin
                @(negedge clk);
                if(|(ctl_rq[1:0]&cp_rq))errors=errors+1;
                for(k=0;k<16;k=k+1)if(rq[k])request_rows=request_rows+1;
                if(wv)begin
                    if(slot!=1||nout>=32)errors=errors+1;
                    else if(wa!=mem[d1][0+:14]+nout || wm!=16'hffff ||
                            wd!=={expected[4*nout+3],expected[4*nout+2],expected[4*nout+1],expected[4*nout]})begin
                        errors=errors+1;if(errors<5)$display("BAD row%0d address%0d",nout,wa);
                    end
                    nout=nout+1;if(first<0)first=t;last=t;
                end
                if(done)begin
                    $display("CP_ENDPOINT_DONE slot%0d cycles%0d fault%0d rows%0d requests%0d tag%0d",slot,t,ctl_fault|tap_fault|cp_fault,nout,request_rows,tag);
                    if(tag!=slot||request_rows!=65)errors=errors+1;
                    break;
                end
            end
            if(!done||ctl_fault||tap_fault||cp_fault)begin
                errors=errors+1;
                if(late)begin
                    $display("CP_ENDPOINT_RESULT errors%0d fault%0d rows%0d",errors,ctl_fault|tap_fault|cp_fault,nout);
                    $fatal(1,"CP_ENDPOINT FAIL");
                end
            end
            repeat(3)@(negedge clk);
        end
        if(nout!=32||jobs!=2)errors=errors+1;
        $display("CP_ENDPOINT_RESULT errors%0d rows%0d first%0d last%0d",errors,nout,first,last);
        if(errors)$fatal(1,"CP_ENDPOINT FAIL");
        $display("CP_ENDPOINT PASS");$finish;
    end
endmodule
