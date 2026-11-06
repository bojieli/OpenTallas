`timescale 1ps/1ps
// HBM-B12-SVGRBK lock-step bench: B8 ot_svgr_bk (renamed ot_svgr_bk_ref, source 4ce474326fb) vs ot_svgr_bk VARIANT
// `VAR (0 = vA, 1 = vB) with mutant `MUTN.  Independent hbm/stream clocks, async resets, random traffic.
// Each design has its own producer (same packet sequence and same random gaps, 8 credits per landing bank, credits
// returned on cr).  Checks:
//   EXACT (`VAR==0): every output of both designs equal at every clock edge of either clock.
//   EVENTS (both): per landing bank the sequence of SRAM landing writes (slot,row,data), complete events (slot),
//     the fault flag and the credit count are equal at the end of each phase; read-back of every row equal.
//   vB invariant: at every take, id_q equals the identity check evaluated in that cycle.
module tb_svgr_bk_b12;
`ifndef VAR
 `define VAR 0
`endif
`ifndef MUTN
 `define MUTN 0
`endif
`ifndef SEED
 `define SEED 1
`endif
`ifndef PHASES
 `define PHASES 60
`endif
`ifndef HP
 `define HP 512
`endif
`ifndef SP
 `define SP 417
`endif
 localparam integer LB=2, IW=283+LB;
 reg hclk=0, sclk=0; always #(`HP) hclk=~hclk; always #(`SP) sclk=~sclk;
 reg rst_n=0; reg bk_hi=0;
 reg res_v=0; reg [1:0] res_bank=0; reg [15:0] res_epoch=0; reg [11:0] res_total=0; reg stop=0;
 reg [3:0] read_v=0; reg [1:0] read_bank=0; reg [23:0] read_row=0;
 // per design inputs
 reg [3:0] in_v[0:1]; reg [4*IW-1:0] in_d[0:1];
 wire [3:0] cr[0:1], cm[0:1], bf[0:1]; wire [7:0] cb[0:1]; wire [1023:0] rd[0:1];
 ot_svgr_bk_ref u_ref(.hbm_clk(hclk),.stream_clk(sclk),.stream_rst_n(rst_n),.hbm_rst_n(rst_n),.bk_hi(bk_hi),
  .in_v(in_v[0]),.in_data(in_d[0]),.cr(cr[0]),.res_v(res_v),.res_bank(res_bank),.res_epoch(res_epoch),.res_total(res_total),.stop(stop),
  .read_v(read_v),.read_bank(read_bank),.read_row(read_row),.complete(cm[0]),.complete_bank(cb[0]),.bfault(bf[0]),.read_data(rd[0]));
 ot_svgr_bk #(.VARIANT(`VAR),.MUT(`MUTN)) u_dut(.hbm_clk(hclk),.stream_clk(sclk),.stream_rst_n(rst_n),.hbm_rst_n(rst_n),.bk_hi(bk_hi),
  .in_v(in_v[1]),.in_data(in_d[1]),.cr(cr[1]),.res_v(res_v),.res_bank(res_bank),.res_epoch(res_epoch),.res_total(res_total),.stop(stop),
  .read_v(read_v),.read_bank(read_bank),.read_row(read_row),.complete(cm[1]),.complete_bank(cb[1]),.bfault(bf[1]),.read_data(rd[1]));

 integer nabort=0, errs=0, nexact=0, ntake=0, ncompl=0, nfault=0, nwr=0;
 task automatic err(input string m); begin errs=errs+1; if(errs<20) $display("MISMATCH t=%0t %s", $time, m); end endtask

 // ---------------- packet sequences (shared) ----------------
 localparam integer QMAX=4096;
 reg [IW-1:0] pq[0:3][0:QMAX-1]; integer pn[0:3]; integer gap[0:3][0:QMAX-1];
 integer pi[0:1][0:3]; integer credit[0:1][0:3]; integer gwait[0:1][0:3];
 integer d, g;
 // producers (hbm domain), one per design, identical gap sequence
 always @(posedge hclk) begin
  for (d=0; d<2; d=d+1) begin
   for (g=0; g<4; g=g+1) begin
    if (!rst_n) begin credit[d][g]=8; in_v[d][g]<=0; gwait[d][g]=-1; end
    else begin
     credit[d][g]=credit[d][g]+cr[d][g];
     in_v[d][g]<=0;
     if (pi[d][g] < pn[g]) begin
      if (gwait[d][g] < 0) gwait[d][g]=gap[g][pi[d][g]];
      if (gwait[d][g] > 0) gwait[d][g]=gwait[d][g]-1;
      else if (credit[d][g] > 0) begin
       in_v[d][g]<=1; in_d[d][IW*g+:IW]<=pq[g][pi[d][g]]; credit[d][g]=credit[d][g]-1; pi[d][g]=pi[d][g]+1; gwait[d][g]=-1;
      end
     end
    end
   end
  end
 end

 // ---------------- event logs (stream domain) ----------------
 localparam integer LMAX=8192;
 reg [255+8:0] wl[0:1][0:3][0:LMAX-1]; integer wn[0:1][0:3];
 reg [1:0] cl[0:1][0:3][0:LMAX-1]; integer cn[0:1][0:3];
 always @(posedge sclk) if (rst_n) begin
  if (u_ref.u[0].u_bank.landing_write) begin wl[0][0][wn[0][0]]={u_ref.u[0].u_bank.bank,u_ref.u[0].u_bank.row,u_ref.u[0].u_bank.packet[255:0]}; wn[0][0]=wn[0][0]+1; end
  if (u_ref.u[1].u_bank.landing_write) begin wl[0][1][wn[0][1]]={u_ref.u[1].u_bank.bank,u_ref.u[1].u_bank.row,u_ref.u[1].u_bank.packet[255:0]}; wn[0][1]=wn[0][1]+1; end
  if (u_ref.u[2].u_bank.landing_write) begin wl[0][2][wn[0][2]]={u_ref.u[2].u_bank.bank,u_ref.u[2].u_bank.row,u_ref.u[2].u_bank.packet[255:0]}; wn[0][2]=wn[0][2]+1; end
  if (u_ref.u[3].u_bank.landing_write) begin wl[0][3][wn[0][3]]={u_ref.u[3].u_bank.bank,u_ref.u[3].u_bank.row,u_ref.u[3].u_bank.packet[255:0]}; wn[0][3]=wn[0][3]+1; end
  if (u_dut.u[0].u_bank.landing_write) begin wl[1][0][wn[1][0]]={u_dut.u[0].u_bank.bank,u_dut.u[0].u_bank.row,u_dut.u[0].u_bank.packet[255:0]}; wn[1][0]=wn[1][0]+1; end
  if (u_dut.u[1].u_bank.landing_write) begin wl[1][1][wn[1][1]]={u_dut.u[1].u_bank.bank,u_dut.u[1].u_bank.row,u_dut.u[1].u_bank.packet[255:0]}; wn[1][1]=wn[1][1]+1; end
  if (u_dut.u[2].u_bank.landing_write) begin wl[1][2][wn[1][2]]={u_dut.u[2].u_bank.bank,u_dut.u[2].u_bank.row,u_dut.u[2].u_bank.packet[255:0]}; wn[1][2]=wn[1][2]+1; end
  if (u_dut.u[3].u_bank.landing_write) begin wl[1][3][wn[1][3]]={u_dut.u[3].u_bank.bank,u_dut.u[3].u_bank.row,u_dut.u[3].u_bank.packet[255:0]}; wn[1][3]=wn[1][3]+1; end
  for (g=0; g<4; g=g+1) begin
   if (cm[0][g]) begin cl[0][g][cn[0][g]]=cb[0][2*g+:2]; cn[0][g]=cn[0][g]+1; ncompl=ncompl+1; end
   if (cm[1][g]) begin cl[1][g][cn[1][g]]=cb[1][2*g+:2]; cn[1][g]=cn[1][g]+1; end
  end
 end
