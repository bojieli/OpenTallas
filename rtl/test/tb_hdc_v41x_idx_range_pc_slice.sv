`timescale 1ns/1ps
module tb_hdc_v41x_idx_range_pc_slice;
    localparam integer AW=28,LENW=4,TAGW=16,BEATW=4,DW=256;
    reg clk=0,rst_n=0;
    always #5 clk=~clk;
    reg [3:0] iv=0,ordy=0;
    reg [4*AW-1:0] ia=0;
    reg [4*LENW-1:0] il=0;
    reg [4*TAGW-1:0] it=0;
    reg hrdy=0,rv=0;
    reg [TAGW-1:0] rt=0;
    reg [BEATW-1:0] rb=0;
    reg [DW-1:0] rd=0;
    wire [3:0] srdy,prdy,sv,pv;
    wire shv,phv,shrr,phrr;
    wire [AW-1:0] sha,pha;
    wire [LENW-1:0] shl,phl;
    wire [TAGW-1:0] sht,pht,st;
    wire [4*TAGW-1:0] pt;
    wire [BEATW-1:0] sb;
    wire [4*BEATW-1:0] pb;
    wire [DW-1:0] sd;
    wire [4*DW-1:0] pd;
    ot_hdc_v41x_idx_range_pc_slice #(.QUANTUM(128)) slice (
        .clk(clk),.rst_n(rst_n),.i_req_v(iv),.i_req_rdy(srdy),
        .i_req_addr(ia),.i_req_len(il),.i_req_tag(it),
        .h_req_v(shv),.h_req_rdy(hrdy),.h_req_addr(sha),
        .h_req_len(shl),.h_req_tag(sht),
        .h_rsp_v(rv),.h_rsp_rdy(shrr),.h_rsp_tag(rt),
        .h_rsp_beat(rb),.h_rsp_data(rd),
        .o_rsp_v(sv),.o_rsp_rdy(ordy),.o_rsp_tag(st),
        .o_rsp_beat(sb),.o_rsp_data(sd));
    ot_hdc_v41x_idx_range_pc_arb #(.NPC(1),.AW(AW),.LENW(LENW),
        .TAGW(TAGW),.BEATW(BEATW),.DW(DW),.QUANTUM(128)) parent (
        .clk(clk),.rst_n(rst_n),.i_req_v(iv),.i_req_rdy(prdy),
        .i_req_addr(ia),.i_req_len(il),.i_req_tag(it),
        .h_req_v(phv),.h_req_rdy(hrdy),.h_req_addr(pha),
        .h_req_len(phl),.h_req_tag(pht),
        .h_rsp_v(rv),.h_rsp_rdy(phrr),.h_rsp_tag(rt),
        .h_rsp_beat(rb),.h_rsp_data(rd),
        .o_rsp_v(pv),.o_rsp_rdy(ordy),.o_rsp_tag(pt),
        .o_rsp_beat(pb),.o_rsp_data(pd),.dbg_grants());
    integer cyc,c,j;
    initial begin
        repeat(4) @(negedge clk);rst_n=1;
        for(cyc=0;cyc<2000;cyc=cyc+1) begin
            @(negedge clk);
            iv=4'($urandom);ordy=4'($urandom);
            hrdy=1'($urandom);rv=1'($urandom);
            rb=BEATW'($urandom);
            rt=TAGW'($urandom);
            for(j=0;j<4;j=j+1) begin
                ia[j*AW +:AW]=AW'($urandom);
                il[j*LENW +:LENW]=LENW'($urandom);
                it[j*TAGW +:TAGW]=TAGW'($urandom)&16'hcfff;
            end
            for(j=0;j<DW/32;j=j+1) rd[j*32 +:32]=$urandom;
            #1;
            if({srdy,shv,sha,shl,sht,shrr,sv} !==
               {prdy,phv,pha,phl,pht,phrr,pv})
                $fatal(1,"slice request/valid differs cycle=%0d",cyc);
            for(j=0;j<4;j=j+1) if(pv[j]) begin
                if(pt[j*TAGW +:TAGW] !== st ||
                   pb[j*BEATW +:BEATW] !== sb ||
                   pd[j*DW +:DW] !== sd)
                    $fatal(1,"slice response differs cycle=%0d ctx=%0d",cyc,j);
            end
        end
        $display("V41X_RANGE_PC_SLICE_PASS cycles=%0d",cyc);
        $finish;
    end
endmodule
