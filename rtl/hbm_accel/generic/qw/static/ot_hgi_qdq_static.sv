`timescale 1ns/1ps
`default_nettype none
// Fixed-calendar QDQ beat engine. One compiler instruction = 32 FP32 values,
// four contiguous VM sectors. No ready, credits, queues, arbitration or rescheduling.
// Source/destination addresses are canonical 16-bit sector addresses, including SID.
// The compiler reserves all four read/write bank slots and excludes RAW/WAR/WAW
// until real macro commit. RL includes bank+station edges, measured at these pins.
// Faults report an invalid calendar; they never stall or extend that calendar.
// The actual released decoder is retained verbatim. Physical reuse of its views
// is conditional on matching phase and pin contract; this transport has no views yet.
module ot_hgi_qdq_static_transport #(
    parameter integer IO_REGS=0,
    parameter integer RL=7,
    parameter integer DL=25, // pipeline stages; post-input edge delta = 24
    parameter integer WC=4, // outgoing bank acceptance1 + actual macro commit3
    parameter integer MUT=0 // 1 wrong input sector permutation; 2 wrong write lane
) (
    input wire clk, rst_n,
    input wire cmd_v,
    input wire [5:0] cmd_op,
    input wire [7:0] cmd_block,
    input wire [15:0] cmd_src, cmd_dst,
    input wire cmd_last,
    output reg [8*17-1:0] rq,
    input wire [8*257-1:0] rr,
    output reg [8*281-1:0] wq,
    output reg beat_done, record_done,
    output reg fault,
    output wire dec_v,
    output wire [127:0] dec_header,
    output wire [1023:0] dec_x,
    input wire vo,qfault,decode_fault,
    input wire [511:0] y
);
    localparam integer NP=RL+1+IO_REGS;
    localparam integer ND=DL+IO_REGS;
    wire [8*257-1:0] rr_local;
    wire [511:0] y_local;
    wire vo_local,qfault_local,decode_fault_local;
    (* keep="true", dont_touch="true" *) reg [2:0] read_bank_local[0:3][0:7];
    (* keep="true", dont_touch="true" *) reg [2:0] write_bank_local[0:7];
    generate if(IO_REGS)begin: registered_boundary
        reg [8*257-1:0] rr_q;
        reg [511:0] y_q;
        reg vo_q,qfault_q,decode_fault_q;
        always @(posedge clk)begin rr_q<=rr;y_q<=y;end
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin vo_q<=0;qfault_q<=0;decode_fault_q<=0;end
            else begin vo_q<=vo;qfault_q<=qfault;decode_fault_q<=decode_fault;end
        assign rr_local=rr_q;assign y_local=y_q;
        assign vo_local=vo_q;assign qfault_local=qfault_q;assign decode_fault_local=decode_fault_q;
        always @(posedge clk)begin
            for(integer k=0;k<4;k=k+1)
                for(integer t=0;t<8;t=t+1)read_bank_local[k][t]<=sp[NP-2][2:0];
            for(integer b=0;b<8;b=b+1)write_bank_local[b]<=dst[ND-2][2:0];
        end
    end else begin: original_boundary
        assign rr_local=rr;assign y_local=y;
        assign vo_local=vo;assign qfault_local=qfault;assign decode_fault_local=decode_fault;
    end endgenerate
    reg [NP-1:0] vp, lp;
    reg [15:0] sp [0:NP-1], dp [0:NP-1];
    reg [13:0] hp [0:NP-1];
    reg gv, gl;
    reg [15:0] gd;
    reg [127:0] gh;
    reg [1023:0] gx;
    reg [ND-1:0] dv, dl;
    reg [WC-1:0] donep,lastp;
    reg [15:0] dst [0:ND-1];
    assign dec_v=gv;assign dec_header=gh;assign dec_x=gx;
    reg [7:0] expected;
    reg bad;
    always @* begin
        expected='0;
        for(integer t=0;t<4;t=t+1) if(vp[NP-1]) expected[(sp[NP-1][2:0]+t)&7]=1'b1;
        bad=1'b0;
        for(integer t=0;t<8;t=t+1) if(rr_local[t*257+256]!=expected[t]) bad=1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            vp<='0; lp<='0; gv<=0; gl<=0;
            dv<='0; dl<='0; donep<='0; lastp<='0; beat_done<=0; record_done<=0; fault<=0;
        end else begin
            vp<={vp[NP-2:0],cmd_v}; lp<={lp[NP-2:0],cmd_last};
            dv<={dv[ND-2:0],gv}; dl<={dl[ND-2:0],gl};
            gv<=vp[NP-1]; gl<=lp[NP-1];
            // Validates the fixed expected return cycle, including unexpected idle responses.
            if(bad || decode_fault_local || (vo_local && qfault_local) || vo_local!=dv[ND-1]) fault<=1;
            if(cmd_v && (!(cmd_op==4 || cmd_op==5 || (cmd_op==6 && cmd_block==16)) ||
                cmd_src[15:3] != ((cmd_src+16'd3)>>3) ||
                cmd_dst[15:3] != ((cmd_dst+16'd3)>>3))) fault<=1;
            donep<={donep[WC-2:0],dv[ND-1]};
            lastp<={lastp[WC-2:0],dv[ND-1]&&dl[ND-1]};
            beat_done<=donep[WC-1]; record_done<=lastp[WC-1];
        end
    end
    reg [8*17-1:0] rq_next;
    reg [8*281-1:0] wq_next;
    generate if(IO_REGS==0)begin: original_port_pack
    always @* begin
        rq_next='0;wq_next='0;
        for(integer k=0;k<4;k=k+1) begin : pack_ports
            reg [15:0] rs,ws;integer rb,wb;
            rs=cmd_src+16'(k);ws=dst[ND-1]+16'(k);
            rb=int'(rs[2:0]);wb=int'(ws[2:0])^(MUT==2?1:0);
            rq_next[rb*17+:17]={cmd_v,rs};
            wq_next[wb*281+:281]={dv[ND-1],ws,256'd0,8'hff};
            for(integer t=0;t<8;t=t+1)
                wq_next[wb*281+8+t*32+:32]={y[(k*8+t)*16+:16],16'd0};
        end
    end
    end else begin: constant_port_pack
        always @* begin
            rq_next='0;wq_next='0;
            for(integer b=0;b<8;b=b+1)begin
                for(integer k=0;k<4;k=k+1)begin
                    if(((int'(cmd_src[2:0])+k)&7)==b)
                        rq_next[b*17+:17]={cmd_v,cmd_src+16'(k)};
                    if((((int'(write_bank_local[b])+k)&7)^(MUT==2?1:0))==b)begin
                        wq_next[b*281+:281]={dv[ND-1],dst[ND-1]+16'(k),256'd0,8'hff};
                        for(integer t=0;t<8;t=t+1)
                            wq_next[b*281+8+t*32+:32]={y_local[(k*8+t)*16+:16],16'd0};
                    end
                end
            end
        end
    end endgenerate
    // Reset only validity; thousands of datapath bits are not reset-tree sinks.
    always @(posedge clk or negedge rst_n)
        if(!rst_n) for(integer k=0;k<8;k=k+1) begin rq[k*17+16]<=0;wq[k*281+280]<=0;end
        else for(integer k=0;k<8;k=k+1) begin rq[k*17+16]<=rq_next[k*17+16];wq[k*281+280]<=wq_next[k*281+280];end
    always @(posedge clk)
        for(integer k=0;k<8;k=k+1) begin rq[k*17+:16]<=rq_next[k*17+:16];wq[k*281+:280]<=wq_next[k*281+:280];end
    // No reset on datapath payload. Registers are bounded latency state, not memory substitutes.
    always @(posedge clk) begin
        sp[0]<=cmd_src; dp[0]<=cmd_dst; hp[0]<={cmd_op,cmd_block};
        for(integer k=1;k<NP;k=k+1) begin sp[k]<=sp[k-1]; dp[k]<=dp[k-1]; hp[k]<=hp[k-1]; end
        gd<=dp[NP-1]; gh<='0; gh[127:124]<=4'd4;
        gh[123:118]<=hp[NP-1][13:8]; gh[71:64]<=hp[NP-1][7:0];
        if(IO_REGS==0)begin
            for(integer k=0;k<4;k=k+1)
                gx[k*256+:256]<=rr[(((int'(sp[NP-1][2:0])+k)&7)^(MUT==1?1:0))*257+:256];
        end
        dst[0]<=gd;
        for(integer k=1;k<ND;k=k+1) dst[k]<=dst[k-1];
    end
    generate if(IO_REGS)begin: constant_read_lanes
        for(genvar k=0;k<4;k=k+1)begin: lane
            for(genvar t=0;t<8;t=t+1)begin: word_
                reg [31:0] selected;
                always @* begin
                    selected='0;
                    for(integer b=0;b<8;b=b+1)
                        if((((int'(read_bank_local[k][t])+k)&7)^(MUT==1?1:0))==b)
                            selected=selected|rr_local[b*257+t*32+:32];
                end
                always @(posedge clk)gx[k*256+t*32+:32]<=selected;
            end
        end
    end endgenerate
    initial if(RL<1 || DL<2 || WC<2) $fatal(1,"invalid measured QDQ pipeline");
endmodule
// Wires-only native engine. All five physical roots remain explicit at the
// enclosing programme parent. Decoder leaf arithmetic is unchanged dec3.
module ot_hgi_qdq_static #(
    parameter integer RL=7,DL=25,WC=4,MUT=0,IO_REGS=0,
    parameter integer TSPLIT=0 // 1: word-sliced transport (ot_hgi_qdq_static_transport_split), same edges; IO_REGS=1 only
                               // 2: r2 split (ot_hgi_qdq_static_transport_split_r2): cmd pin-capture control, +1 edge
)(
    input wire clk_transport,clk_dxl,clk_dbq,clk_daq,rst_n,
    input wire cmd_v,
    input wire [5:0] cmd_op,
    input wire [7:0] cmd_block,
    input wire [15:0] cmd_src,cmd_dst,
    input wire cmd_last,
    output wire [8*17-1:0] rq,
    input wire [8*257-1:0] rr,
    output wire [8*281-1:0] wq,
    output wire beat_done,record_done,fault
);
    wire v,vo,qfault,decode_fault;
    wire [127:0] header;wire [1023:0] x;
    wire [511:0] y;
    wire [17:0] hd={header[127:118],header[71:64]};
    wire [1023:0] xs,xb,xa;wire bvo,bfo;wire [511:0] byo;
    generate if(TSPLIT==2) begin: split_transport_r2
    ot_hgi_qdq_static_transport_split_r2 #(.IO_REGS(IO_REGS),.RL(RL),.DL(DL),.WC(WC),.MUT(MUT)) transport(
        .clk(clk_transport),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_op(cmd_op),.cmd_block(cmd_block),
        .cmd_src(cmd_src),.cmd_dst(cmd_dst),.cmd_last(cmd_last),.rq(rq),.rr(rr),.wq(wq),
        .beat_done(beat_done),.record_done(record_done),.fault(fault),
        .dec_v(v),.dec_header(header),.dec_x(x),.vo(vo),.qfault(qfault),.decode_fault(decode_fault),.y(y));
    end else if(TSPLIT!=0) begin: split_transport
    ot_hgi_qdq_static_transport_split #(.IO_REGS(IO_REGS),.RL(RL),.DL(DL),.WC(WC),.MUT(MUT)) transport(
        .clk(clk_transport),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_op(cmd_op),.cmd_block(cmd_block),
        .cmd_src(cmd_src),.cmd_dst(cmd_dst),.cmd_last(cmd_last),.rq(rq),.rr(rr),.wq(wq),
        .beat_done(beat_done),.record_done(record_done),.fault(fault),
        .dec_v(v),.dec_header(header),.dec_x(x),.vo(vo),.qfault(qfault),.decode_fault(decode_fault),.y(y));
    end else begin: monolith_transport
    ot_hgi_qdq_static_transport #(.IO_REGS(IO_REGS),.RL(RL),.DL(DL),.WC(WC),.MUT(MUT)) transport(
        .clk(clk_transport),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_op(cmd_op),.cmd_block(cmd_block),
        .cmd_src(cmd_src),.cmd_dst(cmd_dst),.cmd_last(cmd_last),.rq(rq),.rr(rr),.wq(wq),
        .beat_done(beat_done),.record_done(record_done),.fault(fault),
        .dec_v(v),.dec_header(header),.dec_x(x),.vo(vo),.qfault(qfault),.decode_fault(decode_fault),.y(y));
    end endgenerate
    ot_hgi_qw_dxl u_dxl(.clk(clk_dxl),.x(x),.xs(xs),.xb(xb),.xa(xa));
    ot_hgi_qw_dbq u_dbq(.clk(clk_dbq),.rst_n(rst_n),.v(v),.hd(hd),.xs(xs),.xb(xb),
        .bvo(bvo),.bfo(bfo),.byo(byo));
    ot_hgi_qw_daq u_daq(.clk(clk_daq),.rst_n(rst_n),.v(v),.hd(hd),.xs(xs),.xa(xa),
        .bvo(bvo),.bfo(bfo),.byo(byo),.vo(vo),.y(y),.fault(qfault),.decode_fault(decode_fault));
endmodule
`default_nettype wire
