`timescale 1ns/1ps
`default_nettype none
// Compiler-selected one-bank physical leaf extracted from the actual eight-bank tap for the shared VM lane group. Two edges
// through dedicated input and mux/output registers in EACH direction.
// All rq records are {v,sector16}; wq {v,sector16,data256,mask8}; rr {v,data256}.
// No queues, arbitration, ready, grants, credits, or runtime rescheduling.
// Local request/select pins sampled n; near request output n+1. VM response
// input sampled m; local/far return output m+1. Fixed calendars reserve local
// returns READ_RETURN/WRITE_RETURN subsequent edges after local input sample.
// Near SU:10/7, middle SFU:14/11, far HC:18/15 for bank read+6/commit+3.
// Missing returns fault and still emit on the reserved edge; no late replay.
module ot_hbm_vm_lg_static_bank #(
    parameter integer READ_RETURN=10,
    parameter integer WRITE_RETURN=7,
    parameter integer MUT=0, //1: write payload mux selects far despite local calendar
    // RET_PIN=1 (H-NETLIST 0600, fewer distinct tiles): the return edges come from identity strap pins rret/wret (die
    // constants, pin-flopped, 2..READ_RETURN / 2..WRITE_RETURN); READ_RETURN/WRITE_RETURN are then the calendar depths.
    parameter integer RET_PIN=0,
    // LOCAL_SPLIT=1 (NATIVE-FIX3/lgtap 10-18, NATIVE-3 audit of ot_hbm_su_static_pg_lg_tap: local_rr launch 319.2 ps,
    // local_rq/local_wq valid capture 236.3 ps). 0 added edges, every output bit identical on every edge:
    //  (a) local_rr data comes from its OWN return register (return_l_d <= rr_d, a keep_hierarchy instance so opt_merge
    //      cannot fold it into return_d); return_d then drives far_rr only, so each copy can sit at its own face;
    //  (b) the calendar head is filled from the pin registers (read_d & lrq_v / write_d & lwq_v) one edge later and the
    //      due tap moves one entry earlier (READ_RETURN-2 / WRITE_RETURN-2), so each local_rq/local_wq valid pin and each
    //      local_read/local_write pin has ONE capture flop (its pin register) instead of pin register + calendar AND.
    // Needs RET_PIN=0 and READ_RETURN/WRITE_RETURN >= 3. SPLIT_MUT (bench only, must FAIL lockstep): 1 = due tap left at
    // READ_RETURN-1 (returns one edge late), 2 = local return copy loaded from the near_rr pins (data one edge early).
    parameter integer LOCAL_SPLIT=0,
    parameter integer SPLIT_MUT=0
)(
    input wire clk,rst_n,
    input wire [4:0] rret,wret,   // identity straps, used only when RET_PIN=1
    input wire [16:0] local_rq,far_rq,
    input wire [280:0] local_wq,far_wq,
    input wire [0:0] local_read,local_write,
    output wire [16:0] near_rq,
    output wire [280:0] near_wq,
    input wire [256:0] near_rr,
    input wire [0:0] near_w_done,
    output wire [256:0] local_rr,far_rr,
    output reg [0:0] local_w_done,far_w_done,
    output reg fault
);
    initial if(READ_RETURN<2||WRITE_RETURN<2)$fatal(1,"tap return latency must include pin/output edges");
    initial if(LOCAL_SPLIT!=0&&(RET_PIN!=0||READ_RETURN<3||WRITE_RETURN<3))$fatal(1,"LOCAL_SPLIT needs RET_PIN=0 and returns >= 3");
    localparam integer DUE_OFF=(LOCAL_SPLIT!=0&&SPLIT_MUT!=1)?2:1;
    reg [16:0] lrq_d,frq_d;
    reg [280:0] lwq_d,fwq_d;
    reg [0:0] lrq_v,frq_v,lwq_v,fwq_v,read_d,write_d;
    reg [16:0] rq_d;
    reg [280:0] wq_d;
    reg [0:0] rq_v,wq_v;
    reg [256:0] rr_d,return_d;
    reg [0:0] rr_v,done_d,local_rr_v,far_rr_v;
    reg [0:0] read_calendar[0:READ_RETURN-1];
    reg [0:0] write_calendar[0:WRITE_RETURN-1];
    reg [4:0] rret_q,wret_q; always @(posedge clk) begin rret_q<=rret; wret_q<=wret; end
    wire [0:0] read_due =(RET_PIN!=0)?read_calendar[rret_q-5'd1]:read_calendar[READ_RETURN-DUE_OFF];
    wire [0:0] write_due=(RET_PIN!=0)?write_calendar[wret_q-5'd1]:write_calendar[WRITE_RETURN-DUE_OFF];
    wire [255:0] return_l;   // data of local_rr: return_d (LOCAL_SPLIT=0) or its own register (LOCAL_SPLIT=1)
    if(LOCAL_SPLIT!=0)begin:g_lsplit
        ot_hbm_vm_lg_keep_reg u_ret_l(.clk(clk),.d(SPLIT_MUT==2?near_rr[255:0]:rr_d[255:0]),.q(return_l));
    end else begin:g_lshare
        assign return_l=return_d[255:0];
    end
    always @(posedge clk)begin
        lrq_d<=local_rq;frq_d<=far_rq;lwq_d<=local_wq;fwq_d<=far_wq;
        rr_d<=near_rr;return_d<=rr_d;
        for(integer b=0;b<1;b=b+1)begin
            rq_d[b*17+:16]<=read_d[b]?lrq_d[b*17+:16]:frq_d[b*17+:16];
            wq_d[b*281+:280]<=write_d[b]?lwq_d[b*281+:280]:fwq_d[b*281+:280];
            if(MUT==1&&write_d[b])wq_d[b*281+8+:256]<=fwq_d[b*281+8+:256];
        end
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            lrq_v<=0;frq_v<=0;lwq_v<=0;fwq_v<=0;read_d<=0;write_d<=0;
            rq_v<=0;wq_v<=0;rr_v<=0;done_d<=0;
            local_rr_v<=0;far_rr_v<=0;local_w_done<=0;far_w_done<=0;fault<=0;
            for(integer i=0;i<READ_RETURN;i=i+1)read_calendar[i]<=0;
            for(integer i=0;i<WRITE_RETURN;i=i+1)write_calendar[i]<=0;
        end else begin
            read_d<=local_read;write_d<=local_write;done_d<=near_w_done;
            for(integer i=1;i<READ_RETURN;i=i+1)read_calendar[i]<=read_calendar[i-1];
            for(integer i=1;i<WRITE_RETURN;i=i+1)write_calendar[i]<=write_calendar[i-1];
            for(integer b=0;b<1;b=b+1)begin
                lrq_v[b]<=local_rq[b*17+16];frq_v[b]<=far_rq[b*17+16];
                lwq_v[b]<=local_wq[b*281+280];fwq_v[b]<=far_wq[b*281+280];
                rr_v[b]<=near_rr[b*257+256];
                if(LOCAL_SPLIT!=0)begin
                    read_calendar[0][b]<=read_d[b]&&lrq_v[b];
                    write_calendar[0][b]<=write_d[b]&&lwq_v[b];
                end else begin
                    read_calendar[0][b]<=local_read[b]&&local_rq[b*17+16];
                    write_calendar[0][b]<=local_write[b]&&local_wq[b*281+280];
                end
                rq_v[b]<=read_d[b]?lrq_v[b]:frq_v[b];
                wq_v[b]<=write_d[b]?lwq_v[b]:fwq_v[b];
                local_rr_v[b]<=read_due[b];
                far_rr_v[b]<=rr_v[b]&&!read_due[b];
                local_w_done[b]<=write_due[b];
                far_w_done[b]<=done_d[b]&&!write_due[b];
                if((lrq_v[b]&&!read_d[b])||(lwq_v[b]&&!write_d[b])||
                   (read_d[b]&&frq_v[b])||(write_d[b]&&fwq_v[b])||
                   (read_due[b]&&!rr_v[b])||
                   (write_due[b]&&!done_d[b]))fault<=1;
            end
        end
    end
    for(genvar b=0;b<1;b=b+1)begin:bank
        assign near_rq[b*17+:17]={rq_v[b],rq_d[b*17+:16]};
        assign near_wq[b*281+:281]={wq_v[b],wq_d[b*281+:280]};
        assign local_rr[b*257+:257]={local_rr_v[b],return_l};
        assign far_rr[b*257+:257]={far_rr_v[b],return_d[b*257+:256]};
    end
endmodule

// A 256-bit plain register kept as its own instance: Yosys opt_merge folds flip-flops with identical D/clock, and a plain
// (* keep *) reg does not stop it, so the face copy needs its own hierarchy. Kept by the kit (route synth_keep_modules ->
// ORFS SYNTH_KEEP_MODULES), not by an RTL attribute, so the flattened cdc_synchronizers lint still sees plain flops.
// No parameters (LGTAP2 10-18): a parameterised instance elaborates as $paramod\ot_hbm_vm_lg_keep_reg\W=256, which the
// SYNTH_KEEP_MODULES name does not match (yosys "did not match any module"), so r2 flattened it and opt_merge folded the
// copy back into return_d (CTS probe: local_rr from return_d at the W face, 330 ps launch, 225 pins over 220).
module ot_hbm_vm_lg_keep_reg (
    input wire clk,
    input wire [255:0] d,
    output reg [255:0] q
);
    always @(posedge clk) q<=d;
endmodule
`default_nettype wire
