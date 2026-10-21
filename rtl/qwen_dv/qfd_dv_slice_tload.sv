`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_slice_tload -- QW-F16PROG4 10-19: the per-slice PRIVATE_CALR table-ROM load path (selected in
// artifacts/qw-calr-installed-assets-model-1019 README: 1664 FF / 6 ROM per loader+calendar).  Three parts, all static:
//   1. 9-bit request face  treq = {valid, stage[5:0], user[1:0]}  (the CALR LOCAL4 table_load pulse that the CTLM core
//      registers once (qfd_tt_ctlm_dv_gi g_calr.treq_q) and the die transports as an ordinary registered lane).  Here it
//      lands in ONE face register; reset lands in 2 registered stages (rl1 -> rl2) at the face.  No ready, no credit.
//   2. the real qfd_dv_table_rom_loader #(SLICE, BTAB_COMPACT 1, WE_COPIES NWC): four 4096x266 mask-ROM macros, fixed 88
//      reads, first VM write 3 edges / last 90 edges after its sample (inherited contract).
//   3. the VM table-write join: the loader write wins its slot (selected by NWC kept tw_we copies, <= 32 select loads each);
//      a stream write in the SAME edge is a COLLISION: both writes are suppressed (tw_we = 0) and the sticky fault rises.
//      The compiler reserves an exclusive static window (no stream table write during a load), so a collision is a
//      schedule fault, never arbitrated.
// Edge price (handed to the schedule, tools/qwen_static_schedule/f16_calr_edges.py): cal table_load E -> CTLM treq_q E+1
// -> die lane (+T_die, GEN) -> face rq +1 -> loader sample +1 -> first VM write +3, final VM write +90 after the sample.
// MUT (bench mutants only): 1 collision not suppressed (stream write passes), 2 face stage bit 0 dropped,
//   3 no collision fault, 4 face register bypassed (request one edge early), 5 join select uses copy 0 for kind/addr only
//   wrong polarity (stream bundle on loader edge).
// =====================================================================================================================
module qfd_dv_slice_tload #(
    parameter integer SLICE = 0,
    parameter integer CAPTURE_MUT = 0,
    parameter integer CAPTURE_STAGE = 0,
    parameter integer LOCAL_JOIN = 0,            // opt-in: 16-bit data / 12-bit address select groups (<=32 gate loads)
    parameter integer REGISTERED_JOIN = 0,       // opt-in one-hot AND capture: loader age unchanged, stream +1 edge
    parameter integer NWC = 34,                  // 32 data copies (32 bits each) + kind + addr
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [8:0]    treq,                   // {valid, stage 6, user 2}: registered CALR request lane
    input  wire          s_we,                   // stream table write (qfd_dv_stream tw_*)
    input  wire [1:0]    s_kind,
    input  wire [23:0]   s_addr,
    input  wire [1023:0] s_data,
    output wire          tw_we,                  // joined write -> qfd_dv_vm tw_*
    output wire [1:0]    tw_kind,
    output wire [23:0]   tw_addr,
    output wire [1023:0] tw_data,
    output wire          busy,                   // observation only (never a waiter)
    output wire          done,
    output reg           fault
);
    initial if (NWC != 34) $error("qfd_dv_slice_tload: NWC must be 34 (32 data + kind + addr copies)");
    initial if (REGISTERED_JOIN && (!LOCAL_JOIN || CAPTURE_STAGE!=1))
        $error("REGISTERED_JOIN requires LOCAL_JOIN1/CAPTURE_STAGE1");
    // ---- reset landing (2 registered stages at the face)
    reg rl1, rl2;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin rl1 <= 1'b0; rl2 <= 1'b0; end
        else begin rl1 <= 1'b1; rl2 <= rl1; end
    // ---- request face register (valid resettable; stage/user unreset payload, qualified by valid)
    reg       rq_v;
    reg [5:0] rq_stage;
    reg [1:0] rq_user;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) rq_v <= 1'b0;
        else rq_v <= rl2 && treq[8];
    always @(posedge ck) begin
        rq_stage <= treq[7:2] & ((MUT == 2) ? 6'b111110 : 6'b111111);
        rq_user  <= treq[1:0];
    end
    wire       l_start = (MUT == 4) ? (rl2 && treq[8]) : rq_v;
    wire [5:0] l_stage = (MUT == 4) ? treq[7:2] : rq_stage;
    wire [1:0] l_user  = (MUT == 4) ? treq[1:0] : rq_user;
    // ---- the real loader (four ROM macros)
    wire          l_we, l_fault;
    localparam integer JOIN_DATA_GROUPS = LOCAL_JOIN ? 64 : 32;
    localparam integer JOIN_DATA_BITS = LOCAL_JOIN ? 16 : 32;
    localparam integer JOIN_COPIES = LOCAL_JOIN ? 67 : NWC;
    wire [JOIN_COPIES-1:0] l_we_k;
    wire [1:0]    l_kind;
    wire [23:0]   l_addr;
    wire [1023:0] l_data;
    qfd_dv_table_rom_loader #(.SLICE(SLICE), .BTAB_COMPACT(1), .CAPTURE_STAGE(CAPTURE_STAGE), .CAPTURE_MUT(CAPTURE_MUT), .LOCAL_CTRL(LOCAL_JOIN), .JOIN_CAPTURE(REGISTERED_JOIN), .WE_COPIES(JOIN_COPIES)) u_ld (.ck(ck), .rst_n(rst_n),
        .start(l_start), .stage(l_stage), .user_id(l_user), .other_table_write(s_we),
        .tw_we(l_we), .tw_we_k(l_we_k), .tw_kind(l_kind), .tw_addr(l_addr), .tw_data(l_data),
        .busy(busy), .done(done), .fault(l_fault));
    // ---- VM join: loader bundle iff loader write (kept copy select), else stream bundle; same edge = collision
    genvar gi;
    wire stream_we;
    generate if(REGISTERED_JOIN)begin:g_registered_join
        // Fuse the loader bundle's original capture edge with the join's
        // one-hot data gates. Every arm performs real selection work; the
        // following output pin register receives only their OR. There is no
        // payload->identity-FF chain or late select-FF->whole mux path.
        for(gi=0;gi<JOIN_DATA_GROUPS;gi=gi+1)begin:g_data
            reg [JOIN_DATA_BITS-1:0] loader_arm,stream_arm;
            always @(posedge ck)begin
                loader_arm<=l_we_k[gi]?l_data[JOIN_DATA_BITS*gi+:JOIN_DATA_BITS]:{JOIN_DATA_BITS{1'b0}};
                stream_arm<=l_we_k[gi]?{JOIN_DATA_BITS{1'b0}}:s_data[JOIN_DATA_BITS*gi+:JOIN_DATA_BITS];
            end
            assign tw_data[JOIN_DATA_BITS*gi+:JOIN_DATA_BITS]=loader_arm|stream_arm;
        end
        reg [1:0] loader_kind,stream_kind;
        always @(posedge ck)begin
            loader_kind<=(l_we_k[64]^(MUT==5))?l_kind:2'd0;
            stream_kind<=(l_we_k[64]^(MUT==5))?2'd0:s_kind;
        end
        assign tw_kind=loader_kind|stream_kind;
        for(gi=0;gi<2;gi=gi+1)begin:g_addr
            reg [11:0] loader_addr,stream_addr;
            always @(posedge ck)begin
                loader_addr<=l_we_k[65+gi]?l_addr[12*gi+:12]:12'd0;
                stream_addr<=l_we_k[65+gi]?12'd0:s_addr[12*gi+:12];
            end
            assign tw_addr[12*gi+:12]=loader_addr|stream_addr;
        end
        reg stream_we_q;
        always @(posedge ck or negedge rst_n)
            if(!rst_n)stream_we_q<=0;else stream_we_q<=rl2&&s_we;
        assign stream_we=stream_we_q;
    end else begin:g_legacy_join
    assign stream_we=s_we;
    for (gi = 0; gi < JOIN_DATA_GROUPS; gi = gi + 1) begin : g_dsel
        assign tw_data[JOIN_DATA_BITS*gi +: JOIN_DATA_BITS] = l_we_k[gi] ? l_data[JOIN_DATA_BITS*gi +: JOIN_DATA_BITS] : s_data[JOIN_DATA_BITS*gi +: JOIN_DATA_BITS];
    end
    assign tw_kind = (l_we_k[JOIN_DATA_GROUPS] ^ (MUT == 5)) ? l_kind : s_kind;
    if (LOCAL_JOIN) begin : g_addr_local
        assign tw_addr[11:0] = l_we_k[65] ? l_addr[11:0] : s_addr[11:0];
        assign tw_addr[23:12] = l_we_k[66] ? l_addr[23:12] : s_addr[23:12];
    end else begin : g_addr_legacy
        assign tw_addr = l_we_k[33] ? l_addr : s_addr;
    end
    end endgenerate
    wire coll = l_we && stream_we;
    assign tw_we = (MUT == 1) ? (l_we || stream_we) : (l_we ^ stream_we);   // collision: both suppressed
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else if (!rl2) fault <= 1'b0;
        else if ((coll && MUT != 3) || l_fault) fault <= 1'b1;
endmodule
