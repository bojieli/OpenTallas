// Candidate physical pin capture proof. Reference slice is unchanged; only its declared boot input is delayed one edge.
`timescale 1ns/1ps
// qwen-split/kvsys die lead r7 2026-10-15: bench of the die-v1.4 slice wrapper qkd_host_pc_slice_die (one stack, 32 slots
// in PHYSICAL slot order, lpc = the landing strip's logical PC of each slot, kv_strips: lpc = 8 q + G(i)).
// REF = 32 bare qkd_host_pc_slice chained as qkd_host_root_composed, slot k started with boot_go delayed k cycles (the
//       wrapper's boot chain), its status bits collected directly.
// DUT = 32 qkd_host_pc_slice_die chained (f / c / a / fault as REF, status + boot chains through the wrapper).
// Checks every cycle: every per-slot output (ctrl_es, land_er) and the chain-head words (fo / co / ao / fault) identical;
// head status vector sk/sd/so/sf[lpc_k] == REF slot k's all_ack/boot_done/boot_ok/boot_fault delayed k + 1 cycles.
// +define+OT_SLICE_DIE_MUT builds the DUT with MUT=1 (status bit at lpc ^ 1) and must FAIL.
module tb_host_pc_slice_die_pin_capture;
 localparam integer N=32, D=40;
 reg ck=0; always #0.5 ck=~ck;
 reg rst_n=0, hbm_rst_n=0, boot_go=0;
 reg [290:0] f0; reg [N*288-1:0] land_es; reg [N*261-1:0] ctrl_er; reg [N-1:0] cmp_v, cmp_we;
 function automatic [4:0] lpc_of(input integer k); lpc_of = 8*(k%4) + (k/4==0?4:k/4==1?5:k/4==2?0:k/4==3?1:k/4==4?2:k/4==5?3:k/4==6?6:7); endfunction
 // boot_go delay line: bgd[j] = boot_go j cycles ago
 reg [D-1:0] bgd=0; always @(posedge ck) bgd <= {bgd[D-2:0], boot_go};
 // ---------------- REF
 wire [(N+1)*291-1:0] rf; wire [(N+1)*32-1:0] rc, ra; wire [N:0] rfl;
 assign rf[0+:291]=f0; assign rc[N*32+:32]=0; assign ra[N*32+:32]=0; assign rfl[N]=0;
 wire [N*261-1:0] r_land_er; wire [N*288-1:0] r_ctrl_es; wire [N-1:0] r_ack, r_bd, r_bo, r_bf;
 // ---------------- DUT
 wire [(N+1)*291-1:0] df; wire [(N+1)*32-1:0] dc, da; wire [N:0] dfl, dbg;
 wire [(N+1)*32-1:0] sk, sd, so, sf;
 assign df[0+:291]=f0; assign dc[N*32+:32]=0; assign da[N*32+:32]=0; assign dfl[N]=0; assign dbg[0]=boot_go;
 assign sk[N*32+:32]=0; assign sd[N*32+:32]=0; assign so[N*32+:32]=0; assign sf[N*32+:32]=0;
 wire [N*261-1:0] d_land_er; wire [N*288-1:0] d_ctrl_es;
 genvar k;
 for(k=0;k<N;k=k+1)begin:g
  wire bg_k = bgd[k]; // accepted uniform +1 boot-start edge; bgo chain unchanged
  qkd_host_pc_slice u_ref(.ck_station(ck),.ck_static(ck),.ck_boot(ck),.ck_boot_test(ck),.host_rst_n(rst_n),.hbm_rst_n(hbm_rst_n),
   .boot_go(bg_k),.lpc(lpc_of(k)),.fi(rf[k*291+:291]),.fo(rf[(k+1)*291+:291]),.ci(rc[(k+1)*32+:32]),.co(rc[k*32+:32]),.ai(ra[(k+1)*32+:32]),.ao(ra[k*32+:32]),.fault_i(rfl[k+1]),.fault_o(rfl[k]),
   .land_es(land_es[k*288+:288]),.land_er(r_land_er[k*261+:261]),.ctrl_es(r_ctrl_es[k*288+:288]),.ctrl_er(ctrl_er[k*261+:261]),
   .ctrl_completion_v(cmp_v[k]),.ctrl_completion_we(cmp_we[k]),.all_ack(r_ack[k]),.boot_done(r_bd[k]),.boot_ok(r_bo[k]),.boot_fault(r_bf[k]));
  qkd_host_pc_slice_die #(.MUT(`ifdef OT_SLICE_BOOT_MUT 2 `elsif OT_SLICE_DIE_MUT 1 `else 0 `endif)) u_dut(.ck_station(ck),.ck_static(ck),.ck_boot(ck),.ck_boot_test(ck),
   .host_rst_n(rst_n),.hbm_rst_n(hbm_rst_n),.lpc(lpc_of(k)),.bgi(dbg[k]),.bgo(dbg[k+1]),
   .fi(df[k*291+:291]),.fo(df[(k+1)*291+:291]),.ci(dc[(k+1)*32+:32]),.co(dc[k*32+:32]),.ai(da[(k+1)*32+:32]),.ao(da[k*32+:32]),.fault_i(dfl[k+1]),.fault_o(dfl[k]),
   .land_es(land_es[k*288+:288]),.land_er(d_land_er[k*261+:261]),.ctrl_es(d_ctrl_es[k*288+:288]),.ctrl_er(ctrl_er[k*261+:261]),
   .ctrl_completion_v(cmp_v[k]),.ctrl_completion_we(cmp_we[k]),
   .ski(sk[(k+1)*32+:32]),.sdi(sd[(k+1)*32+:32]),.soi(so[(k+1)*32+:32]),.sfi(sf[(k+1)*32+:32]),.sko(sk[k*32+:32]),.sdo(sd[k*32+:32]),.soo(so[k*32+:32]),.sfo(sf[k*32+:32]));
  always @(negedge ck) if(rst_n && hbm_rst_n && cyc>2)
   if(u_dut.u_slice.boot_go !== bgd[k]) err("boot capture age");
 end
 // expected head status: slot k's REF bit delayed k + 1 cycles, at bit lpc_of(k)
 reg [N-1:0] hk[0:D], hd[0:D], ho[0:D], hf[0:D];
 integer j;
 always @(posedge ck) begin
  for(j=D;j>0;j=j-1) begin hk[j]<=hk[j-1]; hd[j]<=hd[j-1]; ho[j]<=ho[j-1]; hf[j]<=hf[j-1]; end
  hk[0]<=r_ack; hd[0]<=r_bd; ho[0]<=r_bo; hf[0]<=r_bf;
 end
 function automatic [31:0] expect_head(input integer which);
  integer k; reg [31:0] v; v=0;
  for(k=0;k<N;k=k+1) case(which)
   0: v[lpc_of(k)] = hk[k][k]; 1: v[lpc_of(k)] = hd[k][k]; 2: v[lpc_of(k)] = ho[k][k]; default: v[lpc_of(k)] = hf[k][k];
  endcase
  expect_head=v;
 endfunction
 integer cyc, i, errs=0, firsterr=-1, a_bd=0, a_ces=0, a_hd=0;
 task automatic err(input [8*24-1:0] what);
  begin errs=errs+1; if(firsterr<0) firsterr=cyc; if(errs<10) $display("MISMATCH cyc%0d %0s", cyc, what); end
 endtask
 initial begin
  for(j=0;j<=D;j=j+1) begin hk[j]=0; hd[j]=0; ho[j]=0; hf[j]=0; end
  for(cyc=0;cyc<`ifdef CYCLES `CYCLES `else 6000 `endif;cyc=cyc+1) begin
   if(cyc==8) rst_n=1; if(cyc==10) hbm_rst_n=1; boot_go=(cyc>=16);
   for(i=0;i<N*9;i=i+1) land_es[i*32+:32]=$urandom;
   for(i=0;i<N*261/32+1;i=i+1) ctrl_er[i*32+:32]=$urandom;
   for(i=0;i<10;i=i+1) f0[i*32+:32]=$urandom;
   cmp_v=$urandom; cmp_we=$urandom;
   @(negedge ck);
   if(cyc>D+20) begin
    if(r_ctrl_es!==d_ctrl_es) err("ctrl_es"); if(r_land_er!==d_land_er) err("land_er");
    if(rf[N*291+:291]!==df[N*291+:291]) err("fo tail"); if(rc[0+:32]!==dc[0+:32]) err("co head"); if(ra[0+:32]!==da[0+:32]) err("ao head"); if(rfl[0]!==dfl[0]) err("fault head");
    if(sk[0+:32]!==expect_head(0)) err("status ack"); if(sd[0+:32]!==expect_head(1)) err("status boot_done");
    if(so[0+:32]!==expect_head(2)) err("status boot_ok"); if(sf[0+:32]!==expect_head(3)) err("status boot_fault");
    if(|r_bd) a_bd=a_bd+1; if(|r_ctrl_es) a_ces=a_ces+1; if(|sd[0+:32]) a_hd=a_hd+1;
   end
  end
  $display("ACTIVITY boot_done=%0d ctrl_es=%0d head_boot_done=%0d", a_bd, a_ces, a_hd);
  if(errs) begin $display("FAIL slice die wrapper: %0d mismatches, first cycle %0d", errs, firsterr); $fatal(1); end
  if(a_bd==0 || a_ces==0 || a_hd==0) begin $display("FAIL slice die wrapper bench: idle"); $fatal(1); end
  $display("PASS slice die wrapper: 32 slots physical order, %0d cycles, per-slot outputs identical, head status = REF delayed k+1", cyc);
  $finish;
 end
endmodule
