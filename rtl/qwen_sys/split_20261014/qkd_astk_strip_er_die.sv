`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// KV-WIRE2 2026-10-18 (RTL-BUILD-KV ASTK (a)/(b), lanes/RTL-BUILD-KV.md): the static KV die's ASTK strip DIE FACE.  Wires
// only around qkd_astk_strip_er_st (the static strip with the inline e-read + visibility check) except ONE OR gate:
//   so<e> / si<e>  the per-engine faces of the ECTL frames (qkd_ectl3_kiss_st so 413 b / si 633 b), engine e = bus slice e
//   vh<k>          the V-return header of the stack's V port k (qkd_pvfork vh = {epoch 16, t 14, valid}, a relayed fork
//                  branch of the die word pvh_<st>_<k>): e-read request read_v[k] = vh<k>[0], read_addr[11 k +: 11] =
//                  {t[12:9], t[6:0]} = {vh<k>[13:10], vh<k>[7:1]} (the e quad of the V row the pair is about to take)
//   erd            response_data (4 x 64 b, port k = the e quad of V port k, 7 edges after its request: ERL 3 + 4 tap pin regs) -> the PV pair's
//                  in_e lanes of this stack (pvw_<p>.ie / .iee); response_v / response_addr stay inside (no die e-read
//                  identity check: the tap's own owner / visibility checks fault instead)
//   af             the stack fault lane (sequencer af_<st> + attention fault root ufs_<st>) = strip af | er_fault: the
//                  e-read service fault joins its stack's unit-fault lane (RTL-BUILD-KV/FAULT "not covered": e-read
//                  identity -> OR into the stack lane), same edge as af (both are flop outputs; no extra stage)
//   cal            {EXP base, Z start, LMAX start} of the accepted command (kvs_attn attention root, held)
// Bench: the strip is rtl/test/qwen_kv_die/tb_qkd_astk_strip_er_st.sv (tools/qwen_kv_die/astk_er_static_bench.sh).
// ---------------------------------------------------------------------------------------------------------------------
module qkd_astk_strip_er_die #(
    parameter integer RL = 1,
    parameter integer DISTRIBUTED_ER = 0,
    parameter integer Z_STRIDE = 4
) (
    input  wire              ck_c,
    input  wire [3:0]        ck_z,
    input  wire [31:0]       ck_x,
    input  wire [7:0]        ck_e,
    input  wire              ck_r,
    input  wire              ck_er,
    input  wire              rst_n,
    input  wire [1:0]        st,
    input  wire [539:0]      aq,
    input  wire [35:0]       am,
    input  wire [47:0]       cal,
    output wire [42:0]       ap,
    output wire              af,
    output wire [20:0]       lt,
    input  wire [412:0]      so0,
    input  wire [412:0]      so1,
    input  wire [412:0]      so2,
    input  wire [412:0]      so3,
    input  wire [412:0]      so4,
    input  wire [412:0]      so5,
    input  wire [412:0]      so6,
    input  wire [412:0]      so7,
    output wire [632:0]      si0,
    output wire [632:0]      si1,
    output wire [632:0]      si2,
    output wire [632:0]      si3,
    output wire [632:0]      si4,
    output wire [632:0]      si5,
    output wire [632:0]      si6,
    output wire [632:0]      si7,
    input  wire [30:0]       vh0,
    input  wire [30:0]       vh1,
    input  wire [30:0]       vh2,
    input  wire [30:0]       vh3,
    output wire [255:0]      erd
);
    wire [413*8-1:0] so = {so7, so6, so5, so4, so3, so2, so1, so0};
    wire [633*8-1:0] si;
    assign si0 = si[633*0 +: 633];
    assign si1 = si[633*1 +: 633];
    assign si2 = si[633*2 +: 633];
    assign si3 = si[633*3 +: 633];
    assign si4 = si[633*4 +: 633];
    assign si5 = si[633*5 +: 633];
    assign si6 = si[633*6 +: 633];
    assign si7 = si[633*7 +: 633];
    wire [3:0]  read_v = {vh3[0], vh2[0], vh1[0], vh0[0]};
    wire [43:0] read_addr = {vh3[13:10], vh3[7:1], vh2[13:10], vh2[7:1], vh1[13:10], vh1[7:1], vh0[13:10], vh0[7:1]};
    wire [3:0]  response_v;
    wire [43:0] response_addr;
    wire        af_s, er_fault;
    generate if (DISTRIBUTED_ER) begin : g_phys_fault
        qkd_astk_fault_join u_fault (.ck(ck_er), .rst_n(rst_n), .a(af_s), .b(er_fault), .q(af));
    end else begin : g_legacy_fault
        assign af = af_s | er_fault;
    end endgenerate
    qkd_astk_strip_er_st #(.RL(RL), .Z_STRIDE(Z_STRIDE), .N(4), .DISTRIBUTED_ER(DISTRIBUTED_ER)) u_strip (.ck_c(ck_c), .ck_z(ck_z), .ck_x(ck_x), .ck_e(ck_e),
        .ck_r(ck_r), .ck_er(ck_er), .rst_n(rst_n), .st(st), .aq(aq), .am(am), .cal(cal), .ap(ap), .af(af_s), .lt(lt),
        .so(so), .si(si), .read_v(read_v), .read_addr(read_addr), .response_v(response_v), .response_addr(response_addr),
        .response_data(erd), .er_fault(er_fault));
endmodule
