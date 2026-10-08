`timescale 1ns/1ps
// Lockstep equivalence: Codex's ot_hbm_die_vm_multicast_root (original, package import) against the yosys copy
// (renamed ot_hbm_die_vm_multicast_root_y), ENABLE=1, identical random stimulus incl. write/read/publish/ack protocol,
// wrong-owner ACKs and periodic cold resets.  Every output compared every cycle.
module tb_mroot_equiv;
 reg clk=0; always #0.5 clk=~clk;
 reg por_n; reg wr_v, wr_bank, rd_v, rd_bank, wr_ACK_ready; reg [6:0] wr_addr, rd_addr;
 reg [2062:0] wr_data; reg [191:0] wr_owner, rd_owner; reg [3:0] tap_ready, tap_ACK_v; reg [4*192-1:0] tap_ACK_owner;
 wire wr_ready_a,wr_ACK_v_a,rd_ready_a,native_release_a,drained_a,fault_a; wire [191:0] wr_ACK_owner_a;
 wire [3:0] tap_v_a; wire [4*2063-1:0] tap_data_a; wire [4*192-1:0] tap_owner_a;
 wire wr_ready_b,wr_ACK_v_b,rd_ready_b,native_release_b,drained_b,fault_b; wire [191:0] wr_ACK_owner_b;
 wire [3:0] tap_v_b; wire [4*2063-1:0] tap_data_b; wire [4*192-1:0] tap_owner_b;
 ot_hbm_die_vm_multicast_root #(.ENABLE(1)) a(.clk(clk),.por_n(por_n),.wr_v(wr_v),.wr_ready(wr_ready_a),.wr_bank(wr_bank),.wr_addr(wr_addr),
  .wr_data(wr_data),.wr_owner(wr_owner),.wr_ACK_v(wr_ACK_v_a),.wr_ACK_ready(wr_ACK_ready),.wr_ACK_owner(wr_ACK_owner_a),
  .rd_v(rd_v),.rd_ready(rd_ready_a),.rd_bank(rd_bank),.rd_addr(rd_addr),.rd_owner(rd_owner),.tap_v(tap_v_a),.tap_ready(tap_ready),
  .tap_data(tap_data_a),.tap_owner(tap_owner_a),.tap_ACK_v(tap_ACK_v),.tap_ACK_owner(tap_ACK_owner),
  .native_release(native_release_a),.drained(drained_a),.fault(fault_a));
 ot_hbm_die_vm_multicast_root_y #(.ENABLE(1)) b(.clk(clk),.por_n(por_n),.wr_v(wr_v),.wr_ready(wr_ready_b),.wr_bank(wr_bank),.wr_addr(wr_addr),
  .wr_data(wr_data),.wr_owner(wr_owner),.wr_ACK_v(wr_ACK_v_b),.wr_ACK_ready(wr_ACK_ready),.wr_ACK_owner(wr_ACK_owner_b),
  .rd_v(rd_v),.rd_ready(rd_ready_b),.rd_bank(rd_bank),.rd_addr(rd_addr),.rd_owner(rd_owner),.tap_v(tap_v_b),.tap_ready(tap_ready),
  .tap_data(tap_data_b),.tap_owner(tap_owner_b),.tap_ACK_v(tap_ACK_v),.tap_ACK_owner(tap_ACK_owner),
  .native_release(native_release_b),.drained(drained_b),.fault(fault_b));
 wire [ (6+192+4+4*2063+4*192)-1:0] oa={wr_ready_a,wr_ACK_v_a,rd_ready_a,native_release_a,drained_a,fault_a,wr_ACK_owner_a,tap_v_a,tap_data_a,tap_owner_a};
 wire [ (6+192+4+4*2063+4*192)-1:0] ob={wr_ready_b,wr_ACK_v_b,rd_ready_b,native_release_b,drained_b,fault_b,wr_ACK_owner_b,tap_v_b,tap_data_b,tap_owner_b};
 reg [191:0] shadow[0:7]; reg [7:0] vmap; reg [2:0] ra; reg [3:0] hs=0; always @(posedge clk) hs <= tap_v_a & tap_ready;
 always @(posedge clk) begin if(!por_n) vmap<=0; else if(wr_v && wr_ready_a) begin shadow[{wr_bank,wr_addr[1:0]}] <= wr_owner; vmap[{wr_bank,wr_addr[1:0]}]<=1; end end integer cyc=0, mism=0, nwack=0, nrel=0, nfault=0, i; reg [3:0] sent_seen;
 function [2062:0] rnd2063; integer k; begin for(k=0;k<65;k=k+1) rnd2063[k*32+:32]=$random; end endfunction
 function [191:0] rnd192; integer k; begin for(k=0;k<6;k=k+1) rnd192[k*32+:32]=$random; end endfunction
 initial begin
  por_n=0; wr_v=0; rd_v=0; wr_bank=0; rd_bank=0; wr_addr=0; rd_addr=0; wr_data=0; wr_owner=0; rd_owner=0; wr_ACK_ready=0;
  tap_ready=0; tap_ACK_v=0; tap_ACK_owner=0; sent_seen=0;
  for(cyc=0; cyc<`CYC; cyc=cyc+1) begin
   @(negedge clk);
   if(oa!==ob) begin mism=mism+1; if(mism<5) $display("MISMATCH cyc %0d", cyc); end
   if(wr_ACK_v_a) nwack=nwack+1; if(native_release_a) nrel=nrel+1; if(fault_a) nfault=nfault+1;
   por_n = !((cyc%160)<2);
   wr_v = ($urandom%4)==0; wr_bank=$urandom%2; wr_addr=$urandom%4; wr_data=rnd2063(); wr_owner=rnd192();
   ra=$urandom%8; rd_v = (($urandom%3)==0) && (vmap[ra] || ($urandom%40)==0); rd_bank=ra[2]; rd_addr={5'd0,ra[1:0]}; rd_owner=(($urandom%30)==0)?rnd192():shadow[{rd_bank,rd_addr[1:0]}];
   wr_ACK_ready = ($urandom%2);
   sent_seen = sent_seen | hs;
   tap_ready = $urandom;
   tap_ACK_v=0;
   for(i=0;i<4;i=i+1) if(sent_seen[i] && ($urandom%3)==0) begin tap_ACK_v[i]=1; sent_seen[i]=0;
     tap_ACK_owner[i*192+:192] = (($urandom%50)==0) ? rnd192() : tap_owner_a[i*192+:192]; end
   if(($urandom%3000)==0) tap_ACK_v[$urandom%4]=1;
   if(!por_n) sent_seen=0;
  end
  $display("EQUIV cycles=%0d mismatches=%0d wr_acks=%0d releases=%0d fault_cycles=%0d", cyc, mism, nwack, nrel, nfault);
  if(mism) $fatal(1,"MISMATCH"); $finish;
 end
endmodule
