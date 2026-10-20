`timescale 1ns/1ps
`default_nettype none
// Static HC quadrant LG client (die slot hc_<q>, one master replicated x4; H-NETLIST 2026-10-15).
// Successor of the credited HC lane controller (ot_hgi_hc_eng / _ll: wrq_cr/wwq_cr credits, job_v/job_rdy,
// rg/wg request-grant) for the far HC tap lg_<q>_2 (READ_RETURN 18 / WRITE_RETURN 15). Every VM access of the
// static HC engine in this quadrant is issued here on a compiler-fixed edge:
//   residual read   ot_hnx_hgi_hc_residual_vm       320*npos slots x 8 sectors -> 8192-b x_wave every 4 edges
//   gathered mixes  ot_hnx_hgi_hc_gathered_mix_reader 3 sectors per position, one per 24-edge period
//   result store    ot_hnx_hgi_hc_result_vm          3 sectors (24 FP32) per position from the engine tail
// The three leaves are the codex/hc-static-engine-1014 datapath leaves (a35449ada), unchanged except the
// gathered reader's response phase is now a parameter. The issuer is a programme SRAM (ot_vms_calendar_static,
// same word protection as the VM calendars) loaded/started through ot_static_program_target (TARGET 108+q).
// Programme word calendar[78:0] (one word per edge while running; zero = idle):
//   [0] residual_launch [4:1] residual_npos [20:5] residual_base_sector
//   [21] gather_phase (LG owned by the gathered reader for the whole window, incl. its return edges)
//   [22] gather_launch [26:23] gather_npos [42:27] gather_base_sector [58:43] gather_stride_sector
//   [59] store_slot [75:60] result_base_sector [78:76] store_position
//   HBM-NEXT-UNITS 2026-10-19 (hnx fork, N-row records; ISA rows draft results/arch/hbm_next_1019/cmtp/isa_rows.md):
//   [94:79] residual_row_stride (sectors; 0 = dense d4g form) [110:95] result_row_stride (sectors; 0 = 3, dense)
//   residual_npos = the record's row count N (1..8); SPR = issue slots a row (320 = full K; 80 = a quarter slice).
// COLLAR FOLD (H-DIE option A, 0600): the F20 programme target (ot_static_program_target TGT_PIN=1, id from the
// identity strap tgt = 108+q) is inside this master; it takes the F20 broadcast directly and exposes configured.
// X_WAVE LINK (0600): XW_BEATS=4 sends each 8,192-b wave as 4 beats of 2,048 b on consecutive edges, beat 3 on the
// BEATS=1 wave edge (receiver ot_hnx_hc_xw_rx in hc_eng presents the wave at the same pin-level edge: +0).
// No ready, credit, grant, queue or wait: a missing/unsolicited return, a write-done off its reserved edge,
// an rq from the reader that does not own the phase, or a store without its result raises fault; nothing moves.
// Pin registers: lg_rq out (+1), lg_rr/lg_w_done in (+1), result in (+1); lg_wq, x_wave, gathered mix,
// status are leaf output registers; the F20 bus lands in the folded target's pin flops (tgt strap included).
// Fixed latencies with the hc_<q><k> pair leaves (ot_hgi_sfu_lg_pair_leaf, +1 each way) and the 18/15 tap:
//   residual capture = issue +23 (codex direct-tap value 19, +4 register edges), gathered response phase 23,
//   write-done = store output edge +DONE_LAT (measured by tb_hbm_hc_q_static).
module ot_hnx_hc_q #(
    parameter integer RD_CAPTURE=23,
    parameter integer GATHER_PHASE=23,
    parameter integer DONE_LAT=19,
    parameter integer XW_BEATS=4,
    parameter integer SPR=320,
    parameter integer XFC=0,  // HUBFIX 10-19: 1 = per-face copies of the x_wave beat-control register on x_wave_vf / x_wave_beatf
    parameter integer MUT=0 // 8 the E face copy is a relay one edge late (HUBFIX), 6 residual reader ignores the row stride, 7 result store ignores the row stride, 1 residual wave word mutant, 2 result store one sector late, 3 capture edge early,
                            // 4 x_wave beats 1/2 sent swapped, 5 x_wave beat 3 one edge late
)(
    input wire clk,rst_n,
    input wire [7:0] tgt,              // identity strap: F20 target id (108+q)
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,
    output wire configured,
    output wire [135:0] lg_rq,
    output wire [2247:0] lg_wq,
    input wire [2055:0] lg_rr,
    input wire [7:0] lg_w_done,
    output wire x_wave_v,
    output wire [9:0] x_wave_word,
    output wire [8192/XW_BEATS-1:0] x_wave,
    output wire [1:0] x_wave_beat,
    output wire [3:0] x_wave_vf,       // per-face copies W, N, E, S (same edge as x_wave_v; XFC 0 = wires of it)
    output wire [7:0] x_wave_beatf,
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
    // ---- regional reset (HCDMA-HCQ 10-17): the rst_n port drives only the registered relay (assert asynchronous,
    // release 3 clk edges later); each region resets its own flops from a relay copy placed beside it, so no net from
    // the port spans the 432 um tile. The F20 target already synchronises its own release (2 edges), the host programs
    // the target long after reset, and nothing in this master counts cycles from reset release.
    // HUB-SAFE2 2026-10-20: the relay is u_rst_relay (the name the synthesis pass physical/common_flow/ot_rst_copies.py
    // recognises), REGIONS 16 kept identical copies; the pass re-points the ~420 reset loads over the copies (<= 32 each).
    // Regions 0..5 keep their roles; 6..15 are load-balancing copies.  Census safe1019: one copy (u_rst) drove 299.
    // HUB-SAFE3 2026-10-20: REGIONS 24 (the safe3 copies add ~150 reset loads; census safe2 copies were 33-37).
    wire [23:0] rr_n;
    ot_rst_relay #(.REGIONS(24)) u_rst_relay(.clk(clk),.rst_n_in(rst_n),.rst_n(rr_n));
    // ---- input pin registers
    reg [2055:0] rr_q;
    reg [7:0] w_done_q;
    reg result_v_q;
    reg [2:0] result_pos_q;
    reg [767:0] result_q;
    always @(posedge clk)begin rr_q<=lg_rr;result_pos_q<=result_position;result_q<=result;end
    always @(posedge clk or negedge rr_n[5])
        if(!rr_n[5])begin w_done_q<=0;result_v_q<=0;end
        else begin w_done_q<=lg_w_done;result_v_q<=result_v;end
    // ---- F20 programme target (folded collar, pin-registered soft logic)
    wire cfg_we,start_v,tgt_fault;
    wire [9:0] p_addr,start_base;
    wire [255:0] p_data;
    wire [10:0] start_limit;
    wire [15:0] start_loops;
    ot_hnx_prog_target #(.PCW(10)) target(
        .clk(clk),.rst_n(rr_n[0]),.tgt(tgt),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
        .program_active(program_active),.program_cfg_we(cfg_we),.program_cfg_addr(p_addr),.program_cfg_data(p_data),
        .program_start_v(start_v),.program_start_base(start_base),.program_start_limit(start_limit),
        .program_start_loops(start_loops),.configured(configured),.fault(tgt_fault));
    // ---- programme issuer
    wire [110:0] c;
    wire cal_v,cal_fault;
    wire [7:0] st_v; wire [127:0] st_hdr; wire [191:0] st_sel; wire [15:0] gp_c; wire [9:0] lc_c;
    ot_hnx_hc_cal #(.W(111),.MUT_STRIDE((MUT==7)?1:0),.MUT_SBASE((MUT==2)?1:0)) programme(
        .clk(clk),.rst_n(rr_n[1]),.cfg_we(cfg_we),.cfg_addr(p_addr),.cfg_data(p_data),
        .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .calendar(c),.calendar_v(cal_v),.ordinal(),.active(program_active),.done(program_done),.fault(cal_fault),
        .st_v(st_v),.st_hdr(st_hdr),.st_sel(st_sel),.gp_c(gp_c),.lc_c(lc_c));
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
    wire [15:0] residual_stride=c[94:79],result_stride=c[110:95];
    // ---- residual reader (owns the tap outside gather windows)
    // HUB-SAFE2 2026-10-20 (SAFE item 3): gather_phase gates only the 8 return-valid bits of each reader's local_rr
    // (each reader captures the 2,048 data bits only on its own capture / response slot); census safe1019: c[21] drove
    // 3,524 loads through the two 2,056-b phase gates.  Readers' outputs are unchanged.
    wire [2055:0] rr_res,rr_gat;
    for(genvar b=0;b<8;b=b+1)begin:g_rrg
        assign rr_res[b*257+:257]={rr_q[b*257+256]&!gp_c[8+b],rr_q[b*257+:256]};
        assign rr_gat[b*257+:257]={rr_q[b*257+256]&gp_c[8+b],rr_q[b*257+:256]};
    end
    wire [135:0] res_rq,gat_rq;
    wire [7:0] res_read,gat_read,write_sel;
    wire res_fault,gat_fault,wr_fault;
    ot_hnx_hgi_hc_residual_vm #(.CAPTURE_LAT(RD_CAPTURE-((MUT==3)?1:0)),.MUT_POSITION((MUT==1)?1:0),.BEATS(XW_BEATS),
        .MUT_BEAT((MUT==4)?1:(MUT==5)?2:0),.SPR(SPR),.MUT_STRIDE((MUT==6)?1:0),.XFC(XFC),.MUT_FC((MUT==8)?1:0)) residual(
        .clk(clk),.rst_n(rr_n[2]),.launch(residual_launch),.launch_c(lc_c[3:0]),.npos(residual_npos),.base_sector(residual_base),.row_stride(residual_stride),
        .local_rq(res_rq),.local_read(res_read),.local_rr(rr_res),
        .x_wave_v(x_wave_v),.x_wave_word(x_wave_word),.x_wave(x_wave),.x_wave_beat(x_wave_beat),.x_wave_vf(x_wave_vf),.x_wave_beatf(x_wave_beatf),
        .done(residual_done),.fault(res_fault));
    ot_hnx_hgi_hc_gathered_mix_reader #(.RESP_PHASE(GATHER_PHASE)) gather(
        .clk(clk),.rst_n(rr_n[3]),.launch(gather_launch),.launch_c(lc_c[9:4]),.npos(gather_npos),
        .base_sector(gather_base),.position_stride_sector(gather_stride),
        .local_rq(gat_rq),.local_read(gat_read),.local_rr(rr_gat),
        .gathered_mix_v(gathered_mix_v),.gathered_mix_row(gathered_mix_row),
        .gathered_mix_pos(gathered_mix_pos),.gathered_mix_data(gathered_mix_data),.done(gather_done),.fault(gat_fault));
    ot_hnx_hgi_hc_result_vm #(.MUT_STRIDE((MUT==7)?1:0)) store(
        .clk(clk),.rst_n(rr_n[4]),.store_slot(store_slot),.base_sector(result_base+((MUT==2)?16'd1:16'd0)),
        .row_stride(result_stride),.store_position(store_position),.st_v(st_v),.st_hdr(st_hdr),.st_sel(st_sel),
        .result_v(result_v_q),.result_position(result_pos_q),.result(result_q),
        .local_wq(lg_wq),.local_write(write_sel),.fault(wr_fault));
    // ---- output pin register on the request port (phase-owned, never merged)
    reg res_any,gat_any;
    always @*begin
        res_any=0;gat_any=0;
        for(integer b=0;b<8;b=b+1)begin res_any=res_any|res_rq[b*17+16];gat_any=gat_any|gat_rq[b*17+16];end
    end
    // HUB-SAFE2 2026-10-20: the phase select of bank b uses the calendar's kept gather_phase copy gp_c[b] (= c[21] on
    // the same edge; 17 loads each instead of c[21] -> 136) and only the 8 request-valid bits are reset.
    reg [7:0] rq_v; reg [127:0] rq_a;
    always @(posedge clk or negedge rr_n[5])
        if(!rr_n[5])rq_v<=0;
        else for(integer b=0;b<8;b=b+1)rq_v[b]<=gp_c[8+b]?gat_rq[b*17+16]:res_rq[b*17+16];
    always @(posedge clk)for(integer b=0;b<8;b=b+1)rq_a[b*16+:16]<=gp_c[b]?gat_rq[b*17+:16]:res_rq[b*17+:16];
    for(genvar b=0;b<8;b=b+1)begin:g_rq assign lg_rq[b*17+:17]={rq_v[b],rq_a[b*16+:16]}; end
    // ---- write-done reservation: every store's banks return local_w_done exactly DONE_LAT edges later
    reg [7:0] done_cal[0:DONE_LAT-1];
    reg own_fault;
    always @(posedge clk or negedge rr_n[5])
        if(!rr_n[5])begin
            own_fault<=0;fault<=0;
            for(integer i=0;i<DONE_LAT;i=i+1)done_cal[i]<=0;
        end else begin
            done_cal[0]<=write_sel;
            for(integer i=1;i<DONE_LAT;i=i+1)done_cal[i]<=done_cal[i-1];
            if(w_done_q!=done_cal[DONE_LAT-1])own_fault<=1;
            if((gather_phase&&res_any)||(!gather_phase&&gat_any))own_fault<=1;
            fault<=own_fault|cal_fault|res_fault|gat_fault|wr_fault|tgt_fault;
        end
endmodule
`default_nettype wire
