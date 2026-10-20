`timescale 1ns/1ps
// KV-ATTN4 2026-10-20 (COORD 09:56 decision (b), tree K.STA.AHUB): qkd_ahub7_static_io_bo = qkd_ahub6_static_io_safe
// (rtl/hdc/nearhbm/qkd_ahub6_controls.sv, native-32 g6) with AP_OFS / FR_OFS from the boot pins ofs_ap / ofs_fr.
module qkd_ahub7_static_io_bo #(
    parameter integer AP_ADD = 0,             // elaborated AP_RLY + AP_LAND of the parent (structure, not die binding)
    parameter integer WF_RLY = 0,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input wire [3:0] rst_group,
    // attention root word (kvs_attn attn_root {start_qk, ep, layer, ctx, cal[127:16], cal[175:160]})
    input  wire          hs_start,
    input  wire [15:0]   hs_ep,
    input  wire [5:0]    hs_layer,
    input  wire [13:0]   hs_ctx,
    input  wire [111:0]  hs_cal_lo,           // cal[127:16]: LMAX_START, Z_START, HUB_LMAX, HUB_Z, HUB_RECIP, HUB_PUB, PV_START
    input  wire [15:0]   hs_cal_r,            // cal[175:160]: R
    // KV-ATTN4 10-20 boot offsets (quasi-static, two's complement): ofs_ap[8 s +: 8] = AP_OFS_s, ofs_fr = FR_OFS
    input  wire [31:0]   ofs_ap,
    input  wire [7:0]    ofs_fr,
    // to the hub
    output wire          start,
    output wire [31:0] start_all,
    output reg  [15:0]   epoch,
    output reg  [5:0]    layer,
    output reg  [13:0]   T,
    output wire [191:0]  hub_cal,             // {RZ_PUBLISH, RECIP_ISSUE, Z_START, LMAX_ISSUE, Z_IN x4, LMAX_IN x4}
    output reg  [63:0]   si_epoch,
    output reg  [23:0]   si_layer,
    // from the hub
    input  wire          rz_publish,
    input  wire [15:0]   rz_epoch,
    input  wire [127:0]  rz_vector,
    input  wire          hub_fault,
    // export to pvfin.fr and the die hub fault
    output reg           fr_valid,
    output reg  [15:0]   fr_epoch,
    output reg  [127:0]  fr_rz,
    output reg           fault
);
    wire rst_n = rst_group[0];
    assign start = start_all[0];
    // KV-AHUBDW 10-18 (pin rule: flop-first pins): every hs bit lands in a pin flop first (cal_q / cal_r_q beside start /
    // epoch / layer / T); the calendar adds (constant AP_OFS) and the export target are computed from the pin flops in the
    // same cycle start is high, so the hub still samples hub_cal on start (no added edge, behaviour unchanged).
    reg  [111:0] cal_q;  reg [15:0] cal_r_q;
    always @(posedge ck) begin cal_q <= hs_cal_lo; cal_r_q <= hs_cal_r; end
    // KV-ATTN4 10-20 (COORD 09:56 b): AP_OFS / FR_OFS BOOT-PROGRAMMABLE -- the boot pins land in pin flops (static from before
    // rst_n release, any die relay depth) and replace the elaborated constants in the same adders (0 cycles).
    reg  [31:0] ofs_ap_q;  reg [7:0] ofs_fr_q;
    always @(posedge ck) begin ofs_ap_q <= ofs_ap; ofs_fr_q <= ofs_fr; end
    wire [63:0] AP_OFS;
    for (genvar a_ = 0; a_ < 4; a_ = a_ + 1) begin : g_apofs
        assign AP_OFS[16*a_ +: 16] = {{8{ofs_ap_q[8*a_+7]}}, ofs_ap_q[8*a_ +: 8]} + 16'(AP_ADD);
    end
    wire signed [18:0] FR_OFS = {{11{ofs_fr_q[7]}}, ofs_fr_q};
    wire [15:0] c_lmax = cal_q[15:0],  c_z = cal_q[31:16],  c_hl = cal_q[47:32], c_hz = cal_q[63:48];
    wire [15:0] c_hr = cal_q[79:64],   c_hp = cal_q[95:80], c_pv = cal_q[111:96];
    reg  [191:0] cal_n;
    integer s_;
    always @* begin
        cal_n = {c_hp, c_hr, c_hz, c_hl, 128'd0};
        for (s_ = 0; s_ < 4; s_ = s_ + 1) begin
            cal_n[16*s_ +: 16]      = c_lmax + AP_OFS[16*s_ +: 16];
            cal_n[64 + 16*s_ +: 16] = c_z + AP_OFS[16*s_ +: 16];
        end
    end
    // export target from the same command's PV_START + R (17-bit + sign: never wraps into a reachable age)
    // KV-AHUB7 10-19 (COORD 17:00): the export leaves WF_RLY registered relay edges before the W-face pins, so u_io emits
    // WF_RLY edges earlier; FR_OFS keeps its die meaning (fr still lands on pvfin's R slot, no die re-binding).
    wire signed [18:0] tgt_n = $signed({3'd0, c_pv}) + $signed({3'd0, cal_r_q}) + FR_OFS - WF_RLY + ((MUT == 1) ? 1 : 0);
    // pin stage (every input registered; start / held words ride together, so the hub samples one coherent command)
    for(genvar c=0;c<32;c=c+1) begin:g_start_copy
        ot_ahub6_async_copy #(.ID(c)) u_ff(.ck(ck),.rn(rst_group[c/8]),.d(hs_start),.q(start_all[c]));
    end
    // KV-AHUBDW2 10-18: T is HELD with the command (captured with hs_start, as the core holds epoch / layer) so the core
    // can register nblk(T) and its calendar decodes one edge ahead (qkd_ahub6_static_core_la_safe).
    // T_p is the pin flop; T_h holds the start cycle's T; T = start ? T_p : T_h (flops first, then the mux).
    reg  [13:0] T_p, T_h;
    always @(posedge ck) begin
        epoch <= hs_ep; layer <= hs_layer; T_p <= hs_ctx;
        if (start_all[1]) T_h <= T_p;
    end
    always @* T = start_all[2] ? T_p : T_h;
    assign hub_cal = cal_n;
    reg signed [18:0] tgt_q;
    always @(posedge ck) begin
        if(start_all[3]) tgt_q[9:0] <= tgt_n[9:0];
        if(start_all[4]) tgt_q[18:10] <= tgt_n[18:10];
    end
    // held si identity (the native service's held_epoch / held_layer, captured on start)
    for(genvar c=0;c<4;c=c+1) begin:g_identity
        always @(posedge ck) if(start_all[5+c]) si_epoch[16*c+:16] <= epoch;
        always @(posedge ck) if(start_all[9+c/2]) si_layer[6*c+:6] <= layer;
    end
    // ---- reciprocal export: one registered word at io age tgt ---------------------------------------------------------
    reg         active, published, xf;
    reg  [15:0] age;
    reg  [15:0] prev_ep;
    wire [16:0] age_nx = start_all[11] ? 17'd1 : {1'b0, age} + 17'd1;     // io age of the NEXT cycle
    // KV-AHUBDW2 10-18 (route a1: u_io.cal_r_q -> PV_START + R adder -> age compare -> 145 export enables at the W face,
    // -412 ps): the export edge is decided ONE EDGE AHEAD into em_q from the latched target tgt_q (a 19-bit equality of
    // flops), so the export flops' enable is one flop.  Same export edge as before for every meetable slot; a slot < 3
    // (export on the start edge or the one after, never a compiled slot: PV_START + R is hundreds of cycles) is now an
    // unmeetable-slot fault, and a start on a pending export edge (the next command colliding with the export) faults.
    reg         em_q;
    wire        emit   = em_q;
    // KV-AHUBDW2 a2e 10-18 (gate a2d: u_io.em_q (397,531) -> W-face fr_rz / fr_epoch export flops -11.1 ps, 16 levels over
    // ~660 um): em_w is a kept copy of em_q (same D, same reset) that drives only the W-face export (fr_valid, fr_rz,
    // fr_epoch, prev_ep), so it places beside the fr flops and em_q keeps the local io bookkeeping.  Same edges.
    wire [19:0] em_w_copy;
    wire em_w = em_w_copy[0];
    for(genvar c=0;c<20;c=c+1) begin:g_export_copy
        ot_ahub6_async_copy #(.ID(64+c)) u_ff(.ck(ck),.rn(rst_group[1+c/8]),.d(em_d),.q(em_w_copy[c]));
    end
    wire        bad_t  = start_all[11] && (tgt_n < 19'sd3 || tgt_n > 19'sd65535);
    wire        em_d   = !start && active && !em_q && ($signed({3'b0, 16'(age + 16'd1)}) + 19'sd1 == tgt_q);
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin active <= 1'b0; published <= 1'b0; fr_valid <= 1'b0; xf <= 1'b0; em_q <= 1'b0; end
        else begin
            fr_valid <= em_w;
            em_q <= em_d;
            if (start) begin active <= !bad_t; published <= 1'b0; xf <= bad_t || em_q; end
            else begin
                if (active && rz_publish) published <= 1'b1;
                if (rz_publish && !active) xf <= 1'b1;                           // a publication outside any pass
                if (emit) active <= 1'b0;                                          // once per pass
            end
            if (emit && !published) xf <= 1'b1;                                   // rz late: export before publication
            if (active && age_nx[16]) xf <= 1'b1;                                  // slot beyond the age range
        end
    end
    wire [127:0] export_rz = (MUT == 2) ? {rz_vector[127:64], rz_vector[31:0], rz_vector[63:32]} : rz_vector;
    wire [15:0] export_epoch = (MUT == 3) ? prev_ep : rz_epoch;
    for(genvar c=0;c<16;c=c+1) begin:g_export_data
        always @(posedge ck) if(em_w_copy[c]) fr_rz[8*c+:8] <= export_rz[8*c+:8];
    end
    for(genvar c=0;c<2;c=c+1) begin:g_export_epoch
        always @(posedge ck) if(em_w_copy[16+c]) fr_epoch[8*c+:8] <= export_epoch[8*c+:8];
        always @(posedge ck) if(em_w_copy[18+c]) prev_ep[8*c+:8] <= rz_epoch[8*c+:8];
    end
    for(genvar c=0;c<2;c=c+1) begin:g_age
        always @(posedge ck or negedge rst_group[c])
            if(!rst_group[c]) age[8*c+:8]<=0;
            else if(start_all[30+c]) age[8*c+:8]<=(c==0)?8'd1:8'd0;
            else if(active) age[8*c+:8]<=age_nx[8*c+:8];
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0; else fault <= xf || hub_fault;
endmodule
