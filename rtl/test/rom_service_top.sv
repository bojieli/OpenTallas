`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for the ROM read service.
//
// Both checkers -- the Icarus testbench rtl/test/tb_rom_service.sv and the
// the Verilator C++ harness rtl/test/rom_service_harness.cpp -- instantiate this
// module and read the same generated images, so the two simulators exercise
// identical RTL through independently written checkers.
//
// Images are produced by tools/build_rom_service_vectors.py directly from real
// ABI 3.0 ROM deployments built by compiler/backends/rom, and from the ROM read
// stream the real program actually issues on runtime.sim.device.Device:
//
//   rom_object.hex   8 words per ROM MEMORY_OBJECT (rom_plan regions + the
//                    MEMORY_OBJECT descriptors that name them)
//   rom_shard.hex   12 words per RomShard (placement resource and address)
//   rom_repair.hex   4 words per activated spare (RepairMap.entries)
//   rom_mask.hex     2 words per masked region / quarantined resource
//   rom_request.hex  8 words per read request
//   rom_window.hex  20 words per sense granule of authenticated checkpoint
//                    bytes; the campaign's only real-data window
//   rom_meta.hex     the image populations and the campaign totals
//
// THE ARRAY HERE IS VERIFICATION COLLATERAL, NOT A MACRO.  Sense granules
// inside the published window return real checkpoint bytes; everything outside
// it returns a deterministic function of its own address, so that data
// conveyance is still checked end to end for reads far larger than any image
// this repository could carry.  Which requests are which is in rom_meta.hex and
// in the campaign artifact.
// ---------------------------------------------------------------------------
// The default table depths ARE the campaign's depths.  The Icarus bench used to
// override one of them, so the two simulators elaborated different instances of
// the same design and only the capacity guard noticed; the parameters now have
// exactly one place they are written.
module rom_service_top
    import ot_rom_pkg::*;
#(
    parameter integer OBJECTS        = 512,
    parameter integer SHARDS         = 16384,
    parameter integer REGIONS        = 512,
    parameter integer QUARANTINE_ENTRIES = 32,
    parameter integer REPAIR_ENTRIES = 64,
    parameter integer REQUESTS       = 32768,
    parameter integer WINDOW_ENTRIES = 16384,
    parameter integer MASKS          = 256
) (
    input  wire        clk,
    input  wire        rst_n,

    // -- configuration ---------------------------------------------------
    input  wire        cfg_start,
    output reg         cfg_done,

    // -- one request at a time -------------------------------------------
    input  wire        case_start,
    input  wire [31:0] case_index,
    input  wire        out_ready_in,
    input  wire        sense_ready_in,
    output reg         case_busy,
    output reg         case_done,

    // -- what the checkers compare ---------------------------------------
    output wire [1:0]   cmp_status,
    output wire [3:0]   cmp_fault,
    output wire [63:0]  cmp_beats,
    output wire [63:0]  cmp_bytes,
    output wire [63:0]  cmp_activations,
    output wire [63:0]  cmp_beat_digest,
    output wire [63:0]  cmp_data_digest,
    output wire [255:0] cmp_first_beat,
    output wire [255:0] cmp_last_beat,
    output wire [15:0]  cmp_tag,
    output wire [63:0]  count_requests,
    output wire [63:0]  count_beats,
    output wire [63:0]  count_bytes,
    output wire [63:0]  count_activations,
    output wire [63:0]  count_masked,
    output wire [63:0]  count_faults,
    output wire [3:0]   first_fault_class,
    output wire [31:0]  first_fault_object,
    output reg  [63:0]  array_act_count,
    output reg  [63:0]  array_sense_count,
    output reg  [63:0]  bus_bytes,
    output reg  [63:0]  bus_beats,
    output reg  [63:0]  bus_last_beats,
    output reg          window_miss,

    // -- image populations, read straight out of rom_meta.hex ------------
    output wire [31:0] meta_object_count,
    output wire [31:0] meta_shard_count,
    output wire [31:0] meta_repair_count,
    output wire [31:0] meta_mask_count,
    output wire [31:0] meta_request_count,
    output wire [31:0] meta_window_count,
    output wire [31:0] meta_marker_lo,
    output wire [31:0] meta_marker_hi,

    // The table depths this instance was elaborated with, so a checker can
    // refuse a vector set that outgrew them instead of watching it alias.
    output wire [31:0] cap_objects,
    output wire [31:0] cap_shards,
    output wire [31:0] cap_regions,
    output wire [31:0] cap_quarantine_entries,
    output wire [31:0] cap_repair_entries,
    output wire [31:0] cap_requests,
    output wire [31:0] cap_window_entries,
    output wire [31:0] cap_masks,
    output wire [31:0] req_objects,
    output wire [31:0] req_shards,
    output wire [31:0] req_regions,
    output wire [31:0] req_quarantine_entries,
    output wire [31:0] req_repair_entries,
    output wire [31:0] req_requests,
    output wire [31:0] req_window_entries,
    output wire [31:0] req_masks,

    // The service's sticky refusal of a configuration write that named a slot
    // outside a table, sampled twice.
    //
    //   cfg_error_plan  the value after the whole compiled plan has been
    //                   streamed in and before the negative probe below.  It
    //                   must be 0: every slot the loader named exists.
    //   cfg_error       the value after the probe.  It must be 1.
    //
    // The probe is one deliberately out-of-range write, described at C_PROBE.
    // Requiring the marker to be reproduced anyway is what proves the service
    // DROPPED it rather than folding it onto a legal slot -- a fold would have
    // quarantined placement resource 0 in every set, and no set's marker
    // survives that.  A guard that is never made to fire is not evidence.
    output wire        cfg_error,
    output reg         cfg_error_plan
);
    assign cap_objects        = OBJECTS;
    assign cap_shards         = SHARDS;
    assign cap_regions        = REGIONS;
    assign cap_quarantine_entries      = QUARANTINE_ENTRIES;
    assign cap_repair_entries = REPAIR_ENTRIES;
    assign cap_requests       = REQUESTS;
    assign cap_window_entries = WINDOW_ENTRIES;
    assign cap_masks          = MASKS;
    reg [31:0] object_mem  [0:OBJECTS*8-1];
    reg [31:0] shard_mem   [0:SHARDS*12-1];
    reg [31:0] repair_mem  [0:REPAIR_ENTRIES*4-1];
    reg [31:0] mask_mem    [0:MASKS*2-1];
    reg [31:0] request_mem [0:REQUESTS*8-1];
    reg [31:0] window_mem  [0:WINDOW_ENTRIES*20-1];
    reg [31:0] meta_mem    [0:31];

    // Each image is read with the exact bound the meta image declares, so a
    // simulator never reports a short file and a short file never reads as
    // zeros.  rom_meta.hex is exactly 32 words wide by construction.
    integer zi;
    initial begin
        for (zi = 0; zi < OBJECTS*8; zi = zi + 1)        object_mem[zi]  = 32'd0;
        for (zi = 0; zi < SHARDS*12; zi = zi + 1)        shard_mem[zi]   = 32'd0;
        for (zi = 0; zi < REPAIR_ENTRIES*4; zi = zi + 1) repair_mem[zi]  = 32'd0;
        for (zi = 0; zi < MASKS*2; zi = zi + 1)          mask_mem[zi]    = 32'd0;
        for (zi = 0; zi < REQUESTS*8; zi = zi + 1)       request_mem[zi] = 32'd0;
        for (zi = 0; zi < WINDOW_ENTRIES*20; zi = zi + 1)window_mem[zi]  = 32'd0;
        $readmemh("rom_meta.hex", meta_mem);
        if (meta_mem[0] > 0)
            $readmemh("rom_object.hex",  object_mem,  0, meta_mem[0]*8  - 1);
        if (meta_mem[1] > 0)
            $readmemh("rom_shard.hex",   shard_mem,   0, meta_mem[1]*12 - 1);
        if (meta_mem[2] > 0)
            $readmemh("rom_repair.hex",  repair_mem,  0, meta_mem[2]*4  - 1);
        if (meta_mem[3] > 0)
            $readmemh("rom_mask.hex",    mask_mem,    0, meta_mem[3]*2  - 1);
        if (meta_mem[4] > 0)
            $readmemh("rom_request.hex", request_mem, 0, meta_mem[4]*8  - 1);
        if (meta_mem[5] > 0)
            $readmemh("rom_window.hex",  window_mem,  0, meta_mem[5]*20 - 1);
    end

    assign meta_object_count  = meta_mem[0];
    assign meta_shard_count   = meta_mem[1];
    assign meta_repair_count  = meta_mem[2];
    assign meta_mask_count    = meta_mem[3];
    assign meta_request_count = meta_mem[4];
    assign meta_window_count  = meta_mem[5];
    assign meta_marker_lo     = meta_mem[6];
    assign meta_marker_hi     = meta_mem[7];
    assign req_objects        = meta_mem[18];
    assign req_shards         = meta_mem[19];
    assign req_regions        = meta_mem[20];
    // meta[21] is the number of placement resources the runtime health input
    // WITHDREW, not the number the plan has.  The port used to be called
    // req_resources, which is what the field used to carry; a name that has
    // outlived its meaning is how two different quantities end up quoted for
    // each other.
    assign req_quarantine_entries = meta_mem[21];
    assign req_repair_entries = meta_mem[22];
    assign req_requests       = meta_mem[23];
    assign req_window_entries = meta_mem[24];
    assign req_masks          = meta_mem[25];

    // -----------------------------------------------------------------
    // Configuration sequencer: streams the compiled plan into the service.
    // -----------------------------------------------------------------
    localparam [3:0] C_IDLE = 4'd0, C_OBJ = 4'd1, C_SHD = 4'd2, C_REP = 4'd3,
                     C_MSK = 4'd4, C_CNT = 4'd5, C_CLR = 4'd6, C_PROBE = 4'd7,
                     C_DONE = 4'd8;
    // The quarantine list depth at the width cfg_index is driven at.
    localparam [31:0] QUARANTINE_SLOTS = QUARANTINE_ENTRIES;
    reg [3:0]  cstate;
    reg [31:0] ccursor;
    reg [31:0] qslot;
    reg        cfg_valid;
    reg [3:0]  cfg_sel;
    reg [31:0] cfg_index;
    reg [319:0] cfg_data;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cstate    <= C_IDLE;
            ccursor   <= 32'd0;
            qslot     <= 32'd0;
            cfg_valid <= 1'b0;
            cfg_sel   <= 4'd0;
            cfg_index <= 32'd0;
            cfg_data  <= 320'd0;
            cfg_done  <= 1'b0;
            cfg_error_plan <= 1'b0;
        end else begin
            cfg_valid <= 1'b0;
            case (cstate)
            C_IDLE: if (cfg_start) begin
                        cfg_done <= 1'b0;
                        ccursor  <= 32'd0;
                        qslot    <= 32'd0;
                        cstate   <= C_OBJ;
                    end
            C_OBJ: begin
                if (ccursor >= meta_object_count) begin
                    ccursor <= 32'd0;
                    cstate  <= C_SHD;
                end else begin
                    cfg_valid <= 1'b1;
                    cfg_sel   <= ROM_CFG_OBJECT;
                    cfg_index <= ccursor;
                    cfg_data  <= {64'd0,
                                  object_mem[ccursor*8+7], object_mem[ccursor*8+6],
                                  object_mem[ccursor*8+5], object_mem[ccursor*8+4],
                                  object_mem[ccursor*8+3], object_mem[ccursor*8+2],
                                  object_mem[ccursor*8+1], object_mem[ccursor*8+0]};
                    ccursor   <= ccursor + 32'd1;
                end
            end
            C_SHD: begin
                if (ccursor >= meta_shard_count) begin
                    ccursor <= 32'd0;
                    cstate  <= C_REP;
                end else begin
                    cfg_valid <= 1'b1;
                    cfg_sel   <= ROM_CFG_SHARD;
                    cfg_index <= ccursor;
                    // [319:256] resource_address  [255:192] bytes
                    // [191:128] region_offset     [127: 96] resource_index
                    // [ 95: 80] bank  [79:64] tile  [63:48] reticle
                    // [ 47: 32] node_id           [ 31:  0] region_id
                    cfg_data  <= {shard_mem[ccursor*12+11], shard_mem[ccursor*12+10],
                                  shard_mem[ccursor*12+9],  shard_mem[ccursor*12+8],
                                  shard_mem[ccursor*12+7],  shard_mem[ccursor*12+6],
                                  shard_mem[ccursor*12+5],
                                  shard_mem[ccursor*12+4][15:0],
                                  shard_mem[ccursor*12+3][15:0],
                                  shard_mem[ccursor*12+2][15:0],
                                  shard_mem[ccursor*12+1][15:0],
                                  shard_mem[ccursor*12+0]};
                    ccursor   <= ccursor + 32'd1;
                end
            end
            C_REP: begin
                if (ccursor >= meta_repair_count) begin
                    ccursor <= 32'd0;
                    cstate  <= C_MSK;
                end else begin
                    cfg_valid <= 1'b1;
                    cfg_sel   <= ROM_CFG_REPAIR;
                    cfg_index <= ccursor;
                    cfg_data  <= {222'd0,
                                  repair_mem[ccursor*4+3][1:0],
                                  repair_mem[ccursor*4+2],
                                  repair_mem[ccursor*4+1],
                                  repair_mem[ccursor*4+0]};
                    ccursor   <= ccursor + 32'd1;
                end
            end
            C_MSK: begin
                if (ccursor >= meta_mask_count) begin
                    cstate <= C_CNT;
                end else begin
                    cfg_valid <= 1'b1;
                    if (mask_mem[ccursor*2+0] == 32'd0) begin
                        cfg_sel   <= ROM_CFG_REGION_EN;
                        cfg_index <= mask_mem[ccursor*2+1];
                        cfg_data  <= {319'd0, 1'b1};
                    end else begin
                        // A quarantine list slot: the payload names the
                        // withdrawn placement resource, the index is the slot.
                        cfg_sel   <= ROM_CFG_RESOURCE;
                        cfg_index <= qslot;
                        cfg_data  <= {287'd0, 1'b1, mask_mem[ccursor*2+1]};
                        qslot     <= qslot + 32'd1;
                    end
                    ccursor   <= ccursor + 32'd1;
                end
            end
            C_CNT: begin
                cfg_valid <= 1'b1;
                cfg_sel   <= ROM_CFG_OBJECT_N;
                cfg_index <= meta_object_count;
                cstate    <= C_CLR;
            end
            C_CLR: begin
                cfg_valid <= 1'b1;
                cfg_sel   <= ROM_CFG_CLEAR;
                cfg_index <= 32'd0;
                cstate    <= C_PROBE;
            end
            // One deliberately out-of-range configuration write, issued after
            // the whole plan is loaded so that folding it would be visible.
            // It names quarantine slot QUARANTINE_ENTRIES -- one past the last
            // slot there is -- and asks to withdraw placement resource 0,
            // which every plan here places weights on.  If the service folded
            // the slot index instead of refusing it, slot 0 would now withdraw
            // resource 0 and the run's marker would not be reproduced.  The
            // plan-load value of the sticky bit is captured first, because
            // after this write the bit is 1 by construction.
            C_PROBE: begin
                cfg_error_plan <= cfg_error;
                cfg_valid <= 1'b1;
                cfg_sel   <= ROM_CFG_RESOURCE;
                cfg_index <= QUARANTINE_SLOTS;
                cfg_data  <= {287'd0, 1'b1, 32'd0};
                cstate    <= C_DONE;
            end
            C_DONE: begin
                cfg_done <= 1'b1;
                if (!cfg_start) cstate <= C_IDLE;
            end
            default: cstate <= C_IDLE;
            endcase
        end
    end

    // -----------------------------------------------------------------
    // Request issue
    // -----------------------------------------------------------------
    reg        req_valid;
    wire       req_ready;
    reg [31:0] req_object_id;
    reg [63:0] req_byte_offset;
    reg [31:0] req_byte_length;
    reg [15:0] req_tag;
    reg        req_window_mode;
    wire       cmp_valid;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            req_valid       <= 1'b0;
            req_object_id   <= 32'd0;
            req_byte_offset <= 64'd0;
            req_byte_length <= 32'd0;
            req_tag         <= 16'd0;
            req_window_mode <= 1'b0;
            case_busy       <= 1'b0;
            case_done       <= 1'b0;
        end else begin
            case_done <= 1'b0;
            if (case_start && !case_busy) begin
                req_valid       <= 1'b1;
                req_object_id   <= request_mem[case_index*8+0];
                req_byte_offset <= {request_mem[case_index*8+2],
                                    request_mem[case_index*8+1]};
                req_byte_length <= request_mem[case_index*8+3];
                req_tag         <= request_mem[case_index*8+4][15:0];
                req_window_mode <= request_mem[case_index*8+5][0];
                case_busy       <= 1'b1;
            end else begin
                if (req_valid && req_ready) req_valid <= 1'b0;
                if (cmp_valid) begin
                    case_busy <= 1'b0;
                    case_done <= 1'b1;
                end
            end
        end
    end

    // -----------------------------------------------------------------
    // Sense model.  Verification collateral: see the module header.  A granule
    // inside the published window returns authenticated checkpoint bytes; one
    // outside it returns a deterministic function of its own address, so a read
    // far larger than any image this repository could carry is still checked
    // for conveyance and ordering end to end.
    // -----------------------------------------------------------------
    localparam [2:0] SN_IDLE      = 3'd0;
    localparam [2:0] SN_SEARCH_RD = 3'd1;
    localparam [2:0] SN_SEARCH_CMP= 3'd2;
    localparam [2:0] SN_FETCH     = 3'd3;
    localparam [2:0] SN_EMIT      = 3'd4;
    reg [2:0]  sstate;
    reg [31:0] s_resource_q;
    reg [31:0] s_row_q;
    reg [7:0]  s_subword_q;
    reg [31:0] wlo, whi;
    reg [95:0] wkey;
    reg [95:0] wmid_key_q;
    reg        wfound;
    reg [31:0] wslot;
    reg [ROM_SENSE_BITS-1:0] window_data_q;

    wire        sense_req_valid;
    wire [31:0] sense_resource;
    wire [31:0] sense_row;
    wire [7:0]  sense_subword;
    wire        sense_activate;
    reg         sense_rsp_valid;
    reg [ROM_SENSE_BITS-1:0] sense_rsp_data;
    wire        sense_req_ready = sense_ready_in && (sstate == SN_IDLE);

    wire [31:0] wmid = (wlo + whi) >> 1;
    wire [31:0] wmid_s = (wmid >= WINDOW_ENTRIES) ? (WINDOW_ENTRIES - 1) : wmid;

    // The address-derived granule, computed combinationally.  It reads no
    // array, so its sensitivity list stays small.
    reg [ROM_SENSE_BITS-1:0] pattern_data;
    reg [63:0] pat;
    reg [63:0] pidx;
    integer pi;
    always @* begin
        pat = 64'd0;
        pat = rom_digest_step(pat, {32'd0, s_resource_q});
        pat = rom_digest_step(pat, {32'd0, s_row_q});
        pat = rom_digest_step(pat, {56'd0, s_subword_q});
        pattern_data = {ROM_SENSE_BITS{1'b0}};
        for (pi = 0; pi < ROM_SENSE_BITS/64; pi = pi + 1) begin
            pidx = {32'd0, pi[31:0]};
            pat = rom_digest_step(pat, pidx);
            pattern_data[pi*64 +: 64] = pat;
        end
    end

    integer wi;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sstate            <= SN_IDLE;
            sense_rsp_valid   <= 1'b0;
            sense_rsp_data    <= {ROM_SENSE_BITS{1'b0}};
            s_resource_q      <= 32'd0;
            s_row_q           <= 32'd0;
            s_subword_q       <= 8'd0;
            wlo               <= 32'd0;
            whi               <= 32'd0;
            wkey              <= 96'd0;
            wmid_key_q        <= 96'd0;
            wfound            <= 1'b0;
            wslot             <= 32'd0;
            window_data_q     <= {ROM_SENSE_BITS{1'b0}};
            window_miss       <= 1'b0;
            array_act_count   <= 64'd0;
            array_sense_count <= 64'd0;
        end else begin
            sense_rsp_valid <= 1'b0;
            case (sstate)
            SN_IDLE: if (sense_req_valid && sense_req_ready) begin
                s_resource_q      <= sense_resource;
                s_row_q           <= sense_row;
                s_subword_q       <= sense_subword;
                array_sense_count <= array_sense_count + 64'd1;
                if (sense_activate) array_act_count <= array_act_count + 64'd1;
                wfound <= 1'b0;
                if (req_window_mode) begin
                    wkey   <= {sense_resource, sense_row,
                               {24'd0, sense_subword}};
                    wlo    <= 32'd0;
                    whi    <= meta_window_count;
                    sstate <= SN_SEARCH_RD;
                end else begin
                    sstate <= SN_EMIT;
                end
            end
            SN_SEARCH_RD: begin
                wmid_key_q <= {window_mem[wmid_s*20+0],
                               window_mem[wmid_s*20+1],
                               window_mem[wmid_s*20+2]};
                sstate     <= SN_SEARCH_CMP;
            end
            SN_SEARCH_CMP: begin
                if (wlo >= whi) begin
                    // A windowed request whose granule the window does not hold
                    // is a defect in the vector set, not a tolerable miss.
                    if (!wfound) window_miss <= 1'b1;
                    sstate <= SN_FETCH;
                end else if (wmid_key_q == wkey) begin
                    wfound <= 1'b1;
                    wslot  <= wmid_s;
                    wlo    <= whi;
                    sstate <= SN_SEARCH_RD;
                end else if (wmid_key_q < wkey) begin
                    wlo    <= wmid_s + 32'd1;
                    sstate <= SN_SEARCH_RD;
                end else begin
                    whi    <= wmid_s;
                    sstate <= SN_SEARCH_RD;
                end
            end
            SN_FETCH: begin
                for (wi = 0; wi < ROM_SENSE_BITS/32; wi = wi + 1)
                    window_data_q[wi*32 +: 32] <= window_mem[wslot*20+3+wi];
                sstate <= SN_EMIT;
            end
            SN_EMIT: begin
                sense_rsp_valid <= 1'b1;
                sense_rsp_data  <= wfound ? window_data_q : pattern_data;
                sstate          <= SN_IDLE;
            end
            default: sstate <= SN_IDLE;
            endcase
        end
    end

    // -- operand-bus observer -------------------------------------------
    // Counts what actually crosses the bus, independently of the counters the
    // service keeps for itself.  A service that reported a byte it never
    // delivered would show up here and nowhere else.
    wire        svc_cfg_ready;
    wire        out_valid;
    wire [ROM_SENSE_BITS-1:0] out_data;
    wire [15:0] out_bytes;
    wire [15:0] out_tag;
    wire        out_last;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bus_bytes      <= 64'd0;
            bus_beats      <= 64'd0;
            bus_last_beats <= 64'd0;
        end else if (out_valid && out_ready_in) begin
            bus_bytes      <= bus_bytes + {48'd0, out_bytes};
            bus_beats      <= bus_beats + 64'd1;
            if (out_last) bus_last_beats <= bus_last_beats + 64'd1;
        end
    end

    wire _unused_top = &{1'b0, svc_cfg_ready, out_data, out_tag, 1'b0};

    // -----------------------------------------------------------------
    ot_rom_read_service #(
        .OBJECTS        (OBJECTS),
        .SHARDS         (SHARDS),
        .REGIONS        (REGIONS),
        .QUARANTINE_ENTRIES (QUARANTINE_ENTRIES),
        .REPAIR_ENTRIES (REPAIR_ENTRIES),
        .TAG_W          (16)
    ) u_service (
        .clk               (clk),
        .rst_n             (rst_n),
        .cfg_valid         (cfg_valid),
        .cfg_sel           (cfg_sel),
        .cfg_index         (cfg_index),
        .cfg_data          (cfg_data),
        .cfg_ready         (svc_cfg_ready),
        .cfg_error         (cfg_error),
        .req_valid         (req_valid),
        .req_ready         (req_ready),
        .req_object_id     (req_object_id),
        .req_byte_offset   (req_byte_offset),
        .req_byte_length   (req_byte_length),
        .req_tag           (req_tag),
        .sense_req_valid   (sense_req_valid),
        .sense_req_ready   (sense_req_ready),
        .sense_resource    (sense_resource),
        .sense_row         (sense_row),
        .sense_subword     (sense_subword),
        .sense_activate    (sense_activate),
        .sense_rsp_valid   (sense_rsp_valid),
        .sense_rsp_data    (sense_rsp_data),
        .out_valid         (out_valid),
        .out_ready         (out_ready_in),
        .out_data          (out_data),
        .out_bytes         (out_bytes),
        .out_tag           (out_tag),
        .out_last          (out_last),
        .cmp_valid         (cmp_valid),
        .cmp_tag           (cmp_tag),
        .cmp_status        (cmp_status),
        .cmp_fault         (cmp_fault),
        .cmp_beats         (cmp_beats),
        .cmp_bytes         (cmp_bytes),
        .cmp_activations   (cmp_activations),
        .cmp_beat_digest   (cmp_beat_digest),
        .cmp_data_digest   (cmp_data_digest),
        .cmp_first_beat    (cmp_first_beat),
        .cmp_last_beat     (cmp_last_beat),
        .count_requests    (count_requests),
        .count_beats       (count_beats),
        .count_bytes       (count_bytes),
        .count_activations (count_activations),
        .count_masked      (count_masked),
        .count_faults      (count_faults),
        .first_fault_class (first_fault_class),
        .first_fault_object(first_fault_object)
    );
endmodule
