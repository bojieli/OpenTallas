`timescale 1ns/1ps
`default_nettype none
// HBM-HUB-RTL-1 11-11 (tag hbm-hub-gather-phase): ot_hgi_hc_gathered_mix_reader_static at a padded round trip.
// The reader's request pins drive a fixed-latency pipelined 8-bank VM model of VMLAT register edges (the padded LG
// round trip); RESP_PHASE is passed WITHOUT PERIOD (as the rtl/ q_static parent did), so PERIOD takes its default.
// Golden (the token lowering, tools/hbm_layer_vehicle/hc_layer_lower_1021.py root_rows): gather_period =
// max(24, RESP_PHASE+1); position p row r is on the reader pins at launch + 1 + p*gather_period + RESP_PHASE + 1 + r
// (= hc_images G0 + 24p' with G0 = A0 + RESP_PHASE + 2 at the q_static pins; extra_edges_per_additional_position =
// max(0, RESP_PHASE+1-24)), data = VM word, never a fault, done after the last row.
// Every mix prints "MIX dt=<edges after launch> pos=<p> row=<r> data=<hex>" so the padded run is diffed against the
// unpadded reference (RESP_PHASE 23) as EQ_CYCLE_SHIFTED by 151 + p*151 edges.
// Negative controls: VMLAT=RESP_PHASE+1 (late return -> fault), PERIOD override (schedule mismatch).
module tb_hgi_hc_gather_phase;
    parameter integer RP=174;          // RESP_PHASE passed by the parent
    parameter integer VMLAT=174;       // modelled round trip (must equal RP)
    parameter integer NPOS=3;
    parameter integer PER_OVR=0;       // 0 = reader default PERIOD; >0 = explicit override (negative control)
    localparam integer GP=(RP>=24)?RP+1:24;           // token lowering gather_period
    localparam integer EXP_PER=(PER_OVR>0)?GP:GP;     // golden is always the lowering's period
    localparam integer BASE=8192+5, STRIDE=40;
    reg clk=0,rst_n=0,launch=0;
    always #1 clk=~clk;
    wire [135:0] rq; wire [7:0] rd; reg [2055:0] rr;
    wire mv,done,fault; wire [4:0] mrow; wire [2:0] mpos; wire [31:0] mdata;
    generate if(PER_OVR>0)begin:g_ovr
        ot_hgi_hc_gathered_mix_reader_static #(.RESP_PHASE(RP),.PERIOD(PER_OVR)) dut(
            .clk(clk),.rst_n(rst_n),.launch(launch),.npos(4'(NPOS)),.base_sector(16'(BASE)),.position_stride_sector(16'(STRIDE)),
            .local_rq(rq),.local_read(rd),.local_rr(rr),.gathered_mix_v(mv),.gathered_mix_row(mrow),.gathered_mix_pos(mpos),
            .gathered_mix_data(mdata),.done(done),.fault(fault));
    end else begin:g_def
        ot_hgi_hc_gathered_mix_reader_static #(.RESP_PHASE(RP)) dut(
            .clk(clk),.rst_n(rst_n),.launch(launch),.npos(4'(NPOS)),.base_sector(16'(BASE)),.position_stride_sector(16'(STRIDE)),
            .local_rq(rq),.local_read(rd),.local_rr(rr),.gathered_mix_v(mv),.gathered_mix_row(mrow),.gathered_mix_pos(mpos),
            .gathered_mix_data(mdata),.done(done),.fault(fault));
    end endgenerate
    // VM model: bank b registers {read, sector} and returns {valid, vm[sector]} VMLAT edges later (pipelined)
    reg [255:0] vm[0:32767];
    reg [16:0] pipe[0:7][0:1023];
    always @(posedge clk)begin
        for(integer b=0;b<8;b=b+1)begin
            for(integer k=VMLAT-1;k>0;k=k-1)pipe[b][k]<=pipe[b][k-1];
            pipe[b][0]<={rd[b]&rq[b*17+16],rq[b*17+:16]};
        end
    end
    always @*for(integer b=0;b<8;b=b+1)begin
        rr[b*257+256]=pipe[b][VMLAT-1][16];
        rr[b*257+:256]=pipe[b][VMLAT-1][16]?vm[pipe[b][VMLAT-1][15:0]]:256'd0;
    end
    integer t=0,tl=-1,errors=0,mixes=0,dones=0;
    always @(posedge clk)t<=t+1;
    always @(posedge clk)if(rst_n&&tl>=0)begin
        if(mv)begin:chk
            integer dt,ep,er,exp_t;reg [31:0] ed;
            dt=t-tl;
            $display("MIX dt=%0d pos=%0d row=%0d data=%08h",dt,mpos,mrow,mdata);
            ep=mixes/24;er=mixes%24;
            exp_t=1+ep*EXP_PER+RP+1+er;
            ed=vm[BASE+ep*STRIDE+er/8][(er%8)*32+:32];
            if(dt!==exp_t||mpos!==3'(ep)||mrow!==5'(er)||mdata!==ed)begin
                errors=errors+1;
                if(errors<6)$display("MISMATCH mix %0d: dt=%0d exp %0d pos=%0d exp %0d row=%0d exp %0d data=%08h exp %08h",
                                     mixes,dt,exp_t,mpos,ep,mrow,er,mdata,ed);
            end
            mixes=mixes+1;
        end
        if(done)dones=dones+1;
    end
    initial begin
        for(integer s=0;s<32768;s=s+1)vm[s]={$random,$random,$random,$random,$random,$random,$random,$random};
        for(integer b=0;b<8;b=b+1)for(integer k=0;k<1024;k=k+1)pipe[b][k]=0;
        repeat(3)@(negedge clk);rst_n=1;repeat(3)@(negedge clk);
        launch=1;@(negedge clk);launch=0;tl=t-1;   // launch sampled at edge number tl
        repeat(NPOS*GP+RP+80)@(negedge clk);
        if(mixes!=NPOS*24)begin errors=errors+1;$display("mixes %0d expected %0d",mixes,NPOS*24);end
        if(dones!=1)begin errors=errors+1;$display("done %0d expected 1",dones);end
        if(fault)begin errors=errors+1;$display("reader fault");end
        if(errors==0)$display("TB_GATHER_PHASE PASS RP=%0d VMLAT=%0d NPOS=%0d PERIOD=%0d mixes=%0d",RP,VMLAT,NPOS,
                              (PER_OVR>0)?PER_OVR:GP,mixes);
        else $display("TB_GATHER_PHASE FAIL RP=%0d VMLAT=%0d NPOS=%0d PER_OVR=%0d errors=%0d",RP,VMLAT,NPOS,PER_OVR,errors);
        $finish;
    end
endmodule
`default_nettype wire
