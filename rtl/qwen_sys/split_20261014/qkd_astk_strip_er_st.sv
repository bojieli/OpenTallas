`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// RTL-BUILD-KV/ASTK 2026-10-18 (lanes/RTL-BUILD-KV.md P4; KVE-2-ASTK note for KVJ-D; stub_audit_1017 K-8):
// the static KV die's ASTK strip with its e-read inline, credit-free and lane-free.
//
//   qkd_astk_er_tap_st   = qkd_astk_er_tap (the 4-port e-read leaf on the SO/SI bus, ERL 3) + the e-read VISIBILITY
//                          check that qkd_astk_native_stack_w4_cal kept as wrapper glue: a read of group addr[6:3] before
//                          any EP has committed that group (OR over engines of si[552:537]) is a sticky fault.  The leaf
//                          therefore takes each owner's exp_done[15:0] (si[633 e + 537 +: 16]) besides its e_rdq
//                          (si[633 e + 569 +: 64]).  Same fault law as service + glue; KV-ERTAP 10-18: every pin registered (+4 edges; the
//                          EP's own three read stages + 2 + 2 pin edges = kv_static_die astk_eread erl 7).
//   qkd_astk_strip_er_st = wires-only: qkd_astk_strip_st (ctl_s + 8 ep_s + 32 ex_s + 4 zn + relays) + qkd_astk_er_tap_st.
//                          Engine so[12:0] is replaced by the tap's request field; so[412:13] and the whole si bus are
//                          parent nets (si also feeds the tap).  No nb (32 x 1,024 b), no ck_v, no pv_done, no si[633]
//                          (nb_cr), no so[423:412]: the engine side is qkd_ectl3_kiss_st (413-b so, 633-b si).
//
// so = 8 x {fault, so[411:0]} (413 b an engine), si = 8 x si[632:0] (633 b an engine).  response_data[64 j +: 64] is the
// e quad of read port j, 7 edges after its request (EP ERL 3 + 4 tap pin-register edges, KV-ERTAP 10-18): the die net to the PV pair's in_e (pvw_<p>.ie).
// Bench: rtl/test/qwen_kv_die/tb_qkd_astk_strip_er_st.sv (lockstep vs qkd_astk_native_stack_w4_cal = native_stack_cal +
// qkd_astk_native_er_service_w N 4 + visibility glue).  Mutants: `KVD_STMUT 4 = visibility check removed,
// 5 = response owner taken one tag stage early (the e quad of the wrong owner / edge).
// ---------------------------------------------------------------------------------------------------------------------
// leaf: qkd_astk_er_tap_st.sv

module qkd_astk_strip_er_st #(
    parameter integer RL = 1,
    parameter integer DISTRIBUTED_ER = 0,
    parameter integer Z_STRIDE = 4,
    parameter integer N = 4
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
    input  wire [413*8-1:0]  so,
    output wire [633*8-1:0]  si,
    input  wire [N-1:0]      read_v,
    input  wire [11*N-1:0]   read_addr,
    output wire [N-1:0]      response_v,
    output wire [11*N-1:0]   response_addr,
    output wire [64*N-1:0]   response_data,
    output wire              er_fault
);
    wire [13*8-1:0] aso; wire [7:0] eso_v; wire [64*8-1:0] esi; wire [16*8-1:0] com; wire [413*8-1:0] so_s;
    genvar e;
    generate for (e = 0; e < 8; e = e + 1) begin : g_e
        assign eso_v[e] = so[413*e];
        assign so_s[413*e +: 413] = {so[413*e+13 +: 400], aso[13*e +: 13]};
        assign esi[64*e +: 64] = si[633*e+569 +: 64];
        assign com[16*e +: 16] = si[633*e+537 +: 16];
    end endgenerate
    generate if (DISTRIBUTED_ER) begin : g_er_chain
        qkd_astk_er_chain_st #(.N(N), .RL(RL)) u_er (.ck(ck_er), .rst_n(rst_n), .read_v(read_v), .read_addr(read_addr),
            .eso_v(eso_v), .aso(aso), .esi(esi), .com(com), .response_v(response_v), .response_addr(response_addr),
            .response_data(response_data), .fault(er_fault));
    end else begin : g_er_star
    qkd_astk_er_tap_st #(.N(N), .ERL(3)) u_er (.ck(ck_er), .rst_n(rst_n), .read_v(read_v), .read_addr(read_addr),
        .eso_v_lo(eso_v[3:0]), .eso_v_hi(eso_v[7:4]), .aso_lo(aso[0 +: 52]), .aso_hi(aso[52 +: 52]),
        .esi_lo(esi[0 +: 256]), .esi_hi(esi[256 +: 256]), .com_lo(com[0 +: 64]), .com_hi(com[64 +: 64]),
        .response_v(response_v), .response_addr(response_addr), .response_data(response_data), .fault(er_fault));
    end endgenerate
    qkd_astk_strip_st #(.RL(RL), .Z_STRIDE(Z_STRIDE)) u_strip (.ck_c(ck_c), .ck_z(ck_z), .ck_x(ck_x), .ck_e(ck_e),
        .ck_r(ck_r), .rst_n(rst_n), .st(st), .aq(aq), .am(am), .cal(cal), .ap(ap), .af(af), .lt(lt), .so(so_s), .si(si));
endmodule
