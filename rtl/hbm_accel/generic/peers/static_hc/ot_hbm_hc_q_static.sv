`timescale 1ns/1ps
`default_nettype none
// Static HC quadrant LG client (die slot hc_<q>, one master replicated x4; H-NETLIST 2026-10-15).
// Successor of the credited HC lane controller (ot_hgi_hc_eng / _ll: wrq_cr/wwq_cr credits, job_v/job_rdy,
// rg/wg request-grant) for the far HC tap lg_<q>_2 (READ_RETURN 18 / WRITE_RETURN 15). Every VM access of the
// static HC engine in this quadrant is issued here on a compiler-fixed edge:
//   residual read   ot_hgi_hc_residual_vm_static       320*npos slots x 8 sectors -> 8192-b x_wave every 4 edges
//   gathered mixes  ot_hgi_hc_gathered_mix_reader_static 3 sectors per position, one per 24-edge period
//   result store    ot_hgi_hc_result_vm_static          3 sectors (24 FP32) per position from the engine tail
// The three leaves are the codex/hc-static-engine-1014 datapath leaves (a35449ada), unchanged except the
// gathered reader's response phase is now a parameter. The issuer is a programme SRAM (ot_vms_calendar_static,
// same word protection as the VM calendars) loaded/started through ot_static_program_target (TARGET 108+q).
// Programme word calendar[78:0] (one word per edge while running; zero = idle):
//   [0] residual_launch [4:1] residual_npos [20:5] residual_base_sector
//   [21] gather_phase (LG owned by the gathered reader for the whole window, incl. its return edges)
//   [22] gather_launch [26:23] gather_npos [42:27] gather_base_sector [58:43] gather_stride_sector
//   [59] store_slot [75:60] result_base_sector [78:76] store_position
// No ready, credit, grant, queue or wait: a missing/unsolicited return, a write-done off its reserved edge,
// an rq from the reader that does not own the phase, or a store without its result raises fault; nothing moves.
// Pin registers: lg_rq out (+1), lg_rr/lg_w_done in (+1), result in (+1); lg_wq, x_wave, gathered mix,
// status are leaf output registers; cfg/start are sampled by the programme leaf's first rung.
// Fixed latencies with the hc_<q><k> pair leaves (ot_hgi_sfu_lg_pair_leaf, +1 each way) and the 18/15 tap:
//   residual capture = issue +23 (codex direct-tap value 19, +4 register edges), gathered response phase 23,
//   write-done = store output edge +DONE_LAT (measured by tb_hbm_hc_q_static).
module ot_hbm_hc_q_static #(
    parameter integer RD_CAPTURE=23,
    parameter integer GATHER_PHASE=23,
    parameter integer DONE_LAT=19,
    parameter integer MUT=0 // 1 residual wave word mutant, 2 result store one sector late, 3 capture edge early
)(
    input wire clk,rst_n,
    input wire cfg_we,
    input wire [9:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [9:0] start_base,
    input wire [10:0] start_limit,
    input wire [15:0] start_loops,
    output reg [135:0] lg_rq,
    output wire [2247:0] lg_wq,
    input wire [2055:0] lg_rr,
    input wire [7:0] lg_w_done,
    output wire x_wave_v,
    output wire [9:0] x_wave_word,
    output wire [8191:0] x_wave,
    output wire residual_done,
    output wire gathered_mix_v,
    output wire [4:0] gathered_mix_row,
    output wire [2:0] gathered_mix_pos,
    output wire [31:0] gathered_mix_data,
    output wire gather_done,
    input wire result_v,
    input wire [2:0] result_position,
    input wire [767:0] result,
    output wire program_active,program_done,
    output reg fault
);
    initial if(DONE_LAT<1)$fatal(1,"DONE_LAT must be positive");
    // ---- input pin registers
    reg [2055:0] rr_q;
    reg [7:0] w_done_q;
    reg result_v_q;
    reg [2:0] result_pos_q;
    reg [767:0] result_q;
    always @(posedge clk)begin rr_q<=lg_rr;result_pos_q<=result_position;result_q<=result;end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin w_done_q<=0;result_v_q<=0;end
        else begin w_done_q<=lg_w_done;result_v_q<=result_v;end
    // ---- programme issuer
    wire [78:0] c;
    wire cal_v,cal_fault;
    ot_vms_calendar_static #(.W(79)) programme(
        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .calendar(c),.calendar_v(cal_v),.ordinal(),.active(program_active),.done(program_done),.fault(cal_fault));
    wire residual_launch=c[0];
    wire [3:0] residual_npos=c[4:1];
    wire [15:0] residual_base=c[20:5];
    wire gather_phase=c[21];
    wire gather_launch=c[22];
    wire [3:0] gather_npos=c[26:23];
    wire [15:0] gather_base=c[42:27],gather_stride=c[58:43];
    wire store_slot=c[59];
    wire [15:0] result_base=c[75:60];
    wire [2:0] store_position=c[78:76];
    // ---- residual reader (owns the tap outside gather windows)
    wire [135:0] res_rq,gat_rq;
    wire [7:0] res_read,gat_read,write_sel;
    wire res_fault,gat_fault,wr_fault;
    ot_hgi_hc_residual_vm_static #(.CAPTURE_LAT(RD_CAPTURE-((MUT==3)?1:0)),.MUT_POSITION((MUT==1)?1:0)) residual(
        .clk(clk),.rst_n(rst_n),.launch(residual_launch),.npos(residual_npos),.base_sector(residual_base),
        .local_rq(res_rq),.local_read(res_read),.local_rr(gather_phase?2056'd0:rr_q),
        .x_wave_v(x_wave_v),.x_wave_word(x_wave_word),.x_wave(x_wave),.done(residual_done),.fault(res_fault));
    ot_hgi_hc_gathered_mix_reader_static #(.RESP_PHASE(GATHER_PHASE)) gather(
        .clk(clk),.rst_n(rst_n),.launch(gather_launch),.npos(gather_npos),
        .base_sector(gather_base),.position_stride_sector(gather_stride),
        .local_rq(gat_rq),.local_read(gat_read),.local_rr(gather_phase?rr_q:2056'd0),
        .gathered_mix_v(gathered_mix_v),.gathered_mix_row(gathered_mix_row),
        .gathered_mix_pos(gathered_mix_pos),.gathered_mix_data(gathered_mix_data),.done(gather_done),.fault(gat_fault));
    ot_hgi_hc_result_vm_static store(
        .clk(clk),.rst_n(rst_n),.store_slot(store_slot),.base_sector(result_base+((MUT==2)?16'd1:16'd0)),
        .store_position(store_position),.result_v(result_v_q),.result_position(result_pos_q),.result(result_q),
        .local_wq(lg_wq),.local_write(write_sel),.fault(wr_fault));
    // ---- output pin register on the request port (phase-owned, never merged)
    reg res_any,gat_any;
    always @*begin
        res_any=0;gat_any=0;
        for(integer b=0;b<8;b=b+1)begin res_any=res_any|res_rq[b*17+16];gat_any=gat_any|gat_rq[b*17+16];end
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)lg_rq<=0;
        else lg_rq<=gather_phase?gat_rq:res_rq;
    // ---- write-done reservation: every store's banks return local_w_done exactly DONE_LAT edges later
    reg [7:0] done_cal[0:DONE_LAT-1];
    reg own_fault;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin
            own_fault<=0;fault<=0;
            for(integer i=0;i<DONE_LAT;i=i+1)done_cal[i]<=0;
        end else begin
            done_cal[0]<=write_sel;
            for(integer i=1;i<DONE_LAT;i=i+1)done_cal[i]<=done_cal[i-1];
            if(w_done_q!=done_cal[DONE_LAT-1])own_fault<=1;
            if((gather_phase&&res_any)||(!gather_phase&&gat_any))own_fault<=1;
            fault<=own_fault|cal_fault|res_fault|gat_fault|wr_fault;
        end
endmodule
`default_nettype wire
