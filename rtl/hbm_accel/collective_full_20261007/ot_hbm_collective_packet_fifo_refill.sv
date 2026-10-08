`timescale 1ns/1ps
// II=1 successor of ot_hbm_collective_packet_fifo (same ports, storage, encoding, seal and fault rules).
// Opt-in: selected by ot_hbm_collective_fifo_adapter ENABLE_SRAM=2; the II=3 source is unchanged.
//
// The II=3 queue fetches only when nothing is pending or held: fetch -> pending (SRAM read, rd_out
// updates) -> held (encoded word captured, decoded, visible) -> pop, then the next fetch.
// The refill keeps a TWO-slot head with no new data register:
//   R    = the macro's own read latch (rd_out holds its value while r_ce_in is low; ot_sram_* behavioural
//          model: `if (r_ce_in) rd_out <= ...`), flag c.pending = "rd_out holds a fetched, untransferred word";
//   H    = captured (encoded, 648 b), flag c.held.
// Every cycle: xfer = pending && (!held || pop accepted) moves R -> H (captured <= ram_q);
//              fetch = unread != 0 && (!pending || xfer) issues the next SRAM read into R.
// In a stream with pop every cycle: H pops, R moves to H, the next read refills R -> one flit an edge.
// Empty start latency is unchanged (fetch, transfer, visible: 2 edges after the write edge).
// The read address is the REGISTERED c_rp (no pop -> address path); pop reaches only r_ce_in, the
// captured load enable and the control next-state, so the CDC's registered-address fix
// (addr = (hp==0) ? rb : rb_next) has no analogue here.
// count = unread + pending + held, exactly as before; ready = count < DEPTH; overflow latches.
// Head decode is SPLIT across the transfer edge (the full SECDED decode of the held word was a 27-level
// path to dout and to the fault/enable fan-out; first screen SS -909 ps): at the transfer edge each word's
// syndrome and overall parity are registered from the macro output (ram_q), so the head's data path is
// captured ^ (ovr && syn == position) (4 levels) and its uncorrectable flag is a register.  The SRAM
// residency keeps full SECDED (single corrected, double detected).  While held, the head register is
// checked by per-word parity against the parity registered at load: an upset there is DETECTED (fault one
// edge later; valid drops), not corrected -- the II=3 queue corrected it combinationally.
// Written for the ORFS Yosys frontend (no wildcard import inside a generate block, explicit
// package-scoped SECDED calls, no size casts): the II=3 source does not parse there.
module ot_hbm_collective_packet_fifo_refill #(parameter integer ENABLE=0, DEPTH=256)(
 input wire clk,rst_n,push,input wire [544:0] din,output wire ready,
 input wire pop,output wire valid,output wire [544:0] dout,
 output wire fault,output wire [8:0] count);
`ifndef SYNTHESIS
 initial if(ENABLE&&DEPTH!=64&&DEPTH!=256)$fatal(1,"collective FIFO depth must be 64 or 256");
