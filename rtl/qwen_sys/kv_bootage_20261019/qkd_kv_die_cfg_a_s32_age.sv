// PRIVATE PROTOTYPE; S32=0 source baseline, S32=1 distributed fields. No parent/view qualification.
`timescale 1ns/1ps
// KV-BOOTAGE 2026-10-19 (coordinator decision, lanes/KVR-DERIVE.md "SPEC for the ONE later re-harden"): qkd_kv_die_cfg plus
// the STATIC-SCHEDULE AGE words (AGES=1).  Identical to rtl/qwen_sys/static_kv_20261014/qkd_kv_die_cfg.sv (kept byte-identical
// for the closed control tile) except NA = 19 age words between the capability word and the seal (AGES=1):
//   word A = 32 + NRST + CAP            attention tile: data[7:0] = PV_LEAD (attn root), data[15:8] = F_DLY (result face,
//                                       root END, cal gen R), data[23:16] = D_QK, data[31:24] = D_RL (cal gen)
//   words A + 1 + p, p = 0, 1           PV pair p control: data[7:0] = FIRST_INPUT_AGE
//   words A + 3 + i, i = 4 s + k        V port vport_<STACKS[s]>_<k>: data[7:0] = RT, data[15:8] = DQ
//   every other data bit must be 0; the seal moves to word A + 19.
// The values are the die's derived static schedule (kv_static_params.schedule on the post-station netlist), written by the
// compiler's boot image (kv_static_kvjf_join.die_cfg_image ages=...); the generator fails when an image value differs from
// the netlist-derived one.  Outputs are static after the seal and read 0 until it (an unloaded age is an invalid schedule
// in every consumer: RT 0 / FIRST_INPUT_AGE 0 / F_DLY 0 fault; PV_LEAD consumers are gated by the sealed capability).
// No handshake, credit or ready: configuration nets, POR-held across the functional re-reset (as the ECTL / reset words).
// MUT: 1-5 as qkd_kv_die_cfg; 6 = age words written one word off (vport i takes word i + 1); 7 = age outputs not gated
// by the seal.
// KVJ-F 2026-10-17 (stub audit K-12, coordinator 0da (d): "REJECT functional config straps: KV ectl cfg and reset delay
// must come from real producers (boot config load)").  The KV die's boot-loaded functional configuration, x1 beside the
// boot dispatcher, written ONLY by qkd_static_kv_boot_dispatch (DIECFG=1) pre-boot image target 10:
//   words 0..31          group i = 8*stack + g: data[4:0] = ECTL A cfg, [9:5] = ECTL B cfg, [14:10] = ECTL C cfg
//                        ({engine 3, stack 2} as the ECTL parts read it); data[63:15] must be 0
//   words 32..32+NRST-1  reset region r: data[7:0] = qkd_rst_region dly (the release calendar D - d_r of region r, from
//                        the die plan's reset relay depths); data[63:8] must be 0
//   word 32+NRST         seal 0x514b5644_43464731 ("QKVDCFG1"): sealed only if every earlier word was written once, in order
// The registers are reset by the package POR ONLY (por_n, the same pad the regional reset roots synchronise), never by a
// functional reset: the HOST loads target 10 after the first (unaligned, dly 0) release, then re-asserts and releases the
// functional resets, which now release aligned; this block keeps its words across that re-reset.  Outputs are static
// after the seal (configuration nets: no production path launches from them after setup).  Any out-of-order, repeated,
// non-zero-padding or post-seal write is a sticky fault (the dispatcher's sink fault), and nothing reads as sealed.
// RTL-BUILD-KV/FAULT 2026-10-18 (P8: attention_programme / attn_root fused_program_capability had no producer): CAP=1
// adds ONE capability word between the reset-region words and the seal:
//   word 32+NRST         data[0] = the boot image's fused attention-programme capability; data[63:1] must be 0
//   seal                 moves to word 32+NRST+CAP
// fused_program_capability = the loaded bit AND sealed: 0 from POR until the whole image is sealed (a request before
// that faults in the service root / programme, as the legacy capability-0 case), then the image's bit, static (POR-only
// reset, survives the functional re-reset).  CAP=0 = the KVJ-F block unchanged (the output is then 0).
// MUT (bench negative controls): 1 = ECTL B / C fields swapped; 2 = padding bits not checked; 3 = reset-region words
// written one region off; 4 = capability taken from data[1]; 5 = capability not gated by the seal.
module qkd_kv_die_cfg_a_s32_age #(parameter integer NRST = 43, parameter integer CAP = 0, parameter integer AGES = 1, parameter integer MUT = 0, parameter integer S32 = 0) (
    input  wire               ck, por_n,
    input  wire               cfg_we, input wire [7:0] cfg_addr, input wire [63:0] cfg_data,
    output reg  [32*5-1:0]    ectl_a_cfg, ectl_b_cfg, ectl_c_cfg,
    output reg  [NRST*8-1:0]  rst_dly,
    output wire               fused_program_capability,
    output wire [31:0]        age_attn,         // {D_RL, D_QK, F_DLY, PV_LEAD}
    output wire [15:0]        age_pv,           // {pair 1, pair 0} FIRST_INPUT_AGE
    output wire [255:0]       age_vport,        // port i: [16 i +: 16] = {DQ, RT}
    output reg                sealed, fault
);
    localparam integer NA = (AGES != 0) ? 19 : 0;
    localparam integer A0 = 32 + NRST + ((CAP != 0) ? 1 : 0);   // first age word
    localparam integer NW = A0 + NA;                              // data words before the seal
    localparam [63:0] SEAL = 64'h514b5644_43464731;
    generate if (NRST < 1 || NW + 1 > 256) begin : g_bad
        initial $fatal(1, "qkd_kv_die_cfg: NRST %0d CAP %0d", NRST, CAP);
    end endgenerate
    // POR: two-flop synchronised release (async assert), as qkd_rst_region
    (* keep *) reg [1:0] ps;
    always @(posedge ck or negedge por_n) if (!por_n) ps <= 2'b00; else ps <= {ps[0], 1'b1};
    wire pr_n = ps[1];
    // write port pin registers
    reg we_q; reg [7:0] a_q; reg [63:0] d_q;
    always @(posedge ck or negedge pr_n) if (!pr_n) we_q <= 1'b0; else we_q <= cfg_we;
    always @(posedge ck) begin a_q <= cfg_addr; d_q <= cfg_data; end
    reg [8:0] next;
    wire is_ectl = a_q < 8'd32;
    wire is_rst  = !is_ectl && a_q < 8'(32 + NRST);
    wire is_cap  = (CAP != 0) && a_q == 8'(32 + NRST);
    wire is_age  = (AGES != 0) && a_q >= 8'(A0) && a_q < 8'(A0 + NA);
    wire [7:0] g_ix = a_q - 8'(A0) + ((MUT == 6) ? 8'd1 : 8'd0);
    wire is_seal = a_q == NW[7:0];
    wire age_pad = (g_ix == 8'd0) ? (d_q[63:32] != 0) : (g_ix == 8'd1 || g_ix == 8'd2) ? (d_q[63:8] != 0) : (d_q[63:16] != 0);
    reg  cap_q;
    reg [31:0] ag_attn; reg [15:0] ag_pv; reg [255:0] ag_vp;
    wire [7:0] r_ix = a_q - 8'd32 + ((MUT == 3) ? 8'd1 : 8'd0);
    wire bad = sealed || ({1'b0, a_q} != next) ||
               (MUT != 2 && ((is_ectl && d_q[63:15] != 0) || (is_rst && d_q[63:8] != 0) || (is_cap && d_q[63:1] != 0) || (is_age && age_pad))) ||
               (is_seal && (d_q != SEAL || next != NW[8:0])) || (!is_ectl && !is_rst && !is_cap && !is_age && !is_seal);
    integer i;
    generate if(S32==0)begin:g_original
    always @(posedge ck or negedge pr_n) begin
        if (!pr_n) begin
            ectl_a_cfg <= 0; ectl_b_cfg <= 0; ectl_c_cfg <= 0; rst_dly <= 0; cap_q <= 1'b0;
            ag_attn <= 32'd0; ag_pv <= 16'd0; ag_vp <= 256'd0;
            sealed <= 1'b0; fault <= 1'b0; next <= 9'd0;
        end else if (we_q) begin
            if (bad || fault) fault <= 1'b1;
            else begin
                next <= next + 9'd1;
                if (is_ectl) begin
                    ectl_a_cfg[5*a_q[4:0] +: 5] <= d_q[4:0];
                    ectl_b_cfg[5*a_q[4:0] +: 5] <= (MUT == 1) ? d_q[14:10] : d_q[9:5];
                    ectl_c_cfg[5*a_q[4:0] +: 5] <= (MUT == 1) ? d_q[9:5] : d_q[14:10];
                end
                if (is_rst && r_ix < NRST) rst_dly[8*r_ix +: 8] <= d_q[7:0];
                if (is_cap) cap_q <= (MUT == 4) ? d_q[1] : d_q[0];
                if (is_age) begin
                    if (g_ix == 8'd0) ag_attn <= d_q[31:0];
                    else if (g_ix < 8'd3) ag_pv[8 * (g_ix - 8'd1) +: 8] <= d_q[7:0];
                    else if (g_ix < 8'd19) ag_vp[16 * (g_ix - 8'd3) +: 16] <= d_q[15:0];
                end
                if (is_seal) sealed <= 1'b1;
            end
        end
    end
    end else begin:g_s32
        localparam integer KE = 16, KR = (NRST + 3) / 4;
        (* keep *) reg [KE+KR-1:0] rcp;
        always @(posedge ck or negedge por_n) if (!por_n) rcp <= {(KE+KR){1'b0}}; else rcp <= {(KE+KR){ps[0]}};
        wire wr = we_q && !(bad || fault);
        // decode and data fan-out (ABC would fold a flat decode into every hold mux: 190+ loads on wr / a_q bits): KEPT
        // predecode wires (ABC boundaries) phi = {wr, is_ectl, a_q[4:3]}, plo = a_q[2:0] one-hot, fe = phi & plo (30
        // hold-mux loads each); rst rows likewise (rhi = {wr, is_rst, r_ix[5:3]}, rlo = r_ix[2:0]); write data from 4 KEPT
        // copies of d_q[14:0] (ectl fields 0..15 / 16..31, rst rows 0..21 / 22..)
        (* keep *) wire [3:0] phi; (* keep *) wire [7:0] plo, rlo; (* keep *) wire [5:0] rhi;
        (* keep *) wire [31:0] fe; (* keep *) wire [NRST-1:0] fr;
        (* keep *) reg [14:0] dqc0, dqc1, dqc2, dqc3;
        always @(posedge ck) begin dqc0 <= cfg_data[14:0]; dqc1 <= cfg_data[14:0]; dqc2 <= cfg_data[14:0]; dqc3 <= cfg_data[14:0]; end
        genvar q;
        for (q = 0; q < 4; q = q + 1) begin : g_phi
            assign phi[q] = wr && is_ectl && a_q[4:3] == q;
        end
        for (q = 0; q < 8; q = q + 1) begin : g_plo
            assign plo[q] = a_q[2:0] == q;
            assign rlo[q] = r_ix[2:0] == q;
        end
        for (q = 0; q < 6; q = q + 1) begin : g_rhi
            assign rhi[q] = wr && is_rst && r_ix[5:3] == q && r_ix[7:6] == 2'd0;
        end
        for (q = 0; q < 32; q = q + 1) begin : g_fe
            assign fe[q] = phi[q/8] && plo[q%8];
        end
        for (q = 0; q < NRST; q = q + 1) begin : g_fr
            assign fr[q] = rhi[q/8] && rlo[q%8];
        end
        always @(posedge ck or negedge pr_n) begin
            if (!pr_n) begin
                cap_q <= 1'b0; sealed <= 1'b0; fault <= 1'b0; next <= 9'd0;
            end else if (we_q) begin
                if (bad || fault) fault <= 1'b1;
                else begin
                    next <= next + 9'd1;
                    if (is_cap) cap_q <= (MUT == 4) ? d_q[1] : d_q[0];
                    if (is_seal) sealed <= 1'b1;
                end
            end
        end
        genvar f, r;
        for (f = 0; f < 32; f = f + 1) begin : g_ef
            wire [14:0] dq = (f < 16) ? dqc0 : dqc1;
            wire [14:0] qf;
            qkd_kv_cfg_age_field #(.W(15)) u_f (.ck(ck), .rn(rcp[f/2]), .en(fe[f]),
                .d({(MUT == 1) ? dq[9:5] : dq[14:10], (MUT == 1) ? dq[14:10] : dq[9:5], dq[4:0]}), .q(qf));
            always @* begin ectl_a_cfg[5*f +: 5] = qf[4:0]; ectl_b_cfg[5*f +: 5] = qf[9:5]; ectl_c_cfg[5*f +: 5] = qf[14:10]; end
        end
        for (r = 0; r < NRST; r = r + 1) begin : g_rf
            wire [7:0] qr;
            qkd_kv_cfg_age_field #(.W(8)) u_r (.ck(ck), .rn(rcp[KE + r/4]), .en(fr[r]), .d((r < 22) ? dqc2[7:0] : dqc3[7:0]), .q(qr));
            always @* rst_dly[8*r +: 8] = qr;
        end
        // PRIVATE age fields: same pin-capture data and write edge; kept <=16-bit fields.
        (* keep *) reg age_por0; always @(posedge ck or negedge por_n) if(!por_n) age_por0<=0;else age_por0<=1;
        (* keep, ot_rst_split *) reg [9:0] age_rcp;
        always @(posedge ck or negedge age_por0) if(!age_por0)age_rcp<=0;else age_rcp<={10{age_por0}};
        (* keep *) reg [9:0] seal_pub;
        always @(posedge ck or negedge age_rcp[9]) if(!age_rcp[9])seal_pub<=0;else if(wr&&is_seal)seal_pub<=10'h3ff;
        (* keep *) wire [2:0] age_hi; (* keep *) wire [7:0] age_lo;
        for(genvar h=0;h<3;h=h+1)begin:g_ahi assign age_hi[h]=wr&&is_age&&g_ix[7:5]==0&&g_ix[4:3]==h;end
        for(genvar l=0;l<8;l=l+1)begin:g_alo assign age_lo[l]=g_ix[2:0]==l;end
        wire en_attn_lo;wire[15:0]q_attn_lo;
        qkd_kv_cfg_age_en e_attn_lo(.h(age_hi[0]),.l(age_lo[0]),.y(en_attn_lo));
        qkd_kv_cfg_age_field #(.W(16)) f_attn_lo(.ck(ck),.rn(age_rcp[0]),.en(en_attn_lo),.d(d_q[15:0]),.q(q_attn_lo));
        always @* ag_attn[15:0]=q_attn_lo;
        wire en_attn_hi;wire[15:0]q_attn_hi;
        qkd_kv_cfg_age_en e_attn_hi(.h(age_hi[0]),.l(age_lo[0]),.y(en_attn_hi));
        qkd_kv_cfg_age_field #(.W(16)) f_attn_hi(.ck(ck),.rn(age_rcp[0]),.en(en_attn_hi),.d(d_q[31:16]),.q(q_attn_hi));
        always @* ag_attn[31:16]=q_attn_hi;
        wire en_pair0;wire[7:0]q_pair0;
        qkd_kv_cfg_age_en e_pair0(.h(age_hi[0]),.l(age_lo[1]),.y(en_pair0));
        qkd_kv_cfg_age_field #(.W(8)) f_pair0(.ck(ck),.rn(age_rcp[1]),.en(en_pair0),.d(d_q[7:0]),.q(q_pair0));
        always @* ag_pv[7:0]=q_pair0;
        wire en_pair1;wire[7:0]q_pair1;
        qkd_kv_cfg_age_en e_pair1(.h(age_hi[0]),.l(age_lo[2]),.y(en_pair1));
        qkd_kv_cfg_age_field #(.W(8)) f_pair1(.ck(ck),.rn(age_rcp[1]),.en(en_pair1),.d(d_q[7:0]),.q(q_pair1));
        always @* ag_pv[15:8]=q_pair1;
        wire en_vp0;wire[15:0]q_vp0;
        qkd_kv_cfg_age_en e_vp0(.h(age_hi[0]),.l(age_lo[3]),.y(en_vp0));
        qkd_kv_cfg_age_field #(.W(16)) f_vp0(.ck(ck),.rn(age_rcp[1]),.en(en_vp0),.d(d_q[15:0]),.q(q_vp0));
        always @* ag_vp[0+:16]=q_vp0;
        wire en_vp1;wire[15:0]q_vp1;
        qkd_kv_cfg_age_en e_vp1(.h(age_hi[0]),.l(age_lo[4]),.y(en_vp1));
        qkd_kv_cfg_age_field #(.W(16)) f_vp1(.ck(ck),.rn(age_rcp[2]),.en(en_vp1),.d(d_q[15:0]),.q(q_vp1));
        always @* ag_vp[16+:16]=q_vp1;
        wire en_vp2;wire[15:0]q_vp2;
        qkd_kv_cfg_age_en e_vp2(.h(age_hi[0]),.l(age_lo[5]),.y(en_vp2));
        qkd_kv_cfg_age_field #(.W(16)) f_vp2(.ck(ck),.rn(age_rcp[2]),.en(en_vp2),.d(d_q[15:0]),.q(q_vp2));
        always @* ag_vp[32+:16]=q_vp2;
        wire en_vp3;wire[15:0]q_vp3;
        qkd_kv_cfg_age_en e_vp3(.h(age_hi[0]),.l(age_lo[6]),.y(en_vp3));
        qkd_kv_cfg_age_field #(.W(16)) f_vp3(.ck(ck),.rn(age_rcp[3]),.en(en_vp3),.d(d_q[15:0]),.q(q_vp3));
        always @* ag_vp[48+:16]=q_vp3;
        wire en_vp4;wire[15:0]q_vp4;
        qkd_kv_cfg_age_en e_vp4(.h(age_hi[0]),.l(age_lo[7]),.y(en_vp4));
        qkd_kv_cfg_age_field #(.W(16)) f_vp4(.ck(ck),.rn(age_rcp[3]),.en(en_vp4),.d(d_q[15:0]),.q(q_vp4));
        always @* ag_vp[64+:16]=q_vp4;
        wire en_vp5;wire[15:0]q_vp5;
        qkd_kv_cfg_age_en e_vp5(.h(age_hi[1]),.l(age_lo[0]),.y(en_vp5));
        qkd_kv_cfg_age_field #(.W(16)) f_vp5(.ck(ck),.rn(age_rcp[4]),.en(en_vp5),.d(d_q[15:0]),.q(q_vp5));
        always @* ag_vp[80+:16]=q_vp5;
        wire en_vp6;wire[15:0]q_vp6;
        qkd_kv_cfg_age_en e_vp6(.h(age_hi[1]),.l(age_lo[1]),.y(en_vp6));
        qkd_kv_cfg_age_field #(.W(16)) f_vp6(.ck(ck),.rn(age_rcp[4]),.en(en_vp6),.d(d_q[15:0]),.q(q_vp6));
        always @* ag_vp[96+:16]=q_vp6;
        wire en_vp7;wire[15:0]q_vp7;
        qkd_kv_cfg_age_en e_vp7(.h(age_hi[1]),.l(age_lo[2]),.y(en_vp7));
        qkd_kv_cfg_age_field #(.W(16)) f_vp7(.ck(ck),.rn(age_rcp[5]),.en(en_vp7),.d(d_q[15:0]),.q(q_vp7));
        always @* ag_vp[112+:16]=q_vp7;
        wire en_vp8;wire[15:0]q_vp8;
        qkd_kv_cfg_age_en e_vp8(.h(age_hi[1]),.l(age_lo[3]),.y(en_vp8));
        qkd_kv_cfg_age_field #(.W(16)) f_vp8(.ck(ck),.rn(age_rcp[5]),.en(en_vp8),.d(d_q[15:0]),.q(q_vp8));
        always @* ag_vp[128+:16]=q_vp8;
        wire en_vp9;wire[15:0]q_vp9;
        qkd_kv_cfg_age_en e_vp9(.h(age_hi[1]),.l(age_lo[4]),.y(en_vp9));
        qkd_kv_cfg_age_field #(.W(16)) f_vp9(.ck(ck),.rn(age_rcp[6]),.en(en_vp9),.d(d_q[15:0]),.q(q_vp9));
        always @* ag_vp[144+:16]=q_vp9;
        wire en_vp10;wire[15:0]q_vp10;
        qkd_kv_cfg_age_en e_vp10(.h(age_hi[1]),.l(age_lo[5]),.y(en_vp10));
        qkd_kv_cfg_age_field #(.W(16)) f_vp10(.ck(ck),.rn(age_rcp[6]),.en(en_vp10),.d(d_q[15:0]),.q(q_vp10));
        always @* ag_vp[160+:16]=q_vp10;
        wire en_vp11;wire[15:0]q_vp11;
        qkd_kv_cfg_age_en e_vp11(.h(age_hi[1]),.l(age_lo[6]),.y(en_vp11));
        qkd_kv_cfg_age_field #(.W(16)) f_vp11(.ck(ck),.rn(age_rcp[7]),.en(en_vp11),.d(d_q[15:0]),.q(q_vp11));
        always @* ag_vp[176+:16]=q_vp11;
        wire en_vp12;wire[15:0]q_vp12;
        qkd_kv_cfg_age_en e_vp12(.h(age_hi[1]),.l(age_lo[7]),.y(en_vp12));
        qkd_kv_cfg_age_field #(.W(16)) f_vp12(.ck(ck),.rn(age_rcp[7]),.en(en_vp12),.d(d_q[15:0]),.q(q_vp12));
        always @* ag_vp[192+:16]=q_vp12;
        wire en_vp13;wire[15:0]q_vp13;
        qkd_kv_cfg_age_en e_vp13(.h(age_hi[2]),.l(age_lo[0]),.y(en_vp13));
        qkd_kv_cfg_age_field #(.W(16)) f_vp13(.ck(ck),.rn(age_rcp[8]),.en(en_vp13),.d(d_q[15:0]),.q(q_vp13));
        always @* ag_vp[208+:16]=q_vp13;
        wire en_vp14;wire[15:0]q_vp14;
        qkd_kv_cfg_age_en e_vp14(.h(age_hi[2]),.l(age_lo[1]),.y(en_vp14));
        qkd_kv_cfg_age_field #(.W(16)) f_vp14(.ck(ck),.rn(age_rcp[8]),.en(en_vp14),.d(d_q[15:0]),.q(q_vp14));
        always @* ag_vp[224+:16]=q_vp14;
        wire en_vp15;wire[15:0]q_vp15;
        qkd_kv_cfg_age_en e_vp15(.h(age_hi[2]),.l(age_lo[2]),.y(en_vp15));
        qkd_kv_cfg_age_field #(.W(16)) f_vp15(.ck(ck),.rn(age_rcp[9]),.en(en_vp15),.d(d_q[15:0]),.q(q_vp15));
        always @* ag_vp[240+:16]=q_vp15;
    end endgenerate
    assign fused_program_capability = cap_q && ((MUT == 5) || sealed);
    generate if(S32==0)begin:g_output_original
    wire ag_on=(MUT==7)||sealed;
    assign age_attn=ag_on?ag_attn:32'd0;assign age_pv=ag_on?ag_pv:16'd0;assign age_vport=ag_on?ag_vp:256'd0;
    end else begin:g_output_private
    wire[303:0] raw_age={ag_vp,ag_pv,ag_attn};wire[303:0] published;
    for(genvar k=0;k<304;k=k+1)begin:g_bit assign published[k]=((MUT==7)||g_s32.seal_pub[k/32])?raw_age[k]:1'b0;end
    assign {age_vport,age_pv,age_attn}=published;
    end endgenerate
endmodule
(* keep_hierarchy *) module qkd_kv_cfg_age_field #(parameter integer W=15)(input wire ck,rn,en,input wire[W-1:0]d,output reg[W-1:0]q);
 always @(posedge ck or negedge rn)if(!rn)q<={W{1'b0}};else if(en)q<=d;
endmodule
(* keep_hierarchy *) module qkd_kv_cfg_age_en(input wire h,l,output wire y);assign y=h&l;endmodule
