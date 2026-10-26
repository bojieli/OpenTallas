`timescale 1ns/1ps
// KV-PLAN-CI 2026-10-17 (coordinator decision 3): the per-PC wires-only parent without the legacy controller word ci
// (see rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_nc.sv).  The controller co is co[281:0] (the landing ECC word), so
// the elastic front and the return ring take a 282-b controller word: the front's two-edge pass-through of the legacy
// co[293:282] {at, av, wcon, hand} fields (24 flops, consumed by nothing on the static die: the return ring never read
// them) is removed logic, and the return ring's controller_co pins are the 282 it reads.  Otherwise identical to
// qkd_static_kv_pc_path / qkd_kv_hbm_elastic_front_mc / qkd_static_kv_return_slots_mc (unchanged; the nc front / ring
// reuse their pointer-copy children qkd_kvef_mc_rp / qkd_ksr_mc_rp from those files).
// MU-ADOPT-KV 10-19 (R6 read side, opt-in MU, default 0 = unchanged): the qkd_kv_mu_rrow map between the HBM calendar's
// static_cmd and the PC controller puts the stage user into row[9:8] of KV descriptors (op 0 / 3 on rows < 256; row of
// user u, layer l = 64 + l + 256*u).  The stage user is the calendar's own per-command epoch: static_epoch[1:0]
// (static_epoch is registered on the same edge as static_cmd from the epoch latched at the layer go; the MU epoch
// allocator puts the host step's user in epoch[1:0]).  Combinational, 0 added edges.  MU 0: wires.
module qkd_static_kv_pc_path_nc #(parameter integer MU = 0, CORE_CLOCK = 0) (
    input wire pll_hbm,
    input wire pll_hbm_port,  // u_ctrl.u_port HBM clock entry (same clock as pll_hbm; separate die entry)
    input wire pll_hbm_ecc,   // u_ctrl.u_ecc HBM clock entry (same clock as pll_hbm; separate die entry)
    input wire pll_hbm_cdc,   // u_ctrl.u_cdc HBM clock entry (core_s7; same clock as pll_hbm; separate die entry)
    input wire pll_hbm_obs,   // u_ctrl.u_obs HBM clock entry (core_s7; same clock as pll_hbm; separate die entry)
    input wire hrst,
    input wire ck,
    input wire rsi,
    input wire [4:0] pc,
    input wire [287:0] es,
    output wire [260:0] er,
    output wire [327:0] po,
    input wire [288:0] pi,
    input wire [32:0] ki,
    output wire [32:0] ko,
    input wire fi,
    output wire fo,
    input wire [1:0] cfg_stack,
    input wire [317:0] es_context,
    input wire es_expected_valid,
    input wire [60:0] es_expected_identity,
    input wire [28:0] es_expected_address,
    input wire [4:0] es_expected_pc,
    input wire [1:0] es_expected_stack,
    output wire native_commit_valid,
    output wire [60:0] native_commit_identity,
    output wire [28:0] native_commit_address,
    output wire completion_v,
    output wire completion_we,
    output wire completion_fault,
    output wire idle_core,
    output wire idle_hbm,
    output wire drain_fault_core,
    output wire drain_fault_hbm,
    input wire cal_hck,
    input wire cal_rst_n,
    input wire cal_cfg_we,
    input wire [4:0] cal_cfg_addr,
    input wire [63:0] cal_cfg_data,
    input wire cal_seal,
    input wire cal_go,
    input wire [15:0] cal_epoch,
    input wire [5:0] cal_layer,
    output wire cal_fault_hbm,
    output wire cal_idle_hbm,
    input wire front_hck,
    input wire [3:0] front_hbm_data,
    input wire front_blk_go,
    output wire front_blk_freed,
    output wire front_hold,
    output wire [15:0] front_stall_edges,
    output wire [5:0] front_occupancy,
    output wire front_idle_hbm,
    output wire front_fault_overflow_hbm,
    output wire front_fault_go_hbm,
    input wire return_hck,
    input wire return_ck,
    input wire [3:0] return_hbm_data,
    input wire expected_put,
    input wire [9:0] expected_sector,
    input wire [15:0] expected_epoch,
    input wire [5:0] expected_layer,
    output wire actual_valid,
    output wire [9:0] actual_sector,
    output wire [15:0] actual_epoch,
    output wire [5:0] actual_layer,
    output wire [255:0] actual_data,
    output wire return_fault_hbm,
    output wire return_fault_core,
    output wire return_idle_hbm,
    output wire return_idle_core
);
    wire [281:0] controller_co;
    wire static_cmd_owner;
    wire [42:0] static_cmd;
    wire [42:0] static_cmd_mu;
    wire reserved_rd;
    wire reserved_static_col;
    wire reserved_write_col;
    wire [15:0] static_epoch;
    wire expected_raw_valid;
    wire [15:0] corrected_epoch;
    wire [281:0] front_co;
    wire [15:0] front_epoch;
    wire front_put;
    qkd_ctrl_pc_host_static_nc #(.CORE_CLOCK(CORE_CLOCK),.ROW0(64), .CVL(2), .HOFF(3), .WDONE(CORE_CLOCK ? 19 : 17), .LATE(4096), .PROFILE(0), .EVMUT(0), .MUT(0), .ELASTIC(1), .RAW_WD(256), .TQD(64)) u_ctrl (
        .pll_hbm(pll_hbm),
        .pll_hbm_port(pll_hbm_port),
        .pll_hbm_ecc(pll_hbm_ecc), .pll_hbm_cdc(pll_hbm_cdc), .pll_hbm_obs(pll_hbm_obs),
        .hrst(hrst),
        .ck(ck),
        .rsi(rsi),
        .pc(pc),
        .co(controller_co),
        .es(es),
        .er(er),
        .po(po),
        .pi(pi),
        .ki(ki),
        .ko(ko),
        .fi(fi),
        .fo(fo),
        .static_cmd_owner(static_cmd_owner),
        .static_cmd(static_cmd_mu),
        .reserved_rd(reserved_rd),
        .reserved_static_col(reserved_static_col),
        .reserved_write_col(reserved_write_col),
        .static_epoch(static_epoch),
        .expected_raw_valid(expected_raw_valid),
        .cfg_stack(cfg_stack),
        .es_context(es_context),
        .es_expected_valid(es_expected_valid),
        .es_expected_identity(es_expected_identity),
        .es_expected_address(es_expected_address),
        .es_expected_pc(es_expected_pc),
        .es_expected_stack(es_expected_stack),
        .native_commit_valid(native_commit_valid),
        .native_commit_identity(native_commit_identity),
        .native_commit_address(native_commit_address),
        .corrected_epoch(corrected_epoch),
        .completion_v(completion_v),
        .completion_we(completion_we),
        .completion_fault(completion_fault),
        .idle_core(idle_core),
        .idle_hbm(idle_hbm),
        .drain_fault_core(drain_fault_core),
        .drain_fault_hbm(drain_fault_hbm)
    );
    qkd_controller_hbm_calendar #(.CORE_CLOCK(CORE_CLOCK),.N(16), .ROW0(64), .MUT(0)) u_calendar (
        .hck(cal_hck),
        .rst_n(cal_rst_n),
        .cfg_we(cal_cfg_we),
        .cfg_addr(cal_cfg_addr),
        .cfg_data(cal_cfg_data),
        .seal(cal_seal),
        .go(cal_go),
        .epoch(cal_epoch),
        .layer(cal_layer),
        .static_cmd_owner(static_cmd_owner),
        .static_cmd(static_cmd),
        .reserved_rd(reserved_rd),
        .reserved_static_col(reserved_static_col),
        .reserved_write_col(reserved_write_col),
        .static_epoch(static_epoch),
        .expected_raw_valid(expected_raw_valid),
        .fault(cal_fault_hbm),
        .idle(cal_idle_hbm)
    );
    // qkd_kv_mu_rrow map, inline (no new source file in the parent's source lists): static_cmd = {first sector10,
    // command32 = {op2, n11, row19}, bit0}; KV descriptor = op 0 / 3 with row[18:8] == 0 -> row[9:8] |= user
    wire mu_kv = (MU != 0) && (static_cmd[32:31] == 2'd0 || static_cmd[32:31] == 2'd3) && static_cmd[19:9] == 11'd0;
    assign static_cmd_mu = {static_cmd[42:11], static_cmd[10:9] | (mu_kv ? static_epoch[1:0] : 2'd0), static_cmd[8:0]};
    qkd_kv_hbm_elastic_front_mc_nc #(.NBLK(4), .BLK(8), .STRIDE(1), .MUT(0)) u_front (
        .pll_hbm(front_hck),
        .hrst(hrst),
        .pll_hbm_data(front_hbm_data),
        .co_in(controller_co),
        .epoch_in(corrected_epoch),
        .blk_go(front_blk_go),
        .co_out(front_co),
        .epoch_out(front_epoch),
        .compiled_hbm_put(front_put),
        .blk_freed(front_blk_freed),
        .hold(front_hold),
        .stall_edges(front_stall_edges),
        .occupancy(front_occupancy),
        .idle(front_idle_hbm),
        .fault_overflow(front_fault_overflow_hbm),
        .fault_go(front_fault_go_hbm)
    );
    qkd_static_kv_return_slots_mc_nc #(.DEPTH(8)) u_return (
        .pll_hbm(return_hck),
        .hrst(hrst),
        .ck(return_ck),
        .rsi(rsi),
        .pll_hbm_data(return_hbm_data),
        .controller_co(front_co),
        .controller_epoch(front_epoch),
        .compiled_hbm_put(front_put),
        .expected_put(expected_put),
        .expected_sector(expected_sector),
        .expected_epoch(expected_epoch),
        .expected_layer(expected_layer),
        .actual_valid(actual_valid),
        .actual_sector(actual_sector),
        .actual_epoch(actual_epoch),
        .actual_layer(actual_layer),
        .actual_data(actual_data),
        .fault_hbm(return_fault_hbm),
        .fault_core(return_fault_core),
        .idle_hbm(return_idle_hbm),
        .idle_core(return_idle_core)
    );
endmodule

module qkd_kv_hbm_elastic_front_mc_nc #(
    parameter integer NBLK = 4,           // sized: worst occupancy BLK + GO_DLY(17) + 2 = 27 <= 32 at one read per edge
    parameter integer BLK = 8,
    parameter integer STRIDE = 1,
    parameter integer MUT = 0   // 1: read address +1, 2: ready one sector early, 3: release ignores ready
)(
    input wire pll_hbm, hrst,
    input wire [3:0] pll_hbm_data,
    input wire [281:0] co_in,
    input wire [15:0] epoch_in,
    input wire blk_go,
    output wire [281:0] co_out,
    output wire [15:0] epoch_out,
    output wire compiled_hbm_put,
    output reg blk_freed,
    output reg hold,
    output reg [15:0] stall_edges,
    output reg [$clog2(NBLK*BLK):0] occupancy,   // registered
    output reg idle,                        // registered: nothing landed-unreleased, no release pending/emitting (KV drain)
    output reg fault_overflow, fault_go
);
    localparam integer DEPTH = NBLK * BLK;
    localparam integer AW = $clog2(DEPTH);
    localparam integer BW = $clog2(BLK);
    localparam integer SW = (STRIDE > 1) ? $clog2(STRIDE) : 1;
    localparam integer PW = $clog2(NBLK + 1) + 1;
    // sized constants (plain Verilog: the ORFS yosys has no width casts)
    localparam [AW:0] C_BLK = BLK, C_BLK1 = BLK - 1, C_DEPTH = DEPTH;
    localparam [SW-1:0] C_S1 = STRIDE - 1, C_S0 = 0;
    localparam [BW-1:0] C_B1 = BLK - 1;
    localparam [PW-1:0] C_NBLK = NBLK, C_P1 = 1, C_P0 = 0;
    initial if (NBLK < 2 || (NBLK & (NBLK-1)) != 0 || BLK < 2 || (BLK & (BLK-1)) != 0 || STRIDE < 1)
        $error("elastic front: NBLK>=2 and BLK>=2 powers of two, STRIDE>=1");

    (* keep *) reg hr;
    always @(posedge pll_hbm) hr <= hrst;

    // ---- landing side: actual arrival, in order --------------------------------------------------------------
    (* keep *) reg land_v;
    (* keep *) reg [296:0] land_d;
    always @(posedge pll_hbm or negedge hr)
        if (!hr) land_v <= 1'b0; else land_v <= co_in[0];
    always @(posedge pll_hbm) land_d <= {epoch_in, co_in[281:1]};
    wire [296:0] mem_rd;
    reg [AW:0] wp, rp, bs;          // write, emit read, next block start (entries, wrap bit)
    wire [AW:0] filled = wp - bs;   // landed entries of the next block to release and beyond
    wire ready = (MUT == 3) ? 1'b1 : (MUT == 2) ? (filled >= C_BLK1) : (filled >= C_BLK);
    // Four independently delivered, phase-aligned storage clocks. No clock
    // gating or generated clock; the die delivers every root at the same phase.
    // Data never moves between the storage roots; each holds a fixed bit slice.
    genvar bank;
    generate for (bank=0; bank<4; bank=bank+1) begin : g_storage
        localparam integer LO=bank*75, WD=(LO+75>297)?297-LO:75;
        reg [WD-1:0] bank_mem[0:DEPTH-1];
        assign mem_rd[LO+:WD]=bank_mem[ra_c[AW*(bank*4)+:AW]];
        always @(posedge pll_hbm_data[bank])
            if (land_v) bank_mem[wp[AW-1:0]] <= land_d[LO+:WD];
    end endgenerate

    // ---- release side: compiled blk_go, one ready check per block --------------------------------------------
    // blk_go is captured at its pin (first put 3 edges after blk_go at the pin)
    (* keep *) reg go_q;
    always @(posedge pll_hbm or negedge hr) if (!hr) go_q <= 1'b0; else go_q <= blk_go;
    reg [PW-1:0] pending;
    reg emitting;
    reg [BW-1:0] cnt;
    reg [SW-1:0] sc;
    wire last = emitting && sc == C_S1 && cnt == C_B1;
    wire idle_next = !emitting || last;     // back-to-back blocks: next block starts on the last take edge
    wire start = pending != 0 && idle_next && ready;
    wire take = emitting && sc == C_S1;
    reg put_q;
    reg [296:0] out_q;
    // gate r1 (7.7k-load rp bits on the 32:1 read mux): the read address is REPLICATED once per <= 19-bit slice of the
    // 297-b word (16 keep_hierarchy pointer copies advancing on take exactly as rp), ~300 mux loads a copy
    localparam integer NG = 16, SLW = (297 + NG - 1) / NG;
    wire [AW*NG-1:0] ra_c;
    genvar gr;
    generate for (gr = 0; gr < NG; gr = gr + 1) begin : g_ra
        (* keep_hierarchy *) qkd_kvef_mc_rp #(.AW(AW), .INIT(MUT == 1 ? 1 : 0)) u_rp (.clk(pll_hbm), .rst_n(hr), .adv(take),
            .q(ra_c[AW*gr +: AW]));
    end endgenerate    always @(posedge pll_hbm or negedge hr)
        if (!hr) begin
            wp <= 0; rp <= 0; bs <= 0; pending <= 0; emitting <= 0; cnt <= 0; sc <= 0;
            put_q <= 0; blk_freed <= 0; hold <= 0; stall_edges <= 0; fault_overflow <= 0; fault_go <= 0; idle <= 1'b1;
            occupancy <= 0;
        end else begin
            put_q <= 0; blk_freed <= 0;
            occupancy <= wp - rp;
            idle <= wp == rp && !land_v && pending == 0 && !emitting;
            if (land_v) begin
                wp <= wp + 1'b1;
                if (wp - rp == C_DEPTH) fault_overflow <= 1'b1;
            end
            pending <= pending + (go_q ? C_P1 : C_P0) - (start ? C_P1 : C_P0);
            if (go_q && pending == C_NBLK) fault_go <= 1'b1;
            hold <= pending != 0 && idle_next && !ready;
            if (pending != 0 && idle_next && !ready && stall_edges != 16'hffff) stall_edges <= stall_edges + 1'b1;
            if (emitting) begin
                sc <= (sc == C_S1) ? C_S0 : sc + 1'b1;
                if (take) begin
                    put_q <= 1'b1; rp <= rp + 1'b1; cnt <= cnt + 1'b1;
                    if (last) begin emitting <= 1'b0; blk_freed <= 1'b1; end
                end
            end
            if (start) begin emitting <= 1'b1; cnt <= 0; sc <= C_S1; bs <= bs + C_BLK; end
        end
    always @(posedge pll_hbm) if(take)out_q<=mem_rd;

    // ---- controller-format output (drives qkd_static_kv_return_slots) ----------------------------------------
    // (nc) no pass-through fields: the controller has no legacy write completion / hand-off word
    assign co_out = {out_q[280:0], put_q};
    assign epoch_out = out_q[296:281];
    assign compiled_hbm_put = put_q;
endmodule

module qkd_static_kv_return_slots_mc_nc #(parameter integer DEPTH=8)(
 input wire pll_hbm,hrst,ck,rsi,
 input wire [3:0] pll_hbm_data,
 input wire [281:0] controller_co,input wire [15:0] controller_epoch,
 input wire compiled_hbm_put,
 input wire expected_put,input wire [9:0] expected_sector,
 input wire [15:0] expected_epoch,input wire [5:0] expected_layer,
 output reg actual_valid,output reg [9:0] actual_sector,
 output reg [15:0] actual_epoch,output reg [5:0] actual_layer,
 output reg [255:0] actual_data,output reg fault_hbm,output reg fault_core,
 output reg idle_hbm,output reg idle_core
);
 localparam integer AW=$clog2(DEPTH);
 initial if(DEPTH<4 || (DEPTH&(DEPTH-1))!=0)$error("static return depth must be power of two >=4");
 (* keep *)reg hr;
 always @(posedge pll_hbm)hr<=hrst;
 // mc_r4: the core reset capture is replicated per region (VIS-ROM QKV-13: one rs flop drove 301 loads in the mc3b gate):
 // rs_a ring state (rp/consumed/actual/fault), rs_b publication synchronisers, rs_c slot/idle/read-pointer copies
 // (mc_r5: rs_a / rs_c / hr are also the synchronous clear terms of the fault_core / idle_core / *_hbm pin flops)
 (* keep *)reg rs_a,rs_b,rs_c;
 always @(posedge ck)begin rs_a<=rsi;rs_b<=rsi;rs_c<=rsi;end
 (* keep *)reg observed,write_slot;
 (* keep *)reg [287:0] hd;
 always @(posedge pll_hbm)hd<={controller_epoch,controller_co[17:12],controller_co[11:9],controller_co[7:1],controller_co[281:26]};
 always @(posedge pll_hbm or negedge hr)
  if(!hr)begin observed<=0;write_slot<=0;end
  else begin observed<=controller_co[0];write_slot<=compiled_hbm_put;end
 (* keep *)reg slot;
 (* keep *)reg [31:0] meta;
 always @(posedge ck)meta<={expected_epoch,expected_layer,expected_sector};
 always @(posedge ck or negedge rs_c)if(!rs_c)slot<=0;else slot<=expected_put;
 wire [287:0] read_data;
 reg [DEPTH-1:0] published,consumed,observed_valid;
 (* async_reg="true" *)reg [DEPTH-1:0] pub_sync1,pub_sync2,done_sync1,done_sync2;
 // Local-domain drain observations, not a ready or scheduling interface.
 // Both exports plus upstream controller/front quiet are required at the parent.
 // Core publication synchronizers can lag a new HBM write; idle_core alone
 // therefore cannot establish whole-ring or whole-KV drained.
 // mc_r3b (Q-ELEM 10-16): idle_hbm no longer looks at the raw controller_co[0] / compiled_hbm_put pins (the r3
 // route failed CTS hold/setup on that pin -> compare -> idle_hbm cone: setup -527 ps / hold -90 ps); registered pin
 // captures only (drain observation only; no schedule uses it).
 // mc_r3c (Q-ELEM-RING 10-16): exactly the original observation one local edge later, never earlier: *_pre holds
 // edge e's registered terms, edge e+1 ANDs in the pin captures of edge e (observed/write_slot; slot).
 // mc_r5 (Q-KVRET 10-16): mc_r4's form (P && !slot && !actual_valid, one stage) ANDed the CURRENT occupancy with the
 // previous edge's pin capture and asserted idle_core one edge early vs the reference (tb_static_return_idle_mc FATAL
 // at both phases); the mc_r3c two-stage form is restored on mc_r4's regional resets.
 // mc_r5: the four status exports (idle_*, fault_*) are PLAIN pin flops (no asynchronous clear) with a synchronous
 // regional reset term; their Q drives the port only (sticky fault state is a separate internal flop). Measured on the
 // routed mc3c view: idle_core launch 223.1 ps = DFFASRHQN clk->q + the standard BUF/HB4/BUF out pad (~190 ps, as
 // every data pin) + a late lone-sink leaf at the N face (clock 251.4 vs 231.6 ps at the E-face data pin flops).
 // Reset release is cycle-identical to the asynchronous form (the regional reset flop is low on the release edge);
 // on reset ASSERTION the exports clear one local edge later (drain/fault observations; no schedule uses them).
 (* keep *)reg idle_hbm_pre;
 always @(posedge pll_hbm or negedge hr)
  if(!hr)idle_hbm_pre<=0;
  else idle_hbm_pre<=(published==done_sync2) && !observed && !write_slot;
 always @(posedge pll_hbm)idle_hbm<=hr && idle_hbm_pre && !observed && !write_slot;
 // mc_r5 (10-17, recipe 4 / no pin_reg_split): slot_d is the internal copy of actual_valid (both <= slot), so the
 // actual_valid export flop drives its port only
 (* keep *)reg idle_core_pre,slot_d;
 always @(posedge ck or negedge rs_c)
  if(!rs_c)idle_core_pre<=0;
  else idle_core_pre<=(pub_sync2==consumed) && !slot && !slot_d;
 always @(posedge ck)idle_core<=rs_c && idle_core_pre && !slot;
 reg [AW:0] wp,rp;
 wire [AW-1:0] wa=wp[AW-1:0];
`ifdef OT_KV_RETURN_MUT_READ_ADDR
 wire [AW-1:0] ra=rp[AW-1:0]+1'b1;
