`timescale 1ns/1ps
// qwen-split/kvsys die lead r6 2026-10-15: equivalence bench of the HOST physical partition at the moved boundary.
// REF = the actual source qkd_host_ingest_chain_splitboot + 128 qkd_hbm_boot_static_completion wired exactly as
//       qkd_host_rank_services.g_boot (normal_ctrl_es/er between them; ck_boot/ck_boot_test/hbm_rst_n/boot_go).
// DUT = generated qkd_host_ingest_chain_pt + 128 die slices qkd_host_pc_slice (station + static arbiter + boot demux)
//       chained per stack exactly as the generated qkd_host_root_composed.
// Every boundary input is driven directly (resets released, boot_go pulsed, ing / land_es / ctrl_er / completions random
// every cycle), every boundary output compared every cycle.  +define+OT_PARTITION_MUT crosses PCs 0/1's landing words
// in the DUT and must FAIL.
module tb_host_chain_partition_equiv;
 reg ck=0; always #0.5 ck=~ck;
 reg rst_n=0, hbm_rst_n=0, boot_go=0, marker_cr=0;
 reg [289:0] ing; reg [36863:0] land_es; reg [33407:0] ctrl_er;
 reg [127:0] cmp_v, cmp_we;
 // ---------------- REF
 wire r_ing_cr, r_marker_v, r_map_fault, r_order_fault; wire [65:0] r_marker; wire [31:0] r_issued, r_landed;
 wire [3:0] r_chain_fault; wire [7:0] r_ack_n, r_pack_n; wire [127:0] r_acks, r_bdone, r_bok, r_bfault, nv, nwe;
 wire [33407:0] r_land_er, n_er; wire [36863:0] r_ctrl_es, n_es;
 qkd_host_ingest_chain_splitboot u_ref(.ck_map(ck),.ck_sum(ck),.ck_order(ck),.ck_station({128{ck}}),.ck_static({128{ck}}),.rst_n(rst_n),
  .ing(ing),.ing_cr(r_ing_cr),.all_acks(r_acks),.land_es(land_es),.land_er(r_land_er),.ctrl_es(n_es),.ctrl_er(n_er),
  .completion_v(nv),.completion_we(nwe),.marker_v(r_marker_v),.marker(r_marker),.marker_cr(marker_cr),.issued(r_issued),.landed(r_landed),
  .map_fault(r_map_fault),.chain_fault(r_chain_fault),.ack_n(r_ack_n),.physical_ack_n(r_pack_n),.order_fault(r_order_fault));
 for(genvar pc=0;pc<128;pc=pc+1)begin:g_boot
  qkd_hbm_boot_static_completion u_boot(.ck(ck),.ck_test(ck),.rst_n(hbm_rst_n),.boot_go(boot_go),
  .normal_es(n_es[pc*288+:288]),.normal_er(n_er[pc*261+:261]),
  .ctrl_es(r_ctrl_es[pc*288+:288]),.ctrl_er(ctrl_er[pc*261+:261]),
  .completion_v(cmp_v[pc]),.completion_we(cmp_we[pc]),
  .normal_completion_v(nv[pc]),.normal_completion_we(nwe[pc]),
  .boot_completion_v(),.boot_completion_we(),.boot_done(r_bdone[pc]),.boot_ok(r_bok[pc]),.boot_cause(),.fault(r_bfault[pc]));
 end
 // ---------------- DUT
 wire d_ing_cr, d_marker_v, d_map_fault, d_order_fault; wire [65:0] d_marker; wire [31:0] d_issued, d_landed;
 wire [3:0] d_chain_fault, chain_fault_i; wire [7:0] d_ack_n, d_pack_n; wire [127:0] d_acks, d_bdone, d_bok, d_bfault;
 wire [1163:0] chain_f; wire [127:0] chain_c, chain_a, slice_ack;
 wire [33407:0] d_land_er; wire [36863:0] d_ctrl_es;
 qkd_host_ingest_chain_pt u_dut(.ck_map(ck),.ck_sum(ck),.ck_order(ck),.rst_n(rst_n),.ing(ing),.ing_cr(d_ing_cr),
  .chain_f(chain_f),.chain_c(chain_c),.chain_a(chain_a),.chain_fault_i(chain_fault_i),.slice_ack(slice_ack),
  .all_acks(d_acks),.marker_v(d_marker_v),.marker(d_marker),.marker_cr(marker_cr),.issued(d_issued),.landed(d_landed),
  .map_fault(d_map_fault),.chain_fault(d_chain_fault),.ack_n(d_ack_n),.physical_ack_n(d_pack_n),.order_fault(d_order_fault));
 for(genvar st=0;st<4;st=st+1)begin:g_stack
  wire[290:0]f[0:32];wire[31:0]c[0:32],a[0:32];wire[32:0]fault;
  assign f[0]=chain_f[st*291+:291];assign c[32]=0;assign a[32]=0;assign fault[32]=0;
  assign chain_c[st*32+:32]=c[0];assign chain_a[st*32+:32]=a[0];assign chain_fault_i[st]=fault[0];
  for(genvar pc=0;pc<32;pc=pc+1)begin:g_pc
   localparam integer ID=st*32+pc;
   qkd_host_pc_slice u_slice(.ck_station(ck),.ck_static(ck),.ck_boot(ck),.ck_boot_test(ck),
    .host_rst_n(rst_n),.hbm_rst_n(hbm_rst_n),.boot_go(boot_go),.lpc(5'(pc)),
    .fi(f[pc]),.fo(f[pc+1]),.ci(c[pc+1]),.co(c[pc]),.ai(a[pc+1]),.ao(a[pc]),.fault_i(fault[pc+1]),.fault_o(fault[pc]),
`ifdef OT_PARTITION_MUT
    .land_es(land_es[(ID<2?ID^1:ID)*288+:288]),
