`timescale 1ns/1ps
// KV-CTL10 10-20 (generated from the boot-ages qkd_kvs_ctl port list): whole-tile lockstep of the REFERENCE ctl
// (qkd_kvs_ctl_ref = qkd_kvs_tiles_hroot_ff_k_mu_ba.sv qkd_kvs_ctl with u_own PIPE 1 / SAFE 1 and u_boot SRQ 2, the
// declared schedule deltas, from the KV-CTL3 reference copies) vs the c32 tile (native-census members), every output
// on every edge after the first reset release.  +define FIRST: run with --x-initial unique + rand reset (first use).
// PASS KV_CTL_C32_TILE ... / FAIL ... mismatches<n>
module tb_kv_ctl_c32_tile;
 parameter integer CYC=200000;
 reg ck=0;always #5 ck=~ck;
 integer seed=3,cyc=0,mism=0,live=0,act=0;
 reg [142:0] boot__boot_pr=0;
 reg [3:0] boot__boot_image_target=0;
 reg [0:0] boot__boot_image_ready=0;
 reg [0:0] boot__boot_image_fault=0;
 reg [15:0] boot__boot_image_epoch=0;
 reg [63:0] boot__boot_image_digest=0;
 reg [173:0] d2d__svc=0;
 reg [0:0] por_n=0;
 reg rst_n=0;
 reg [292:0] embgw__bw=0;
 reg [0:0] st=0;
 reg [81:0] auth=0;
 reg [58:0] cht=0;
 reg [1:0] chg=0;
 reg [11:0] d2d__skw=0;
 reg [0:0] oobs__host_launch_quiet=0;
 reg [5:0] oobs__host_upstream_quiet=0;
 reg [521:0] d2d__srx=0;
 reg [58:0] d2d__kvn_word_identity=0;
 reg [1:0] d2d__kvn_word_generation=0;
 reg [143:0] i_hroot_WS=0;
 reg [143:0] i_hroot_WN=0;
 reg [143:0] i_hroot_ES=0;
 reg [143:0] i_hroot_EN=0;
 wire [0:0] a_boot__link_cfg_tx_we,b_boot__link_cfg_tx_we;
 wire [0:0] a_boot__link_cfg_rx_we,b_boot__link_cfg_rx_we;
 wire [5:0] a_boot__link_cfg_addr,b_boot__link_cfg_addr;
 wire [31:0] a_boot__link_cfg_data,b_boot__link_cfg_data;
 wire [60:0] a_kvi,b_kvi;
 wire [0:0] a_oobs__kv_drained_local,b_oobs__kv_drained_local;
 wire [0:0] a_oobs__kv_flush_local,b_oobs__kv_flush_local;
 wire [0:0] a_oobs__kv_active_local,b_oobs__kv_active_local;
 wire [15:0] a_dcfg__age_vport__0_16,b_dcfg__age_vport__0_16;
 wire [15:0] a_dcfg__age_vport__16_16,b_dcfg__age_vport__16_16;
 wire [15:0] a_dcfg__age_vport__32_16,b_dcfg__age_vport__32_16;
 wire [15:0] a_dcfg__age_vport__48_16,b_dcfg__age_vport__48_16;
 wire [22:0] a_kg,b_kg;
 wire [15:0] a_dcfg__age_vport__64_16,b_dcfg__age_vport__64_16;
 wire [15:0] a_dcfg__age_vport__80_16,b_dcfg__age_vport__80_16;
 wire [15:0] a_dcfg__age_vport__96_16,b_dcfg__age_vport__96_16;
 wire [15:0] a_dcfg__age_vport__112_16,b_dcfg__age_vport__112_16;
 wire [15:0] a_dcfg__age_vport__128_16,b_dcfg__age_vport__128_16;
 wire [15:0] a_dcfg__age_vport__144_16,b_dcfg__age_vport__144_16;
 wire [15:0] a_dcfg__age_vport__160_16,b_dcfg__age_vport__160_16;
 wire [15:0] a_dcfg__age_vport__176_16,b_dcfg__age_vport__176_16;
 wire [15:0] a_dcfg__age_vport__192_16,b_dcfg__age_vport__192_16;
 wire [15:0] a_dcfg__age_vport__208_16,b_dcfg__age_vport__208_16;
 wire [15:0] a_dcfg__age_vport__224_16,b_dcfg__age_vport__224_16;
 wire [15:0] a_dcfg__age_vport__240_16,b_dcfg__age_vport__240_16;
 wire [20:0] a_lp,b_lp;
 wire [0:0] a_boot__setup_ready,b_boot__setup_ready;
 wire [0:0] a_own__native_reserved,b_own__native_reserved;
 wire [0:0] a_own__ownership_valid,b_own__ownership_valid;
 wire [0:0] a_cf_root__fault,b_cf_root__fault;
 wire [15:0] a_dcfg__age_pv,b_dcfg__age_pv;
 wire [108:0] a_o_attn,b_o_attn;
 wire [72:0] a_o_emb,b_o_emb;
 wire [1117:0] a_o_hroot_WS,b_o_hroot_WS;
 wire [1117:0] a_o_hroot_WN,b_o_hroot_WN;
 wire [1117:0] a_o_hroot_ES,b_o_hroot_ES;
 wire [1117:0] a_o_hroot_EN,b_o_hroot_EN;
 qkd_kvs_ctl_ref ref0(.ck(ck), .rst_n(rst_n), .boot__boot_pr(boot__boot_pr), .boot__boot_image_target(boot__boot_image_target), .boot__boot_image_ready(boot__boot_image_ready), .boot__boot_image_fault(boot__boot_image_fault), .boot__boot_image_epoch(boot__boot_image_epoch), .boot__boot_image_digest(boot__boot_image_digest), .d2d__svc(d2d__svc), .por_n(por_n), .embgw__bw(embgw__bw), .st(st), .auth(auth), .cht(cht), .chg(chg), .d2d__skw(d2d__skw), .oobs__host_launch_quiet(oobs__host_launch_quiet), .oobs__host_upstream_quiet(oobs__host_upstream_quiet), .d2d__srx(d2d__srx), .d2d__kvn_word_identity(d2d__kvn_word_identity), .d2d__kvn_word_generation(d2d__kvn_word_generation), .i_hroot_WS(i_hroot_WS), .i_hroot_WN(i_hroot_WN), .i_hroot_ES(i_hroot_ES), .i_hroot_EN(i_hroot_EN), .boot__link_cfg_tx_we(a_boot__link_cfg_tx_we), .boot__link_cfg_rx_we(a_boot__link_cfg_rx_we), .boot__link_cfg_addr(a_boot__link_cfg_addr), .boot__link_cfg_data(a_boot__link_cfg_data), .kvi(a_kvi), .oobs__kv_drained_local(a_oobs__kv_drained_local), .oobs__kv_flush_local(a_oobs__kv_flush_local), .oobs__kv_active_local(a_oobs__kv_active_local), .dcfg__age_vport__0_16(a_dcfg__age_vport__0_16), .dcfg__age_vport__16_16(a_dcfg__age_vport__16_16), .dcfg__age_vport__32_16(a_dcfg__age_vport__32_16), .dcfg__age_vport__48_16(a_dcfg__age_vport__48_16), .kg(a_kg), .dcfg__age_vport__64_16(a_dcfg__age_vport__64_16), .dcfg__age_vport__80_16(a_dcfg__age_vport__80_16), .dcfg__age_vport__96_16(a_dcfg__age_vport__96_16), .dcfg__age_vport__112_16(a_dcfg__age_vport__112_16), .dcfg__age_vport__128_16(a_dcfg__age_vport__128_16), .dcfg__age_vport__144_16(a_dcfg__age_vport__144_16), .dcfg__age_vport__160_16(a_dcfg__age_vport__160_16), .dcfg__age_vport__176_16(a_dcfg__age_vport__176_16), .dcfg__age_vport__192_16(a_dcfg__age_vport__192_16), .dcfg__age_vport__208_16(a_dcfg__age_vport__208_16), .dcfg__age_vport__224_16(a_dcfg__age_vport__224_16), .dcfg__age_vport__240_16(a_dcfg__age_vport__240_16), .lp(a_lp), .boot__setup_ready(a_boot__setup_ready), .own__native_reserved(a_own__native_reserved), .own__ownership_valid(a_own__ownership_valid), .cf_root__fault(a_cf_root__fault), .dcfg__age_pv(a_dcfg__age_pv), .o_attn(a_o_attn), .o_emb(a_o_emb), .o_hroot_WS(a_o_hroot_WS), .o_hroot_WN(a_o_hroot_WN), .o_hroot_ES(a_o_hroot_ES), .o_hroot_EN(a_o_hroot_EN));
 qkd_kvs_ctl dut(.ck(ck), .rst_n(rst_n), .boot__boot_pr(boot__boot_pr), .boot__boot_image_target(boot__boot_image_target), .boot__boot_image_ready(boot__boot_image_ready), .boot__boot_image_fault(boot__boot_image_fault), .boot__boot_image_epoch(boot__boot_image_epoch), .boot__boot_image_digest(boot__boot_image_digest), .d2d__svc(d2d__svc), .por_n(por_n), .embgw__bw(embgw__bw), .st(st), .auth(auth), .cht(cht), .chg(chg), .d2d__skw(d2d__skw), .oobs__host_launch_quiet(oobs__host_launch_quiet), .oobs__host_upstream_quiet(oobs__host_upstream_quiet), .d2d__srx(d2d__srx), .d2d__kvn_word_identity(d2d__kvn_word_identity), .d2d__kvn_word_generation(d2d__kvn_word_generation), .i_hroot_WS(i_hroot_WS), .i_hroot_WN(i_hroot_WN), .i_hroot_ES(i_hroot_ES), .i_hroot_EN(i_hroot_EN), .boot__link_cfg_tx_we(b_boot__link_cfg_tx_we), .boot__link_cfg_rx_we(b_boot__link_cfg_rx_we), .boot__link_cfg_addr(b_boot__link_cfg_addr), .boot__link_cfg_data(b_boot__link_cfg_data), .kvi(b_kvi), .oobs__kv_drained_local(b_oobs__kv_drained_local), .oobs__kv_flush_local(b_oobs__kv_flush_local), .oobs__kv_active_local(b_oobs__kv_active_local), .dcfg__age_vport__0_16(b_dcfg__age_vport__0_16), .dcfg__age_vport__16_16(b_dcfg__age_vport__16_16), .dcfg__age_vport__32_16(b_dcfg__age_vport__32_16), .dcfg__age_vport__48_16(b_dcfg__age_vport__48_16), .kg(b_kg), .dcfg__age_vport__64_16(b_dcfg__age_vport__64_16), .dcfg__age_vport__80_16(b_dcfg__age_vport__80_16), .dcfg__age_vport__96_16(b_dcfg__age_vport__96_16), .dcfg__age_vport__112_16(b_dcfg__age_vport__112_16), .dcfg__age_vport__128_16(b_dcfg__age_vport__128_16), .dcfg__age_vport__144_16(b_dcfg__age_vport__144_16), .dcfg__age_vport__160_16(b_dcfg__age_vport__160_16), .dcfg__age_vport__176_16(b_dcfg__age_vport__176_16), .dcfg__age_vport__192_16(b_dcfg__age_vport__192_16), .dcfg__age_vport__208_16(b_dcfg__age_vport__208_16), .dcfg__age_vport__224_16(b_dcfg__age_vport__224_16), .dcfg__age_vport__240_16(b_dcfg__age_vport__240_16), .lp(b_lp), .boot__setup_ready(b_boot__setup_ready), .own__native_reserved(b_own__native_reserved), .own__ownership_valid(b_own__ownership_valid), .cf_root__fault(b_cf_root__fault), .dcfg__age_pv(b_dcfg__age_pv), .o_attn(b_o_attn), .o_emb(b_o_emb), .o_hroot_WS(b_o_hroot_WS), .o_hroot_WN(b_o_hroot_WN), .o_hroot_ES(b_o_hroot_ES), .o_hroot_EN(b_o_hroot_EN));
 wire [5077:0] va={a_boot__link_cfg_tx_we,a_boot__link_cfg_rx_we,a_boot__link_cfg_addr,a_boot__link_cfg_data,a_kvi,a_oobs__kv_drained_local,a_oobs__kv_flush_local,a_oobs__kv_active_local,a_dcfg__age_vport__0_16,a_dcfg__age_vport__16_16,a_dcfg__age_vport__32_16,a_dcfg__age_vport__48_16,a_kg,a_dcfg__age_vport__64_16,a_dcfg__age_vport__80_16,a_dcfg__age_vport__96_16,a_dcfg__age_vport__112_16,a_dcfg__age_vport__128_16,a_dcfg__age_vport__144_16,a_dcfg__age_vport__160_16,a_dcfg__age_vport__176_16,a_dcfg__age_vport__192_16,a_dcfg__age_vport__208_16,a_dcfg__age_vport__224_16,a_dcfg__age_vport__240_16,a_lp,a_boot__setup_ready,a_own__native_reserved,a_own__ownership_valid,a_cf_root__fault,a_dcfg__age_pv,a_o_attn,a_o_emb,a_o_hroot_WS,a_o_hroot_WN,a_o_hroot_ES,a_o_hroot_EN};
 wire [5077:0] vb={b_boot__link_cfg_tx_we,b_boot__link_cfg_rx_we,b_boot__link_cfg_addr,b_boot__link_cfg_data,b_kvi,b_oobs__kv_drained_local,b_oobs__kv_flush_local,b_oobs__kv_active_local,b_dcfg__age_vport__0_16,b_dcfg__age_vport__16_16,b_dcfg__age_vport__32_16,b_dcfg__age_vport__48_16,b_kg,b_dcfg__age_vport__64_16,b_dcfg__age_vport__80_16,b_dcfg__age_vport__96_16,b_dcfg__age_vport__112_16,b_dcfg__age_vport__128_16,b_dcfg__age_vport__144_16,b_dcfg__age_vport__160_16,b_dcfg__age_vport__176_16,b_dcfg__age_vport__192_16,b_dcfg__age_vport__208_16,b_dcfg__age_vport__224_16,b_dcfg__age_vport__240_16,b_lp,b_boot__setup_ready,b_own__native_reserved,b_own__ownership_valid,b_cf_root__fault,b_dcfg__age_pv,b_o_attn,b_o_emb,b_o_hroot_WS,b_o_hroot_WN,b_o_hroot_ES,b_o_hroot_EN};
 function automatic [31:0] r32();r32=$unsigned($random(seed));endfunction
 task automatic rnd(input integer dens);begin
  boot__boot_pr=($unsigned($random(seed))%100<dens)?{r32(),r32(),r32(),r32(),r32()}:boot__boot_pr;
  boot__boot_pr[0]=($unsigned($random(seed))%100<dens);
  boot__boot_image_target=($unsigned($random(seed))%100<dens)?4'(r32()):4'(0);
  boot__boot_image_ready=($unsigned($random(seed))%100<dens)?1'(r32()):1'(0);
  boot__boot_image_fault=($unsigned($random(seed))%100<dens)?1'(r32()):1'(0);
  boot__boot_image_epoch=($unsigned($random(seed))%100<dens)?16'(r32()):16'(0);
  boot__boot_image_digest=($unsigned($random(seed))%100<dens)?{r32(),r32()}:boot__boot_image_digest;
  boot__boot_image_digest[0]=($unsigned($random(seed))%100<dens);
  d2d__svc=($unsigned($random(seed))%100<dens)?{r32(),r32(),r32(),r32(),r32(),r32()}:d2d__svc;
  d2d__svc[0]=($unsigned($random(seed))%100<dens);
  embgw__bw=($unsigned($random(seed))%100<dens)?{r32(),r32(),r32(),r32(),r32(),r32(),r32(),r32(),r32(),r32()}:embgw__bw;
  embgw__bw[0]=($unsigned($random(seed))%100<dens);
  st=($unsigned($random(seed))%100<dens)?1'(r32()):1'(0);
  auth=($unsigned($random(seed))%100<dens)?{r32(),r32(),r32()}:auth;
  auth[0]=($unsigned($random(seed))%100<dens);
  cht=($unsigned($random(seed))%100<dens)?{r32(),r32()}:cht;
  cht[0]=($unsigned($random(seed))%100<dens);
  chg=($unsigned($random(seed))%100<dens)?2'(r32()):2'(0);
  d2d__skw=($unsigned($random(seed))%100<dens)?12'(r32()):12'(0);
  oobs__host_launch_quiet=($unsigned($random(seed))%100<dens)?1'(r32()):1'(0);
  oobs__host_upstream_quiet=($unsigned($random(seed))%100<dens)?6'(r32()):6'(0);
  d2d__srx=($unsigned($random(seed))%100<dens)?{r32(),r32(),r32(),r32(),r32(),r32(),r32(),r32(),r32(),r32(),r32(),r32(),r32(),r32(),r32(),r32(),r32()}:d2d__srx;
  d2d__srx[0]=($unsigned($random(seed))%100<dens);
  d2d__kvn_word_identity=($unsigned($random(seed))%100<dens)?{r32(),r32()}:d2d__kvn_word_identity;
  d2d__kvn_word_identity[0]=($unsigned($random(seed))%100<dens);
  d2d__kvn_word_generation=($unsigned($random(seed))%100<dens)?2'(r32()):2'(0);
  i_hroot_WS=($unsigned($random(seed))%100<dens)?{r32(),r32(),r32(),r32(),r32()}:i_hroot_WS;
  i_hroot_WS[0]=($unsigned($random(seed))%100<dens);
  i_hroot_WN=($unsigned($random(seed))%100<dens)?{r32(),r32(),r32(),r32(),r32()}:i_hroot_WN;
  i_hroot_WN[0]=($unsigned($random(seed))%100<dens);
  i_hroot_ES=($unsigned($random(seed))%100<dens)?{r32(),r32(),r32(),r32(),r32()}:i_hroot_ES;
  i_hroot_ES[0]=($unsigned($random(seed))%100<dens);
  i_hroot_EN=($unsigned($random(seed))%100<dens)?{r32(),r32(),r32(),r32(),r32()}:i_hroot_EN;
  i_hroot_EN[0]=($unsigned($random(seed))%100<dens);
 end endtask
 integer ph=0,armed=0;
 always @(posedge ck)begin
  #1;cyc=cyc+1;
  if(armed)begin if(va!==vb)begin mism=mism+1;if(mism<=8)$display("MISMATCH cyc %0d first diff bit %0d",cyc,$clog2(((va^vb)&-(va^vb))+1)-1);end else live=live+1;end
  if(va!=0)act=act+1;
 end
 initial begin
  rst_n=0;por_n=0;
  repeat(12)@(negedge ck);por_n=1;repeat(4)@(negedge ck);rst_n=1;repeat(16)@(negedge ck);armed=1;
  while(cyc<CYC)begin
   @(negedge ck);ph=$unsigned($random(seed))%1000;
   rnd((ph<20)?60:3);
   if(ph==999)begin armed=0;rst_n=0;repeat(3)@(negedge ck);rst_n=1;repeat(16)@(negedge ck);armed=1;end
   if(ph==998&&($unsigned($random(seed))%8==0))begin armed=0;rst_n=0;por_n=0;repeat(3)@(negedge ck);por_n=1;repeat(4)@(negedge ck);rst_n=1;repeat(16)@(negedge ck);armed=1;end
  end
  if(mism==0)$display("PASS KV_CTL_C32_TILE mismatches0 cycles%0d compared%0d nonzero_output_cycles%0d outbits5078",cyc,live,act);
  else $display("FAIL KV_CTL_C32_TILE mismatches%0d cycles%0d",mism,cyc);
  $finish;
 end
endmodule
