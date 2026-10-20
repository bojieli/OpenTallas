`timescale 1ns/1ps
// Isolated PC native32 structural candidate; not adopted.
module qkd_kvpc_s_front_native32 #(
    parameter integer NBLK = 4,
    parameter integer BLK = 8,
    parameter integer STRIDE = 1,
    parameter integer MUT = 0   // 1: read address +1, 2: ready one sector early, 3: release ignores ready, 4: bank permutation, 5: no prefetch
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
    output reg [$clog2(NBLK*BLK):0] occupancy,
    output reg idle,
    output reg fault_overflow, fault_go
);
    localparam integer DEPTH = NBLK * BLK;
    localparam integer AW = $clog2(DEPTH);
    localparam integer BW = $clog2(BLK);
    localparam integer SW = (STRIDE > 1) ? $clog2(STRIDE) : 1;
    localparam integer PW = $clog2(NBLK + 1) + 1;
    localparam [AW:0] C_BLK = BLK, C_BLK1 = BLK - 1, C_DEPTH = DEPTH;
    localparam [SW-1:0] C_S1 = STRIDE - 1, C_S0 = 0;
    localparam [BW-1:0] C_B1 = BLK - 1;
    localparam [PW-1:0] C_NBLK = NBLK, C_P1 = 1, C_P0 = 0;
    localparam [AW-1:0] C_RA0 = (MUT == 1) ? 1 : 0;
    initial if (NBLK < 2 || (NBLK & (NBLK-1)) != 0 || BLK < 2 || (BLK & (BLK-1)) != 0 || STRIDE < 1 || DEPTH > 32)
        $error("elastic front: NBLK>=2 and BLK>=2 powers of two, STRIDE>=1, NBLK*BLK<=32");

    // item 3: hr (50 loads) and emitting (606: take = emitting enables the 297-bit out_q) are kept copy families
    (* keep, ot_rst_split *) reg [2:0] hr__qv;
    wire hr = hr__qv[0];
    always @(posedge pll_hbm) hr__qv <= {3{hrst}};
    (* keep *) reg land_v;
    (* keep *) reg [296:0] land_d;
    always @(posedge pll_hbm or negedge hr)
        if (!hr) land_v <= 1'b0; else land_v <= co_in[0];
    always @(posedge pll_hbm) land_d <= {epoch_in, co_in[281:1]};
    wire [296:0] mem_rd;
    reg [AW:0] wp, rp, bs;
    wire [AW:0] filled = wp - bs;
    wire ready = (MUT == 3) ? 1'b1 : (MUT == 2) ? (filled >= C_BLK1) : (filled >= C_BLK);

    (* keep *) reg go_q;
    always @(posedge pll_hbm or negedge hr) if (!hr) go_q <= 1'b0; else go_q <= blk_go;
    reg [PW-1:0] pending;
    (* keep, ot_rst_split *) reg [25:0] emitting__qv;
    wire emitting = emitting__qv[0];
    reg [BW-1:0] cnt;
    reg [SW-1:0] sc;
    wire last = emitting && sc == C_S1 && cnt == C_B1;
    wire idle_next = !emitting || last;
    wire start = pending != 0 && idle_next && ready;
    wire take = emitting && sc == C_S1;
    // KV-PC2: emitting as master + identical copies (the copies' own-Q hold made bit 0 a DFFE and the family REFUSED by
    // ot_rst_copies, gate 164813: 590 loads on one flop).  emitting_m holds the state; every copy loads emitting_nx.
    (* keep *) reg emitting_m;
    wire emitting_nx = start ? 1'b1 : (last ? 1'b0 : emitting_m);
    always @(posedge pll_hbm or negedge hr__qv[1])
        if (!hr__qv[1]) begin emitting_m <= 1'b0; emitting__qv <= 26'd0; end
        else begin emitting_m <= emitting_nx; emitting__qv <= {26{emitting_nx}}; end
    reg put_q;
    reg [296:0] out_q;

    // storage: registered read of mem[ra(t)] issued at t-1 with ra(t) = ra + take (the original pointer copies advance
    // on take exactly as rp).  A same-edge write to that entry blocks the read (no physical collision).
    reg [AW-1:0] ra;
    wire [AW-1:0] ra_next = (MUT == 5) ? ra : (emitting__qv[21] && sc==C_S1) ? ra + 1'b1 : ra;
    wire w_hit = land_v && wp[AW-1:0] == ra_next;
`ifdef OT_KVPC_FRONT_MUT4
    localparam integer RAM_MUT = 1;                 // tile-bench mutant: bank permutation inside the tile