`ifdef VB_INV
 // vB invariant: id_q used at a take equals the identity evaluated in the take cycle
 always @(posedge sclk) if (rst_n) begin
  if (u_dut.u[0].u_bank.packet_take && u_dut.u[0].u_bank.identity_ok != u_dut.u[0].u_bank.identity_c) err("vB id_q stale u0");
  if (u_dut.u[1].u_bank.packet_take && u_dut.u[1].u_bank.identity_ok != u_dut.u[1].u_bank.identity_c) err("vB id_q stale u1");
  if (u_dut.u[2].u_bank.packet_take && u_dut.u[2].u_bank.identity_ok != u_dut.u[2].u_bank.identity_c) err("vB id_q stale u2");
  if (u_dut.u[3].u_bank.packet_take && u_dut.u[3].u_bank.identity_ok != u_dut.u[3].u_bank.identity_c) err("vB id_q stale u3");
 end
`endif
 `ifdef DBG
 always @(posedge sclk) if (rst_n && u_ref.u[0].u_bank.packet_take && !u_ref.u[0].u_bank.identity_ok)
   $display("DBG t=%0t u0 fail: ord %h bank %0d ep %h row %0d valid %b epq %h cnt %0d seen %b bid %0d", $time, u_ref.u[0].u_bank.ordinal, u_ref.u[0].u_bank.bank,
     u_ref.u[0].u_bank.epoch, u_ref.u[0].u_bank.row, u_ref.u[0].u_bank.valid_q, u_ref.u[0].u_bank.epoch_q[u_ref.u[0].u_bank.bank], u_ref.u[0].u_bank.count_q[u_ref.u[0].u_bank.bank],
     u_ref.u[0].u_bank.seen_q[u_ref.u[0].u_bank.bank][u_ref.u[0].u_bank.row], u_ref.u[0].u_bank.bank_id);
 `endif
 // ---------------- exact compare (vA) ----------------
