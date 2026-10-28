`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-10 bench: one-owner crossing read on REAL q0_faces banks (no bank substitute).
//  owner half: 8 hfd_vms_bank_native_q0_faces banks (as vmb_Q0..7 of one hub half); every read of group XG is issued
//    by the OWNER schedule with the record; responses stream over hfd_vms_xread_link (LX edges) to the far stations.
//  far half: one q0_faces bank whose group-XG request pins are the dead-by-schedule tie (17'b0, xread_ties.json);
//    its other groups keep running local reads in the same cycles.
// Checks every cycle: far-station valid/data == owner read at n+6+PIN+LX (exact edge, exact SRAM row), no early or
// extra valid, far bank group XG never answers, no bank FAULT.  Mutant hooks: LMUT (link MUT 1/2/3), TMUT 1 = the
// tied pin carries a live request (the dead-by-schedule claim broken).
module tb_vms_xread_link;
    parameter integer LMUT=0, TMUT=0, LX=4, XG=2;
    localparam integer RG=5,WG=2,RB=3,WB=3,PIN=1,LANES=8;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    reg [8*RG*17-1:0] rq=0; reg [7:0] rslot_v=0,wslot_v=0; reg [8*RB-1:0] rslot=0; reg [8*WB-1:0] wslot=0;
    reg [8*WG*281-1:0] wq=0;
    wire [8*RG*257-1:0] rr; wire [143:0] status; wire [8*WG-1:0] wdone;
    for(genvar b=0;b<8;b=b+1)begin:own
        hfd_vms_bank_native_q0_faces m(.bid(3'(b)),.sid(2'd0),.clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),
          .clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(rst_n),.rslot_v(rslot_v[b]),.rslot(rslot[b*RB+:RB]),
          .wslot_v(wslot_v[b]),.wslot(wslot[b*WB+:WB]),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),
          .xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status[b*18+:18]),
          .rq0(rq[(b*RG+0)*17+:17]),.rr0(rr[(b*RG+0)*257+:257]),.rq1(rq[(b*RG+1)*17+:17]),.rr1(rr[(b*RG+1)*257+:257]),
          .rq2(rq[(b*RG+2)*17+:17]),.rr2(rr[(b*RG+2)*257+:257]),.rq3(rq[(b*RG+3)*17+:17]),.rr3(rr[(b*RG+3)*257+:257]),
          .rq4(rq[(b*RG+4)*17+:17]),.rr4(rr[(b*RG+4)*257+:257]),.wq0(wq[(b*WG)*281+:281]),.wq1(wq[(b*WG+1)*281+:281]),
          .wq_done0(wdone[b*WG]),.wq_done1(wdone[b*WG+1]));
    end
    // owner group-XG responses -> crossing link -> far stations
    wire [LANES*257-1:0] rr_own, rr_far;
    for(genvar b=0;b<8;b=b+1)begin:sel assign rr_own[b*257+:257]=rr[(b*RG+XG)*257+:257]; end
    hfd_vms_xread_link #(.LANES(LANES),.LX(LX),.MUT(LMUT)) link(.clk_stage({LX{clk}}),.rst_n(rst_n),.rr_owner(rr_own),.rr_far(rr_far));
    // far bank: group XG request pins = dead-by-schedule tie
    reg [16:0] far_rq0=0, far_live=0; reg far_rv=0; reg [2:0] far_rs=0;
    wire [256:0] far_rr0, far_rrx; wire [17:0] far_status;
    wire [16:0] far_rqx = (TMUT==1) ? far_live : 17'b0;   // production: TIELO at the pin
    hfd_vms_bank_native_q0_faces far(.bid(3'd1),.sid(2'd1),.clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),
          .clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(rst_n),.rslot_v(far_rv),.rslot(far_rs),
          .wslot_v(1'b0),.wslot(3'd0),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),
          .xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(far_status),
          .rq0(far_rq0),.rr0(far_rr0),.rq1(17'd0),.rr1(),.rq2(XG==2?far_rqx:17'd0),.rr2(far_rrx),.rq3(17'd0),.rr3(),
          .rq4(17'd0),.rr4(),.wq0(281'd0),.wq1(281'd0),.wq_done0(),.wq_done1());
    function automatic [255:0] payload(input integer b,row);
        for(integer w=0;w<8;w=w+1)payload[w*32+:32]=32'hbeaf1280^32'(b<<24)^32'(row<<9)^32'(w*31);
    endfunction
    reg [7:0] exp_v[0:4095]; reg [2047:0] exp_d[0:4095];
    integer cycle=0, issued=0, far_reads=0, far_local=0; reg far_local_exp[0:4095];
    task clear; begin rq=0;wq=0;rslot_v=0;wslot_v=0;rslot=0;wslot=0;far_rq0=0;far_live=0;far_rv=0;far_rs=0; end endtask
    task tick; integer row; begin
        @(posedge clk);
        if(rst_n)begin
            for(integer b=0;b<8;b=b+1) if(rslot_v[b]&&rslot[b*RB+:RB]==XG&&rq[(b*RG+XG)*17+16])begin
                row=int'(rq[(b*RG+XG)*17+3+:10]); issued=issued+1;
                exp_v[cycle+6+PIN+LX][b]=1; exp_d[cycle+6+PIN+LX][b*256+:256]=payload(b,row);
            end
            if(far_rv&&far_rs==0&&far_rq0[16]) far_local_exp[cycle+6+PIN]=1;
        end
        #2;
        if(rst_n)begin
            if(status!==0||far_status!==0)$fatal(1,"FATAL bank fault cycle=%0d",cycle);
            if(far_rrx[256]!==1'b0)$fatal(1,"FATAL dead-by-schedule tied group %0d answered cycle=%0d",XG,cycle);
            if(far_rr0[256]!==far_local_exp[cycle])$fatal(1,"FATAL far-half local read phase cycle=%0d",cycle);
            if(far_rr0[256])far_local=far_local+1;
            for(integer b=0;b<LANES;b=b+1)begin
                if(rr_far[b*257+256]!==exp_v[cycle][b])$fatal(1,"FATAL crossing valid phase cycle=%0d lane=%0d got=%b",cycle,b,rr_far[b*257+256]);
                if(exp_v[cycle][b])begin
                    if(rr_far[b*257+:256]!==exp_d[cycle][b*256+:256])$fatal(1,"FATAL crossing data cycle=%0d lane=%0d",cycle,b);
                    far_reads=far_reads+1;
                end
            end
        end
        cycle=cycle+1;@(negedge clk);
    end endtask
    initial begin
        integer row;
        for(integer c=0;c<4096;c=c+1)begin exp_v[c]=0;exp_d[c]=0;far_local_exp[c]=0;end
        repeat(3)tick();rst_n=1;repeat(3)@(negedge clk);
        for(row=0;row<128;row=row+1)begin
            clear();wslot_v=8'hff;
            for(integer b=0;b<8;b=b+1)begin wslot[b*WB+:WB]=WB'(row%WG);
                wq[(b*WG+(row%WG))*281+:281]={1'b1,1'b0,2'd0,10'(row),3'(b),payload(b,row),8'hff}; end
            tick();
        end
        clear();repeat(8)tick();
        // owner-issued streaming read: every bank, every cycle, one row on group XG (sparse gaps every 7th cycle);
        // far half reads its own bank on group 0 in the same cycles; TMUT 1 also drives the tied group.
        for(integer t=0;t<256;t=t+1)begin
            clear();
            for(integer b=0;b<8;b=b+1) if((t+b)%7!=3)begin
                rslot_v[b]=1;rslot[b*RB+:RB]=RB'(XG);rq[(b*RG+XG)*17+:17]={1'b1,1'b0,2'd0,10'((t*5+b*11)%128),3'(b)}; end
            far_rv=1; far_rs=(TMUT==1&&t==40)?3'(XG):3'd0; far_rq0={1'b1,1'b0,2'd1,10'(t%64),3'd1};
            far_live={1'b1,1'b0,2'd1,10'd5,3'd1};
            tick();
        end
        clear();repeat(12)tick();
        if(far_reads!=issued||issued<1700)$fatal(1,"FATAL crossing inventory %0d",far_reads);
        $display("XREAD_LINK PASS lanes=%0d LX=%0d XG=%0d crossing_reads=%0d far_local_reads=%0d edge=n+6+PIN+LX exact; tied group never answered",LANES,LX,XG,far_reads,far_local);
        $finish;
    end
endmodule
`default_nettype wire