`else
    .land_es(land_es[ID*288+:288]),
`endif
    .land_er(d_land_er[ID*261+:261]),.ctrl_es(d_ctrl_es[ID*288+:288]),.ctrl_er(ctrl_er[ID*261+:261]),
    .ctrl_completion_v(cmp_v[ID]),.ctrl_completion_we(cmp_we[ID]),
    .all_ack(slice_ack[ID]),.boot_done(d_bdone[ID]),.boot_ok(d_bok[ID]),.boot_fault(d_bfault[ID]));
  end
 end
 reg [16:0] sec; integer tcred=8;
 integer cyc, i, errs=0, firsterr=-1, a_ces=0, a_ler=0, a_ack=0, a_bd=0, a_ingcr=0, a_iss=0;
 task automatic drive;
  for(i=0;i<1152;i=i+1) land_es[i*32+:32]=$urandom;
  for(i=0;i<1044;i=i+1) ctrl_er[i*32+:32]=$urandom;
  // ingest words: legal local KV sector writes (map address rules), sent only on a held input credit (map ing_cr)
  for(i=0;i<9;i=i+1) ing[i*32+:32]=$urandom; ing[289:288]=$urandom;
  sec=$urandom; sec[7]=0; sec[16:11]=$urandom%36;
  ing[33:2]={1'b0,7'd0,sec,7'($urandom)}; ing[1]=1'b1; ing[0]=(tcred>0) && ($urandom%4!=0);
  if(ing[0]) tcred=tcred-1;
  for(i=0;i<4;i=i+1) begin cmp_v[i*32+:32]=$urandom; cmp_we[i*32+:32]=$urandom; end
  marker_cr=$urandom;
 endtask
 `define CMP(n) if(r_``n!==d_``n) begin errs=errs+1; if(firsterr<0) firsterr=cyc; if(errs<12) $display("MISMATCH cyc%0d n", cyc); end
 task automatic check;
  `CMP(ing_cr) `CMP(marker_v) `CMP(marker) `CMP(issued) `CMP(landed) `CMP(map_fault) `CMP(chain_fault)
  `CMP(ack_n) `CMP(pack_n) `CMP(order_fault) `CMP(acks) `CMP(bdone) `CMP(bok) `CMP(bfault) `CMP(land_er) `CMP(ctrl_es)
  if(|r_ctrl_es) a_ces=a_ces+1; if(|r_land_er) a_ler=a_ler+1; if(|r_acks) a_ack=a_ack+1; if(|r_bdone) a_bd=a_bd+1;
  if(r_ing_cr) a_ingcr=a_ingcr+1; if(r_issued!=0) a_iss=a_iss+1;
 endtask
 initial begin
  drive;
  for(cyc=0;cyc<`ifdef CYCLES `CYCLES `else 20000 `endif;cyc=cyc+1) begin
   if(cyc==8) rst_n=1; if(cyc==10) hbm_rst_n=1; boot_go=(cyc>=16 && cyc<18);
   @(negedge ck); check; if(r_ing_cr) tcred=tcred+1; drive;
  end
  $display("ACTIVITY ctrl_es=%0d land_er=%0d all_acks=%0d boot_done=%0d ing_cr=%0d issued_nonzero=%0d", a_ces, a_ler, a_ack, a_bd, a_ingcr, a_iss);
  if(errs) begin $display("FAIL host chain partition: %0d mismatching output samples, first cycle %0d", errs, firsterr); $fatal(1); end
  if(a_ces==0 || a_ler==0 || a_bd==0 || a_iss==0) begin $display("FAIL host chain partition bench: moved logic idle"); $fatal(1); end
  $display("PASS host chain partition equivalence: 128 PCs, %0d cycles, all boundary outputs identical every cycle (station->static host acks not reached: boot never qualifies on random controller returns; per-PC wiring proven formally by yosys equiv vs qkd_host_pc_slice_ref)", cyc);
  $finish;
 end
endmodule
