// Diagnostic clock-role class fixture only; NOT full capsule qualification.
module hhp_clock_mesh_role_fixture (
input wire ckm_w_ckm_n10_h1101010010,
input wire ckm_w_ckm_n10_h1101010011,
input wire ckm_w_ckm_n10_h1101010110,
input wire ckm_w_ckm_n10_h1101010111,
output wire ck_mesh);
BUFx24_ASAP7_75t_R kvpc0_mp_isl0_ck0 (.A(ckm_w_ckm_n10_h1101010111), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc0_mp_isl0_ck1 (.A(ckm_w_ckm_n10_h1101010111), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc0_mp_isl1_ck0 (.A(ckm_w_ckm_n10_h1101010110), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc0_mp_isl1_ck1 (.A(ckm_w_ckm_n10_h1101010110), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc1_mp_isl0_ck0 (.A(ckm_w_ckm_n10_h1101010111), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc1_mp_isl0_ck1 (.A(ckm_w_ckm_n10_h1101010111), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc1_mp_isl1_ck0 (.A(ckm_w_ckm_n10_h1101010110), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc1_mp_isl1_ck1 (.A(ckm_w_ckm_n10_h1101010110), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc2_mp_isl0_ck0 (.A(ckm_w_ckm_n10_h1101010011), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc2_mp_isl0_ck1 (.A(ckm_w_ckm_n10_h1101010011), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc2_mp_isl1_ck0 (.A(ckm_w_ckm_n10_h1101010010), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc2_mp_isl1_ck1 (.A(ckm_w_ckm_n10_h1101010010), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc3_mp_isl0_ck0 (.A(ckm_w_ckm_n10_h1101010011), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc3_mp_isl0_ck1 (.A(ckm_w_ckm_n10_h1101010011), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc3_mp_isl1_ck0 (.A(ckm_w_ckm_n10_h1101010010), .Y(ck_mesh));
BUFx24_ASAP7_75t_R kvpc3_mp_isl1_ck1 (.A(ckm_w_ckm_n10_h1101010010), .Y(ck_mesh));
endmodule