`else
    localparam integer RAM_MUT = (MUT == 4) ? 1 : 0;
`endif
    qkd_kvpc_ram2c #(.WORDS(DEPTH), .BITS(297), .NW(1), .WCLK_MAP(64'd0), .MUT(RAM_MUT)) u_mem (
        .wclk(pll_hbm), .rclk(pll_hbm), .r_ce(!w_hit), .r_addr(ra_next), .rd(mem_rd),
        .w_ce({5{land_v}}), .w_addr(wp[AW-1:0]), .wd(land_d));
`ifndef SYNTHESIS
    reg blk_q;
    always @(posedge pll_hbm) begin
        blk_q <= w_hit;
        if (blk_q && take && hr && MUT == 0) $error("qkd_kvpc_s_front: a consumed read collided with its write");
    end
`endif

    // Reset leaves are existing same-edge face copies: no new release edge.
    // hr0: pointer/counter state27+land/go2; hr1: emitting27; hr2: flags32.
    always @(posedge pll_hbm or negedge hr__qv[0])
        if(!hr__qv[0])begin wp<=0;rp<=0;bs<=0;cnt<=0;sc<=0;ra<=C_RA0;end
        else begin
            if(land_v)wp<=wp+1'b1;
            if(emitting__qv[22])begin
                sc<=(sc==C_S1)?C_S0:sc+1'b1;
                if(sc==C_S1)begin rp<=rp+1'b1;cnt<=cnt+1'b1;ra<=ra+1'b1;end
            end
            if(start)begin cnt<=0;sc<=C_S1;bs<=bs+C_BLK;end
        end
    always @(posedge pll_hbm or negedge hr__qv[2])
        if(!hr__qv[2])begin
            pending<=0;put_q<=0;blk_freed<=0;hold<=0;stall_edges<=0;
            fault_overflow<=0;fault_go<=0;idle<=1;occupancy<=0;
        end else begin
            put_q<=0;blk_freed<=0;occupancy<=wp-rp;
            idle<=wp==rp&&!land_v&&pending==0&&!emitting;
            if(land_v&&wp-rp==C_DEPTH)fault_overflow<=1;
            pending<=pending+(go_q?C_P1:C_P0)-(start?C_P1:C_P0);
            if(go_q&&pending==C_NBLK)fault_go<=1;
            hold<=pending!=0&&idle_next&&!ready;
            if(pending!=0&&idle_next&&!ready&&stall_edges!=16'hffff)stall_edges<=stall_edges+1'b1;
            if(emitting__qv[23]&&sc==C_S1)begin put_q<=1;if(last)blk_freed<=1;end
        end
    // Distinct kept control state is referenced by each <=15-bit payload slice.
    // The old canonical pin split balanced direct loads but INV-transparent
    // effective union still gave one emitting root586. No new edge or storage.
    for(genvar g=0;g<20;g=g+1)begin:g_native_payload
        localparam integer LO=g*15,WD=297-LO<15?297-LO:15;
        wire take_local=emitting__qv[g+1] && sc==C_S1;
        always @(posedge pll_hbm)if(take_local)out_q[LO+:WD]<=mem_rd[LO+:WD];
    end
    assign co_out = {out_q[280:0], put_q};
    assign epoch_out = out_q[296:281];
    assign compiled_hbm_put = put_q;
endmodule