`ifdef EXACT
 always @(posedge hclk or posedge sclk) begin
  #1;
  nexact=nexact+1;
  if (cr[0]!==cr[1]) err($sformatf("cr %h %h", cr[0], cr[1]));
  if (cm[0]!==cm[1]) err($sformatf("complete %h %h", cm[0], cm[1]));
  if (cb[0]!==cb[1]) err($sformatf("complete_bank %h %h", cb[0], cb[1]));
  if (bf[0]!==bf[1]) err($sformatf("bfault %h %h", bf[0], bf[1]));
  if (rd[0]!==rd[1]) err("read_data");
 end
`endif

 // ---------------- phases ----------------
 integer ph, i, j, k, cnt, bad, total, slot, abortp, seed, rr, row, perm[0:63];
 reg [15:0] ep; reg [255:0] pay;
 function automatic integer cntof(input integer t, input integer bid); cntof = (t > bid) ? (t + 7 - bid) / 8 : 0; endfunction
 task automatic do_reset; begin
  @(negedge sclk); rst_n=0; repeat(3) @(posedge hclk); repeat(3) @(posedge sclk);
  for (d=0; d<2; d=d+1) for (g=0; g<4; g=g+1) begin pi[d][g]=0; wn[d][g]=0; cn[d][g]=0; end
  for (g=0; g<4; g=g+1) pn[g]=0;
  @(negedge hclk); rst_n=1; repeat(4) @(posedge sclk);
 end endtask
 task automatic compare_events(input integer p); integer dd, gg, m; begin
  for (gg=0; gg<4; gg=gg+1) begin
   if (wn[0][gg]!=wn[1][gg]) err($sformatf("ph %0d u%0d landing writes %0d %0d", p, gg, wn[0][gg], wn[1][gg]));
   else for (m=0; m<wn[0][gg]; m=m+1) if (wl[0][gg][m]!==wl[1][gg][m]) err($sformatf("ph %0d u%0d write %0d differs", p, gg, m));
   if (cn[0][gg]!=cn[1][gg]) err($sformatf("ph %0d u%0d completes %0d %0d", p, gg, cn[0][gg], cn[1][gg]));
   else for (m=0; m<cn[0][gg]; m=m+1) if (cl[0][gg][m]!==cl[1][gg][m]) err($sformatf("ph %0d u%0d complete %0d bank", p, gg, m));
   if (bf[0][gg]!==bf[1][gg]) err($sformatf("ph %0d u%0d fault %b %b", p, gg, bf[0][gg], bf[1][gg]));
   if (credit[0][gg]!=credit[1][gg]) err($sformatf("ph %0d u%0d credits %0d %0d", p, gg, credit[0][gg], credit[1][gg]));
   if (pi[0][gg]!=pi[1][gg]) err($sformatf("ph %0d u%0d sent %0d %0d", p, gg, pi[0][gg], pi[1][gg]));
   nwr=nwr+wn[0][gg];
  end
 end endtask
 initial begin
  seed=`SEED; void'($urandom(seed));
  for (d=0; d<2; d=d+1) begin in_v[d]=0; in_d[d]=0; for (g=0; g<4; g=g+1) begin pi[d][g]=0; credit[d][g]=8; wn[d][g]=0; cn[d][g]=0; gwait[d][g]=-1; end end
  for (g=0; g<4; g=g+1) pn[g]=0;
  bk_hi=$urandom%2;
  repeat(3) @(posedge hclk); @(negedge hclk); rst_n=1; repeat(4) @(posedge sclk);
  for (ph=0; ph<`PHASES; ph=ph+1) begin
   abortp = ($urandom%8==0);   // re-reserve the active slot mid-traffic (vB: events not compared, invariant checked)
   slot=$urandom%4; ep=$urandom; total=$urandom%512;
   // reserve
   @(negedge sclk); res_v=1; res_bank=slot; res_epoch=ep; res_total=total; @(negedge sclk); res_v=0;
   repeat(2) @(posedge sclk);
   // build packet sequences
   for (g=0; g<4; g=g+1) begin
    cnt=cntof(total, {bk_hi,2'(g)});
    for (i=0;i<64;i=i+1) perm[i]=i;
    for (i=cnt-1;i>0;i=i-1) begin j=$urandom%(i+1); k=perm[i]; perm[i]=perm[j]; perm[j]=k; end
    bad=($urandom%10==0) ? $urandom%(cnt+1) : -1;
    for (i=0; i<cnt+((bad>=0)?1:0); i=i+1) begin
     row = (bad>=0 && i>bad) ? perm[i-1] : (bad>=0 && i==bad) ? -1 : perm[i];
     pay={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
     if (row>=0) pq[g][pn[g]]={2'b00,row[5:0],bk_hi,2'(g),2'(slot),ep,pay};
     else begin
      case ($urandom%5)
       0: pq[g][pn[g]]={2'b00,6'(perm[(i>0)?0:1]),bk_hi,2'(g),2'(slot),ep,pay};          // duplicate (or valid when first)
       1: pq[g][pn[g]]={2'b00,6'(perm[i]),bk_hi,2'(g),2'(slot),ep^16'h0100,pay};          // wrong epoch
       2: pq[g][pn[g]]={2'b00,6'(perm[i]),~bk_hi,2'(g+1),2'(slot),ep,pay};                // wrong landing bank
       3: pq[g][pn[g]]={2'b00,6'(cnt+($urandom%2)),bk_hi,2'(g),2'(slot),ep,pay};          // row >= count (or 63 wrap)
       default: pq[g][pn[g]]={2'b00,6'(perm[i]),bk_hi,2'(g),2'(slot+1),ep,pay};          // other slot (maybe unreserved)
      endcase
     end
     gap[g][pn[g]] = ($urandom%3==0) ? $urandom%6 : 0;
     pn[g]=pn[g]+1;
    end
   end
   // traffic: random stop, random reads (exact mode), random reserves of other slots
   for (i=0; i<1200; i=i+1) begin
    @(negedge sclk);
    stop = ($urandom%10==0) ? ~stop : stop; if (stop && $urandom%4==0) stop=0;
    if (`VAR==0) begin read_v=$urandom; read_bank=$urandom; read_row=$urandom; end else read_v=0;
    // other-slot reserves avoid slot+1 (the slot a bad packet may name); abort phases re-reserve the active slot
    if ($urandom%40==0) begin res_v=1; res_bank=(abortp && $urandom%2) ? slot : slot+2+$urandom%2; res_epoch=$urandom; res_total=$urandom%512; end else res_v=0;
   end
   @(negedge sclk); stop=0; res_v=0; read_v=0;
   repeat(200) @(posedge sclk);
   // read back every row of the phase slot
   for (row=0; row<64; row=row+1) begin
    @(negedge sclk); read_v=4'hf; read_bank=slot; read_row={4{row[5:0]}};
    @(negedge sclk); read_v=0;
    if (rd[0]!==rd[1] && (!abortp || `VAR==0)) err($sformatf("ph %0d readback slot %0d row %0d", ph, slot, row));
   end
`ifdef DBG
   $display("ph %0d slot %0d total %0d abort %0d bf %b wn %0d %0d %0d %0d pn %0d %0d %0d %0d sent %0d %0d %0d %0d cn %0d %0d %0d %0d ov %b%b%b%b sticky %b%b%b%b", ph, slot, total, abortp, bf[0],
     wn[0][0],wn[0][1],wn[0][2],wn[0][3], pn[0],pn[1],pn[2],pn[3], pi[0][0],pi[0][1],pi[0][2],pi[0][3], cn[0][0],cn[0][1],cn[0][2],cn[0][3],
     u_ref.u[0].u_bank.ov,u_ref.u[1].u_bank.ov,u_ref.u[2].u_bank.ov,u_ref.u[3].u_bank.ov,
     u_ref.u[0].u_bank.sticky,u_ref.u[1].u_bank.sticky,u_ref.u[2].u_bank.sticky,u_ref.u[3].u_bank.sticky);
`endif
   if (abortp) begin nabort=nabort+1; $display("ABORT_PHASE %0d (vB: events and read-back not compared)", ph); end
   if (!abortp || `VAR==0) compare_events(ph);
   nfault=nfault+(bf[0]!=0);
   // reset after faults / aborts or at random, so the log and fault state restart together
   if (bf[0]!=0 || bf[1]!=0 || abortp || $urandom%6==0) do_reset;
   // vB abort phase: the outcome of packets around a mid-traffic re-reserve of their own slot may differ by the extra
   // stream cycle, so the bench copies the reference SRAM contents into the DUT bench SRAM after the reset
   if (abortp && `VAR!=0) for (k=0; k<256; k=k+1) begin
    u_dut.u[0].u_bank.u_payload.m[k]=u_ref.u[0].u_bank.u_payload.m[k]; u_dut.u[1].u_bank.u_payload.m[k]=u_ref.u[1].u_bank.u_payload.m[k];
    u_dut.u[2].u_bank.u_payload.m[k]=u_ref.u[2].u_bank.u_payload.m[k]; u_dut.u[3].u_bank.u_payload.m[k]=u_ref.u[3].u_bank.u_payload.m[k];
   end
  end
  $display("BENCH aborts=%0d var=%0d mut=%0d seed=%0d phases=%0d writes=%0d completes=%0d fault_phases=%0d exact_samples=%0d errors=%0d",
           nabort, `VAR, `MUTN, `SEED, `PHASES, nwr, ncompl, nfault, nexact, errs);
  if (errs==0) $display("SVGR_BK_B12_BENCH PASS"); else $display("SVGR_BK_B12_BENCH FAIL");
  $finish;
 end
endmodule

// bench SRAM model (both designs): registered read, holds without r_ce, full-word write
module ot_sram_1r1w_256x256_m2_r2c2(input wire clk, input wire r_ce_in, input wire [7:0] r_addr_in, output reg [255:0] rd_out,
 input wire w_ce_in, input wire [7:0] w_addr_in, input wire [255:0] wd_in, input wire [255:0] w_mask_in,
 input wire [1:0] rr_en, input wire [13:0] rr_addr, input wire [1:0] cr_en, input wire [15:0] cr_sel);
 reg [255:0] m[0:255]; integer i; initial begin for (i=0;i<256;i=i+1) m[i]=0; rd_out=0; end
 always @(posedge clk) begin if (r_ce_in) rd_out<=m[r_addr_in]; if (w_ce_in) m[w_addr_in]<=(wd_in&w_mask_in)|(m[w_addr_in]&~w_mask_in); end
endmodule