`else
 wire [AW-1:0] ra=rp[AW-1:0];
`endif
 // mc_r5: sticky fault state (internal) and its plain pin-flop export load the same next value every edge
 (* keep *)reg fault_hbm_s,fault_core_s;
 wire fault_hbm_set=(observed !== write_slot) || (write_slot && done_sync2[wa] !== wp[AW]);
 wire fault_core_set=slot && (pub_sync2[ra] !== ~rp[AW] || observed_valid[ra] !== 1'b1 || read_data[287:256] !== meta);
 always @(posedge pll_hbm or negedge hr)
  if(!hr)begin wp<=0;published<=0;observed_valid<=0;done_sync1<=0;done_sync2<=0;fault_hbm_s<=0;end
  else begin
   done_sync1<=consumed;done_sync2<=done_sync1;
   if(fault_hbm_set)fault_hbm_s<=1;
   if(write_slot)begin
    published[wa]<=~wp[AW];observed_valid[wa]<=observed;
    wp<=wp+1'b1;
   end
  end
 always @(posedge pll_hbm)fault_hbm<=hr && (fault_hbm_s || fault_hbm_set);
 // Storage roots are independent die clock entries with exactly the same
 // frequency/phase as pll_hbm. Every fixed 72-bit slice has <= DEPTH*72 sinks.
 genvar bank;
 generate for(bank=0;bank<4;bank=bank+1)begin:g_storage
  reg [71:0] bank_data[0:DEPTH-1];
  // mc_r3b: the 64:1 read mux select is a per-18-bit pointer copy (4 per bank, 16 total), not the one rp
  // (mc3b gate: rp[1] drove 18,407 mux loads). Each copy advances on slot exactly as rp (keep_hierarchy).
  genvar q;
  for(q=0;q<4;q=q+1)begin:g_rq
   wire [AW-1:0] rq;
   (* keep_hierarchy *) qkd_ksr_mc_rp #(.AW(AW),
`ifdef OT_KV_RETURN_MUT_READ_ADDR
    .INIT(1)
`else
    .INIT(0)
`endif
   ) u_rq(.clk(ck),.rst_n(rs_c),.adv(slot),.q(rq));
   assign read_data[bank*72+q*18+:18]=bank_data[rq][q*18+:18];
  end
  always @(posedge pll_hbm_data[bank])
   if(hr && write_slot)bank_data[wa]<=hd[bank*72+:72];
 end endgenerate
 always @(posedge ck or negedge rs_b)
  if(!rs_b)begin pub_sync1<=0;pub_sync2<=0;end
  else begin pub_sync1<=published;pub_sync2<=pub_sync1;end
 always @(posedge ck or negedge rs_a)
  if(!rs_a)begin rp<=0;consumed<=0;actual_valid<=0;slot_d<=0;fault_core_s<=0;end
  else begin
   actual_valid<=slot;slot_d<=slot;
   if(fault_core_set)fault_core_s<=1;
   if(slot)begin
    actual_data<=read_data[255:0];actual_sector<=read_data[265:256];
    actual_layer<=read_data[271:266];actual_epoch<=read_data[287:272];
    consumed[ra]<=~rp[AW];rp<=rp+1'b1;
   end
  end
 always @(posedge ck)fault_core<=rs_a && (fault_core_s || fault_core_set);
endmodule
