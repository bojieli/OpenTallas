`timescale 1ns/1ps
// Deterministic two-user index/KV overlap test.  The stack endpoint is a
// one-entry per-PC responder so the measured effect is arbiter service and
// backpressure, not a claim about the separate weight-HBM timing model.
module tb_chip_v41x_hbm_arb_concurrent;
`ifdef HDC_KARB_PIPE
    localparam integer PIPE=1;
`else
    localparam integer PIPE=0;
`endif
    localparam integer NPC=32, AW=28, TAGW=16, DW=256, BCNT=256, KCNT=2048;
    reg clk=0; always #1 clk=~clk;
    reg rst_n=0;
    reg [NPC-1:0] b_v='0, b_rsp_rdy;
    wire [NPC-1:0] b_rdy,b_wr_done,b_rsp_v;
    reg [NPC*AW-1:0] b_addr='0;
    reg [NPC*4-1:0] b_len='0;
    reg [NPC*TAGW-1:0] b_tag='0;
    wire [NPC*TAGW-1:0] b_rsp_tag;
    wire [NPC*4-1:0] b_rsp_beat;
    wire [NPC*DW-1:0] b_rsp_data;
    reg k_v=0,k_rsp_rdy=0;
    wire k_rdy,k_wr_done,k_rsp_v;
    reg [AW-1:0] k_addr='0;
    reg [TAGW-1:0] k_tag='0;
    wire [TAGW-1:0] k_rsp_tag;
    wire [3:0] k_rsp_beat;
    wire [DW-1:0] k_rsp_data;
    wire [NPC-1:0] h_v,h_rdy,h_we,h_wr_done,r_v,r_rdy;
    wire [NPC*AW-1:0] h_addr;
    wire [NPC*4-1:0] h_len,r_beat;
    wire [NPC*(TAGW+1)-1:0] h_tag,r_tag;
    wire [NPC*DW-1:0] h_wdata,r_data;
    wire [NPC*DW/8-1:0] h_wstrb;
    wire [31:0] kg,bg,cont;
    ot_chip_v41x_hbm_karb #(.NPC(NPC),.AW(AW),.TAGW(TAGW),.DW(DW),
                              .PIPE_OUT(PIPE),.PIPE_RSP(PIPE)) dut (
        .clk(clk),.rst_n(rst_n),.b_v(b_v),.b_rdy(b_rdy),.b_addr(b_addr),.b_len(b_len),.b_tag(b_tag),
        .b_we({NPC{1'b0}}),.b_wdata({NPC*DW{1'b0}}),.b_wstrb({NPC*DW/8{1'b0}}),
        .b_wr_done(b_wr_done),.b_rsp_v(b_rsp_v),.b_rsp_rdy(b_rsp_rdy),
        .b_rsp_tag(b_rsp_tag),.b_rsp_beat(b_rsp_beat),.b_rsp_data(b_rsp_data),
        .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(4'd1),.k_tag(k_tag),
        .k_we(1'b0),.k_wdata({DW{1'b0}}),.k_wstrb({DW/8{1'b0}}),.k_wr_done(k_wr_done),
        .k_rsp_v(k_rsp_v),.k_rsp_rdy(k_rsp_rdy),.k_rsp_tag(k_rsp_tag),.k_rsp_beat(k_rsp_beat),
        .k_rsp_data(k_rsp_data),.h_v(h_v),.h_rdy(h_rdy),.h_addr(h_addr),.h_len(h_len),
        .h_tag(h_tag),.h_we(h_we),.h_wdata(h_wdata),.h_wstrb(h_wstrb),.h_wr_done(h_wr_done),
        .r_v(r_v),.r_rdy(r_rdy),.r_tag(r_tag),.r_beat(r_beat),.r_data(r_data),
        .k_grants(kg),.b_grants(bg),.contended(cont));
    function automatic [AW-1:0] baddress(input integer pc, input integer seq);
        baddress=AW'(32'h1000 + (seq&1)*32'h4000 + pc*BCNT*2 + seq*2);
    endfunction
    function automatic [AW-1:0] kaddress(input integer seq);
        kaddress=AW'(32'h200000 + (seq&1)*32'h8000 + seq*2);
    endfunction
    function automatic [DW-1:0] datum(input [AW-1:0] address);
        datum={8{32'(address ^ 28'h95ac30)}};
    endfunction
    reg [NPC-1:0] qv=0;
    reg [NPC*(TAGW+1)-1:0] qt='0;
    reg [NPC*DW-1:0] qd='0;
    genvar g;
    generate for (g=0;g<NPC;g=g+1) begin : g_mem
        assign h_rdy[g]=!qv[g] || r_rdy[g];
        assign r_v[g]=qv[g];
        assign r_tag[g*(TAGW+1)+:TAGW+1]=qt[g*(TAGW+1)+:TAGW+1];
        assign r_beat[g*4+:4]=4'd0;
        assign r_data[g*DW+:DW]=qd[g*DW+:DW];
        assign h_wr_done[g]=1'b0;
        always @(posedge clk) if (!rst_n) qv[g]<=1'b0;
        else if (h_rdy[g]) begin
            qv[g]<=h_v[g];
            if (h_v[g]) begin
                qt[g*(TAGW+1)+:TAGW+1]<=h_tag[g*(TAGW+1)+:TAGW+1];
                qd[g*DW+:DW]<=datum(h_addr[g*AW+:AW]);
            end
        end
    end endgenerate
    integer cycle=0, p, seq, bad=0, b_done=0, k_done=0;
    integer b_sent[0:NPC-1], b_recv[0:NPC-1];
    integer b_time[0:NPC-1][0:BCNT-1], k_time[0:KCNT-1];
    integer b_lat=0,k_lat=0,b_max=0,k_max=0,b_user[0:1],k_user[0:1];
    initial begin
        for(p=0;p<NPC;p=p+1) begin b_sent[p]=0; b_recv[p]=0; end
        b_user[0]=0;b_user[1]=0;k_user[0]=0;k_user[1]=0;
        b_rsp_rdy={NPC{1'b1}};
        repeat(3) @(negedge clk);
        rst_n=1;
        for(cycle=0;cycle<12000;cycle=cycle+1) begin
            @(negedge clk);
            k_v=(k_done<KCNT);
            k_tag=TAGW'(k_done);
            k_addr=kaddress(k_done);
            k_rsp_rdy=(cycle%13!=0);
            for(p=0;p<NPC;p=p+1) begin
                b_v[p]=(b_sent[p]<BCNT);
                b_addr[p*AW+:AW]=baddress(p,b_sent[p]);
                b_tag[p*TAGW+:TAGW]=TAGW'(b_sent[p]);
                b_len[p*4+:4]=4'd1;
            end
            @(posedge clk);
            for(p=0;p<NPC;p=p+1) if(b_v[p] && b_rdy[p]) begin
                b_time[p][b_sent[p]]=cycle;
                b_sent[p]=b_sent[p]+1;
            end
            if(k_v && k_rdy) begin k_time[k_done]=cycle; k_done=k_done+1; end
            for(p=0;p<NPC;p=p+1) if(b_rsp_v[p] && b_rsp_rdy[p]) begin
                seq=integer'(b_rsp_tag[p*TAGW+:TAGW]);
                if(seq>=BCNT || b_rsp_data[p*DW+:DW]!==datum(baddress(p,seq)) || b_rsp_beat[p*4+:4]!=0)
                    bad=bad+1;
                else begin
                    b_lat=b_lat+cycle-b_time[p][seq];
                    if(cycle-b_time[p][seq]>b_max) b_max=cycle-b_time[p][seq];
                    b_user[seq&1]=b_user[seq&1]+1;
                end
                b_recv[p]=b_recv[p]+1;b_done=b_done+1;
            end
            if(k_rsp_v && k_rsp_rdy) begin
                seq=integer'(k_rsp_tag);
                if(seq>=KCNT || k_rsp_data!==datum(kaddress(seq)) || k_rsp_beat!=0) bad=bad+1;
                else begin
                    k_lat=k_lat+cycle-k_time[seq];
                    if(cycle-k_time[seq]>k_max) k_max=cycle-k_time[seq];
                    k_user[seq&1]=k_user[seq&1]+1;
                end
            end
            if(b_done==NPC*BCNT && k_user[0]+k_user[1]==KCNT) begin
                if(bad!=0) $fatal(1,"bad=%0d",bad);
                $display("PASS pipe=%0d cycles=%0d b_done=%0d k_done=%0d b_lat_sum=%0d k_lat_sum=%0d b_max=%0d k_max=%0d b_u0=%0d b_u1=%0d k_u0=%0d k_u1=%0d bg=%0d kg=%0d cont=%0d",
                         PIPE,cycle,b_done,KCNT,b_lat,k_lat,b_max,k_max,b_user[0],b_user[1],k_user[0],k_user[1],bg,kg,cont);
                $finish;
            end
        end
        $fatal(1,"timeout bad=%0d b_done=%0d k_done=%0d",bad,b_done,k_user[0]+k_user[1]);
    end
endmodule
