`timescale 1ns/1ps
// One rank's actual WN A/B stage circuit. Same endpoint, physical lane RTL,
// relay/landing legs and cable model as tb_xdie_s81_2 XL5/MU2/LEG1.
// Inputs are exact dp2 projections of that bench's immutable six-position image;
// no dates, payloads, tags or idle clocks are compressed or regenerated.
module tb_mtp_wn_positions #(
    parameter integer NSMAX=3841, NMMAX=49, QD=3841, MAXCYC=6315716,
    parameter integer D_ST=258
);
    reg clk=0; always #0.4167 clk=~clk;
    reg rst_n=0, go=0;
    integer cyc=0; always @(posedge clk) cyc<=cyc+1;
    reg [1103:0] ri=0;
    reg [33:0] muc=0;
    wire [1103:0] ro,lri;
    wire [31:0] mrt;
    wire [2175:0] ptx,prx;
    wire fault; wire [3:0] live;
    xdie_s81_2_ep #(.SIDE(0),.HOST(0),.MU(2),.AB(1),.LEG(1),
        .LRXS(1),.LINP(1),.LN32(1)) u_ep (
        .clk(clk),.rst_n(rst_n),.sid(4'd1),.ch_b(1'b1),
        .ri_n(ri),.ro_n(ro),.pma_tx(ptx),.pma_rx(prx),
        .mu_c(muc),.mu_rt(mrt),.lep_ri(lri),.fault(fault),.live(live));
    genvar l;
    generate for(l=0;l<4;l=l+1) begin:g_c
        localparam integer SL=(l<2)?l+2:l-2;
        xdie2_chan #(.W(544),.D(D_ST)) u_ch (
            .clk(clk),.errp(32'd0),.extra(32'd0),
            .d(ptx[544*SL+:544]),.q(prx[544*l+:544]));
    end endgenerate
    reg [1175:0] stim[0:NSMAX-1];
    reg [79:0] mcmd[0:NMMAX-1];
    reg [1103:0] sent[0:QD-1];
    integer issue[0:QD-1],deadline[0:QD-1];
    integer ns=0,nm=0,si=0,mi=0,nsent=0,nrecv=0;
    integer bad=0,extra=0,late=0,tagbad=0,ntag=0,ntag_exp=0;
    integer minage=2147483647,maxage=0;
    reg fseen=0;
    initial begin
        if(!$value$plusargs("NS=%d",ns)) $fatal(1,"NS required");
        if(!$value$plusargs("NM=%d",nm)) $fatal(1,"NM required");
        if(ns<=0||ns>=NSMAX||nm<=0||nm>=NMMAX||ns>=QD)
            $fatal(1,"derived inventory exceeds capacity");
        $readmemh("stim.hex",stim); $readmemh("mu.hex",mcmd);
        $display("WN_CFG NS %0d NM %0d MAXCYC %0d D_ST %0d real_lanes 4",ns,nm,MAXCYC,D_ST);
        repeat(8) @(posedge clk); rst_n=1; go=1;
    end
    reg [1175:0] w;
    always @(negedge clk) if(go) begin
        ri=0; muc=0;
        while(mi<nm&&mcmd[mi][79:48]==cyc+1) begin
            if(mcmd[mi][47:40]!=2) $fatal(1,"non-WN command in projection");
            muc=mcmd[mi][33:0]; mi=mi+1;
        end
        while(si<ns&&stim[si][1143:1112]==cyc+1) begin
            w=stim[si];
            if(w[1111:1104]!=2||ri[0]||nsent>=QD) $fatal(1,"invalid WN issue inventory");
            ri=w[1103:0]; sent[nsent]=w[1103:0];
            issue[nsent]=cyc+1; deadline[nsent]=w[1175:1144]; nsent=nsent+1;
            if(w[13]) ntag_exp=ntag_exp+1;
            si=si+1;
        end
    end
    function automatic [1103:0] hopsm2(input [1103:0] b);
        begin hopsm2=b; hopsm2[8:4]=b[8:4]-5'd2; end
    endfunction
    reg [31:0] texp;
    integer age;
    always @(posedge clk) if(go) begin
        fseen=fseen|fault;
        if(lri[0]) begin
            texp=lri[13]?{1'b1,lri[23:14],lri[44:24]}:32'd0;
            if(mrt!==texp) begin tagbad=tagbad+1;$display("TAGBAD cyc %0d",cyc);end
            if(mrt[31]) ntag=ntag+1;
        end else if(mrt!==0) begin tagbad=tagbad+1;$display("TAGBAD idle cyc %0d",cyc);end
        if(ro[0]) begin
            if(ro[12:9]!=2||nrecv>=nsent) extra=extra+1;
            else begin
                if(ro!==hopsm2(sent[nrecv])) begin
                    bad=bad+1;$display("MISMATCH k %0d cyc %0d",nrecv,cyc);
                end
                if(deadline[nrecv]!=0&&cyc>deadline[nrecv]) late=late+1;
                age=cyc-issue[nrecv]; if(age<minage)minage=age;if(age>maxage)maxage=age;
                $display("WN_LAND %0d %0d %0d %0d %0d",ro[1095:1088],nrecv,issue[nrecv],cyc,deadline[nrecv]);
            end
            nrecv=nrecv+1;
        end
    end
    initial begin
        wait(go);
        while(nrecv<ns&&cyc<MAXCYC) @(posedge clk);
        repeat(2000) @(posedge clk);
        $display("WN_STATS beats %0d landed %0d mismatch %0d extra %0d late %0d tags %0d/%0d tagbad %0d fault %b live %b minage %0d maxage %0d last_cycle %0d",
            ns,nrecv,bad,extra,late,ntag,ntag_exp,tagbad,fseen,live,minage,maxage,cyc);
        if(nrecv==ns&&nsent==ns&&mi==nm&&bad==0&&extra==0&&late==0&&ntag==ntag_exp&&tagbad==0&&!fseen&&live==4'b1111)
            $display("PASS mtp_wn_positions: exact six-position timeline, data, tags and real path");
        else $display("FAIL mtp_wn_positions");
        $finish;
    end
endmodule