`endif
 localparam [7:0] LAST=DEPTH-1;
 localparam [8:0] DEPTH9=DEPTH;
 localparam [0:0] EN=(ENABLE!=0);
 // control word {wp, rp, unread, pending, held, overflow} = 28 b, sealed with SECDED like the II=3 queue
 reg [7:0] c_wp,c_rp,n_wp,n_rp;reg [8:0] c_unread,n_unread;
 reg c_pending,c_held,c_overflow,n_pending,n_held,n_overflow;
 wire [63:0] c_word={36'b0,c_wp,c_rp,c_unread,c_pending,c_held,c_overflow};
 wire [63:0] n_word={36'b0,n_wp,n_rp,n_unread,n_pending,n_held,n_overflow};
 reg [71:0] seal;reg [647:0] captured;
 wire [767:0] ram_q;wire [767:0] ram_d;
 wire bad=seal!=ot_gpu_w6_secded_pkg::encode64(c_word);
 wire [575:0] decoded;wire [8:0] par_live;
 reg [62:0] syn_q;reg [8:0] ovr_q;reg ue_q,hpar_q;
 wire [575:0] din_pad={31'b0,din};
 // SECDED (ot_gpu_w6_secded_pkg layout): code position p = 1..71 at bit p-1, parity bits at 2^k, bit 71 overall.
 function automatic [6:0] syndrome7(input [71:0] code);
  integer k,p;
  begin
   syndrome7=7'd0;
   for(k=0;k<7;k=k+1)for(p=1;p<=71;p=p+1)if((p&(1<<k))!=0)syndrome7[k]=syndrome7[k]^code[p-1];
  end
 endfunction
 function automatic [63:0] correct64(input [71:0] code,input [6:0] syn,input ovr);
  integer p,j;
  begin
   correct64=64'd0;j=0;
   for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin correct64[j]=code[p-1]^(ovr&&syn==p[6:0]);j=j+1;end
  end
 endfunction
 genvar s;
 wire [8:0] ue_load;wire [62:0] syn_load;wire [8:0] ovr_load;
 generate for(s=0;s<9;s=s+1)begin:g_decode
  // load-time syndrome / parity from the macro output word
  assign syn_load[s*7+:7]=syndrome7(ram_q[s*72+:72]);
  assign ovr_load[s]=^ram_q[s*72+:72];
  assign ue_load[s]=(syn_load[s*7+:7]!=0)&&!(ovr_load[s]&&syn_load[s*7+:7]<=7'd71);
  // held-word data: registered syndrome selects the flip
  assign decoded[s*64+:64]=correct64(captured[s*72+:72],syn_q[s*7+:7],ovr_q[s]);
  assign par_live[s]=^captured[s*72+:72];
  assign ram_d[s*72+:72]=ot_gpu_w6_secded_pkg::encode64(din_pad[s*64+:64]);
 end endgenerate
 assign ram_d[767:648]=120'b0;
 wire [8:0] count_i=c_unread+{8'b0,c_pending}+{8'b0,c_held};
 // head faults: uncorrectable at load (registered), parity change while held (registered), nonzero pad bits
 wire fault_i=bad||c_overflow||(c_held&&(ue_q||hpar_q||(|decoded[575:545])));
 assign count=EN?count_i:9'd0;
 assign fault=EN&&fault_i;
 assign valid=EN&&c_held&&!fault_i;assign dout=EN?decoded[544:0]:545'b0;
 assign ready=EN&&count_i<DEPTH9&&!fault_i;
 wire put=push&&ready;
 wire take=valid&&pop;
 wire xfer=c_pending&&(!c_held||take)&&!fault;
 wire fetch=c_unread!=0&&(!c_pending||xfer)&&!fault;
 always @*begin
  n_wp=c_wp;n_rp=c_rp;n_unread=c_unread;n_pending=c_pending;n_held=c_held;n_overflow=c_overflow;
  if(push&&!ready)n_overflow=1'b1;
  if(put)begin n_wp=(c_wp==LAST)?8'd0:c_wp+8'd1;n_unread=n_unread+9'd1;end
  if(take)n_held=1'b0;
  if(xfer)begin n_pending=1'b0;n_held=1'b1;end
  if(fetch)begin n_rp=(c_rp==LAST)?8'd0:c_rp+8'd1;n_unread=n_unread-9'd1;n_pending=1'b1;end
 end
 genvar m;
 generate for(m=0;m<3;m=m+1)begin:g_ram
  ot_sram_1r1w_256x256_m2_r2c2 storage(.clk(clk),.r_ce_in(fetch),.r_addr_in(c_rp),.rd_out(ram_q[m*256+:256]),
   .w_ce_in(put),.w_addr_in(c_wp),.wd_in(ram_d[m*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin
   c_wp<=0;c_rp<=0;c_unread<=0;c_pending<=0;c_held<=0;c_overflow<=0;seal<=0;captured<=0;
   syn_q<=0;ovr_q<=0;ue_q<=0;hpar_q<=0;
  end else if(!fault)begin
   c_wp<=n_wp;c_rp<=n_rp;c_unread<=n_unread;c_pending<=n_pending;c_held<=n_held;c_overflow<=n_overflow;
   seal<=ot_gpu_w6_secded_pkg::encode64(n_word);
   if(xfer)begin captured<=ram_q[647:0];syn_q<=syn_load;ovr_q<=ovr_load;ue_q<=|ue_load;hpar_q<=1'b0;end
   else if(c_held)hpar_q<=hpar_q||(par_live!=ovr_q);
  end
endmodule
