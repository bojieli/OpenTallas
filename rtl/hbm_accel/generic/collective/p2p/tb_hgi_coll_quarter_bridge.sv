`timescale 1ns/1ps
module tb_hgi_coll_quarter_bridge;
    parameter integer MUT_SELECT=0,MUT_FAULT=0;
    localparam CYCLES=700;
    reg clk=0,rst_n=0;
    always #5 clk=~clk;
    wire [7:0] ov[0:3];
    wire [8*545-1:0] od[0:3];
    wire [15:0] fault[0:3];
    reg [4:0] ev[0:3];
    reg [7:0] slot[0:3];
    reg [23:0] sel[0:3];
    reg injv[0:3];
    reg [544:0] inj[0:3];
    reg [4:0] plan_ev[0:CYCLES-1][0:3];
    reg [7:0] plan_slot[0:CYCLES-1][0:3];
    reg [23:0] plan_sel[0:CYCLES-1][0:3];
    reg plan_injv[0:CYCLES-1][0:3];
    reg [544:0] plan_inj[0:CYCLES-1][0:3];
    reg [7:0] check_v[0:CYCLES-1][0:3];
    reg [8*545-1:0] check_d[0:CYCLES-1][0:3];
    integer total=0;
    wire rx_v;
    wire [1:0] rx_fault;
    wire [544:0] rx_d,relay1_d,relay2_d;
    wire relay1_v,relay2_v;
    ot_hgi_coll_quarter_bridge_mux #(.NS(2)) rx_face(
        .clk(clk),.rst_n(rst_n),.src_v({ov[0][3],injv[0]}),
        .src_d({od[0][3*545+:545],inj[0]}),.expect_v({ov[0][3],injv[0]}),
        .slot(ov[0][3]),.select(1'b1),.out_v(rx_v),.out_d(rx_d),.fault(rx_fault));
    ot_hgi_coll_quarter_bridge_relay relay1(.clk(clk),.rst_n(rst_n),
        .in_v(ov[0][0]),.in_d(od[0][0+:545]),.out_v(relay1_v),.out_d(relay1_d));
    ot_hgi_coll_quarter_bridge_relay relay2(.clk(clk),.rst_n(rst_n),
        .in_v(relay1_v),.in_d(relay1_d),.out_v(relay2_v),.out_d(relay2_d));
    function integer nextq(input integer q);
        case(q) 0:nextq=1;1:nextq=3;3:nextq=2;default:nextq=0;endcase
    endfunction
    function integer prevq(input integer q);
        case(q) 0:prevq=2;2:prevq=3;3:prevq=1;default:prevq=0;endcase
    endfunction
    for(genvar q=0;q<4;q=q+1) begin:gq
        localparam N=q==0?3:2, NS=N+2, ND=2*N+2;
        localparam PREV=q==0?2:q==1?0:q==3?1:3;
        localparam NEXT=q==0?1:q==1?3:q==3?2:0;
        localparam PN=PREV==0?3:2, NN=NEXT==0?3:2;
        wire [NS-1:0] sv;
        wire [NS*545-1:0] sd;
        assign sv={{ov[NEXT][2*NN+1],ov[PREV][2*PN]}, {(N-1){1'b0}},injv[q]};
        assign sd={od[NEXT][(2*NN+1)*545+:545],od[PREV][2*PN*545+:545],{((N-1)*545){1'b0}},inj[q]};
        if(ND<8) begin
            assign ov[q][7:ND]=0;assign od[q][8*545-1:ND*545]=0;assign fault[q][15:ND*2]=0;
        end
        wire [ND*$clog2(NS)-1:0] compact_sel;
        for(genvar d=0;d<ND;d=d+1) begin
            assign compact_sel[d*$clog2(NS)+:$clog2(NS)]=sel[q][d*3+:$clog2(NS)];
        end
        ot_hgi_coll_quarter_bridge #(.NPT(N),.MUT_SELECT(MUT_SELECT),.MUT_FAULT(MUT_FAULT)) dut(
            .clk_output({ND{clk}}),.rst_n(rst_n),.src_v(sv),.src_d(sd),.expect_v(ev[q][NS-1:0]),
            .out_slot(slot[q][ND-1:0]),.out_select(compact_sel),.out_v(ov[q][ND-1:0]),
            .out_d(od[q][ND*545-1:0]),.fault(fault[q][ND*2-1:0]));
    end
    task add_transfer(input integer start,input integer src,input integer dst,input integer seed);
        integer q,n,t,input_sel,output_sel,direction;
        reg [544:0] flit;
        reg [31:0] rng;
        begin:transfer
            rng=32'h9e3779b9^32'(seed);
            for(integer b=0;b<545;b=b+1) begin
                rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
                flit[b]=rng[0];
            end
            flit[544:512]={1'b1,8'hff,8'(src),16'(seed)};
            q=src;t=start;input_sel=0;direction=seed&1;
            plan_injv[t][q]=1;plan_inj[t][q]=flit;
            while(1) begin
                n=q==0?3:2;output_sel=q==dst?((seed&2)?n:0):2*n+direction;
                plan_ev[t][q][input_sel]=1;
                if(plan_slot[t][q][output_sel]) $fatal(1,"compiler resource conflict");
                plan_slot[t][q][output_sel]=1;
                plan_sel[t][q][output_sel*3+:3]=3'(input_sel);
                check_v[t+1][q][output_sel]=1;
                check_d[t+1][q][output_sel*545+:545]=flit;
                if(q==dst) begin total=total+1; disable transfer; end
                q=direction==0?nextq(q):prevq(q);n=q==0?3:2;input_sel=n+direction;t=t+2;

            end
            total=total+1;
        end
    endtask
    initial begin
        for(integer t=0;t<CYCLES;t=t+1) for(integer q=0;q<4;q=q+1) begin
            plan_ev[t][q]=0;plan_slot[t][q]=0;plan_sel[t][q]=0;plan_injv[t][q]=0;
            plan_inj[t][q]=0;check_v[t][q]=0;check_d[t][q]=0;
        end
        for(integer q=0;q<4;q=q+1) begin ev[q]=0;slot[q]=0;sel[q]=0;injv[q]=0;inj[q]=0;end
        // Streaming bursts exercise full545 payload and every real quarter leaf.
        for(integer src=0;src<4;src=src+1)
            for(integer dst=0;dst<4;dst=dst+1)
                for(integer k=0;k<16;k=k+1)
                    add_transfer(2+(src*4+dst)*40+k,src,dst,src*1000+dst*100+k);
        repeat(3) @(negedge clk);rst_n=1;
        for(integer t=0;t<CYCLES;t=t+1) begin
            for(integer q=0;q<4;q=q+1) begin
                ev[q]=plan_ev[t][q];slot[q]=plan_slot[t][q];sel[q]=plan_sel[t][q];
                injv[q]=plan_injv[t][q];inj[q]=plan_inj[t][q];
            end
            @(posedge clk);#1;
            if(t>=2) begin
                if(rx_v!==check_v[t-2][0][3]) $fatal(1,"RX mux cadence");
                if(rx_v && rx_d!==check_d[t-2][0][3*545+:545]) $fatal(1,"RX mux exact545");
                if(relay2_v!==check_v[t-2][0][0]) $fatal(1,"two relay cadence");
                if(relay2_v && relay2_d!==check_d[t-2][0][0+:545]) $fatal(1,"two relay exact545");
            end
            for(integer q=0;q<4;q=q+1) begin
                if(ov[q]!==check_v[t][q]) $fatal(1,"valid cadence t=%0d q=%0d",t,q);
                for(integer d=0;d<8;d=d+1)
                    if(check_v[t][q][d] && od[q][d*545+:545]!==check_d[t][q][d*545+:545])
                        $fatal(1,"exact545 mismatch t=%0d q=%0d d=%0d",t,q,d);
            end
            @(negedge clk);
        end
        for(integer q=0;q<4;q=q+1) if(fault[q]!=0) $fatal(1,"unexpected fault q=%0d fault=%h",q,fault[q]);
        // Unavailable, invalid-select and unexpected-input reservations fault;
        // their reserved output edge remains fixed.
        slot[0]=1;sel[0]=7;@(negedge clk);slot[0]=0;
        repeat(2) @(negedge clk);
        if(!fault[0][1]) $fatal(1,"invalid selection checker absent");
        injv[1]=1;ev[1]=0;@(negedge clk);injv[1]=0;
        repeat(2) @(negedge clk);
        if(!fault[1][0]) $fatal(1,"unexpected input checker absent");
        slot[2]=1;sel[2]=0;@(negedge clk);slot[2]=0;
        repeat(2) @(negedge clk);
        if(!fault[2][1]) $fatal(1,"unavailable input checker absent");
        $display("PASS quarter bridge exact545 transfers=%0d; actual q3+3q2; invalid/unavailable/unexpected faults",total);
        $finish;
    end
endmodule
