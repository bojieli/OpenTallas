`timescale 1ns/1ps
`default_nettype none
// OT_SFU_SYNC_RST (H-SU k8, 2026-10-16 owner standard: regional SYNC reset trees, no async-clear fanout): when defined,
// every reset in this file is synchronous to its own clock (the regional rst_n comes registered from ot_rst_relay /
// the die's regional relays); undefined = the previous asynchronous form, bit-identical behaviour after release.
`ifndef OT_SFU_ARST
`ifdef OT_SFU_SYNC_RST
`define OT_SFU_ARST(r)
`else
`define OT_SFU_ARST(r) or negedge r
`endif
`endif
// Fixed-cycle SFU VM prefetch/drain bridge. Requests and selectors come from
// an actual compiler programme. No request FIFO, credits, leases or retries.
// Mid-tap READ_RETURN14 is measured at response pins after edge n+14 for a
// request captured n; SRAM/scalar store consumes the response at n+15.
// The metadata delay crosses exactly those14 response edges alongside data.
module ot_hgi_sfu_vm_static_bridge #(
 parameter integer LWB=15, READ_RETURN=14, WRITE_RETURN=11,
 // DRAIN_PIPE=1 (SFU-K9 10-18, k9 textbook REFUSE: operand-store output bank word select -> sector rotate -> BF16
 // round adder -> write_q mux was one ~772 ps / 19-level reg->reg stage): one clk register stage on the whole drain
 // interface (drain_v/round/vm_sector/result_v/data) before the per-group write logic. Every drain observer moves with
 // the data, so the drain-> local_wq edge and local_w_done return both come exactly 1 edge later; WRITE_RETURN is
 // unchanged (it counts from the registered drain). 0 = the previous behaviour (k7/k8/split kits, scheduled engine).
 parameter integer DRAIN_PIPE=0,
 // BRING=1 (L2H-SU-FB k9x 10-19, safe-design item 5: storage > 2 kb / delay lines >= 3 deep): the READ_RETURN+1-edge
 // metadata delay of each LG root (44 x 65 = 2,860 flops) and the scalar-address delay (96 x 65 = 6,240 flops) were
 // 65-deep flop shift chains with a synchronous clear on every stage. Each becomes a ring buffer in one
 // ot_sram_1r1w_128x256_m1_r2c2 on the same root (written and read every edge, read address = write address - READ_RETURN,
 // registered read = the last stage) plus a 7-bit fill counter that holds the output at 0 until READ_RETURN+1 edges
 // after reset release -- exactly the cleared chain's output. Same edges; 0 = the flop chains (bit-identical).
 parameter integer BRING=0
)(
 input wire clk,rst_n,
 // Four related, same-frequency clock roots, one for each physical bank pair.
 // They are not asynchronous domains: no CDC FIFO or extra service edge.
 input wire [3:0] clk_lg,rst_lg_n,
 input wire [7:0] prefetch_v,
 input wire [127:0] prefetch_sector,
 input wire [15:0] prefetch_group,
 input wire [8*LWB-1:0] prefetch_local_addr,
 input wire [7:0] prefetch_scalar,
 input wire [23:0] prefetch_word,
 input wire [95:0] scalar_addr,
 output wire [135:0] local_rq,
 input wire [2055:0] local_rr,
 output wire [7:0] stage_v,
 output wire [15:0] stage_group,
 output wire [8*LWB-1:0] stage_addr,
 output wire [2047:0] stage_data,
 output wire [63:0] stage_mask,
 output reg [3:0] scalar_load,
 output wire [95:0] scalar_load_addr,
 output reg [127:0] scalar_data,
 input wire [1:0] drain_v,drain_round_bf16,
 input wire [31:0] drain_vm_sector,
 input wire [1:0] drain_result_v,
 input wire [511:0] drain_data,
 output wire [2247:0] local_wq,
 input wire [7:0] local_w_done,
 output reg fault
);
 localparam META=2+4+2*LWB+2+6;
 wire [1:0] dr_v,dr_round,dr_result_v;
 wire [31:0] dr_sector;
 wire [511:0] dr_data;
 if(DRAIN_PIPE!=0)begin:g_drain_pipe
  reg [1:0] v_q,round_q,result_q;
  reg [31:0] sector_q;
  reg [511:0] data_q;
  always @(posedge clk)begin round_q<=drain_round_bf16;sector_q<=drain_vm_sector;data_q<=drain_data;end
  always @(posedge clk `OT_SFU_ARST(rst_n))
   if(!rst_n)begin v_q<=0;result_q<=0;end else begin v_q<=drain_v;result_q<=drain_result_v;end
`ifdef OT_SFU_BRIDGE_MUT_NODRAINPIPE
  // bench negative control: data bypasses the drain stage while the valids keep it (sector written 1 edge early)
  assign {dr_v,dr_round,dr_sector,dr_result_v,dr_data}={v_q,drain_round_bf16,drain_vm_sector,result_q,drain_data};
`else
  assign {dr_v,dr_round,dr_sector,dr_result_v,dr_data}={v_q,round_q,sector_q,result_q,data_q};
`endif
 end else begin:g_drain_direct
  assign {dr_v,dr_round,dr_sector,dr_result_v,dr_data}={drain_v,drain_round_bf16,drain_vm_sector,drain_result_v,drain_data};
 end
 wire [7:0] expect_v,scalar;
 wire [23:0] word_sel;
 wire [3:0] group_fault;
 // Scalar addresses belong to the programme, independent of the VM bank.
 wire [95:0] scalar_ring_q;
 if(BRING!=0)begin:g_sring
  ot_hgi_sfu_delay_sram #(.W(96),.D(READ_RETURN+1)) u_sring(.clk(clk),.rst_n(rst_n),.d(scalar_addr),.q(scalar_ring_q));
 end else begin:g_spipe
  reg [95:0] scalar_addr_pipe[0:READ_RETURN];
  always @(posedge clk `OT_SFU_ARST(rst_n))begin
   if(!rst_n)begin
    for(integer i=0;i<=READ_RETURN;i=i+1)scalar_addr_pipe[i]<=0;
   end else begin
    scalar_addr_pipe[0]<=scalar_addr;
    for(integer i=1;i<=READ_RETURN;i=i+1)scalar_addr_pipe[i]<=scalar_addr_pipe[i-1];
   end
  end
  assign scalar_ring_q=scalar_addr_pipe[READ_RETURN];
 end
 assign scalar_load_addr=scalar_ring_q;
 assign stage_v=expect_v&~scalar;
 assign stage_mask=64'hffffffffffffffff;
 for(genvar b=0;b<8;b=b+1)begin:g_read
  assign local_rq[b*17+:17]={prefetch_v[b],prefetch_sector[b*16+:16]};
  assign stage_data[b*256+:256]=local_rr[b*257+:256];
 end
 reg scalar_collision;
 reg [3:0] used_group;
 always @*begin
  scalar_load=0;scalar_data=0;used_group=0;scalar_collision=0;
  for(integer b=0;b<8;b=b+1)if(expect_v[b]&&scalar[b])begin
   if(used_group[stage_group[2*b+:2]])scalar_collision=1;
   used_group[stage_group[2*b+:2]]=1;
   scalar_load[stage_group[2*b+:2]]=1;
   scalar_data[32*stage_group[2*b+:2]+:32]=local_rr[257*b+32*word_sel[3*b+:3]+:32];
  end
 end
 function automatic [255:0] round_sector(input [255:0] data,input do_round);
  reg [31:0] word,rounded;
  for(integer w=0;w<8;w=w+1)begin
   word=data[32*w+:32];
`ifdef OT_SFU_VM_BF16_MUTANT
   rounded=word+32'h00007fff; // true negative: ties with odd high word round the wrong way
`else
   rounded=word+32'h00007fff+{31'd0,word[16]};
`endif
   round_sector[32*w+:32]=do_round?{rounded[31:16],16'd0}:word;
  end
 endfunction
 // Actual state partition: each root owns only its two banks' metadata,
 // request checks, write output flops and fixed completion observers.
 // The programme and operand store remain on clk. Their related-clock
 // crossings require the die clock/pin plan; this is not a reach waiver.
 for(genvar g=0;g<4;g=g+1)begin:g_lg
  wire [META-1:0] meta_in={prefetch_v[2*g+:2],prefetch_group[4*g+:4],prefetch_local_addr[2*LWB*g+:2*LWB],
              prefetch_scalar[2*g+:2],prefetch_word[6*g+:6]};
  wire [META-1:0] meta_q;
  if(BRING!=0)begin:g_mring
   ot_hgi_sfu_delay_sram #(.W(META),.D(READ_RETURN+1)) u_mring(.clk(clk_lg[g]),.rst_n(rst_lg_n[g]),.d(meta_in),.q(meta_q));
  end else begin:g_mpipe
   reg [META-1:0] meta[0:READ_RETURN];
   always @(posedge clk_lg[g] `OT_SFU_ARST(rst_lg_n[g]))begin
    if(!rst_lg_n[g])begin
     for(integer i=0;i<=READ_RETURN;i=i+1)meta[i]<=0;
    end else begin
     meta[0]<=meta_in;
     for(integer i=1;i<=READ_RETURN;i=i+1)meta[i]<=meta[i-1];
    end
   end
   assign meta_q=meta[READ_RETURN];
  end
  reg [561:0] write_q;
  assign local_wq[562*g+:562]=write_q;
  assign {expect_v[2*g+:2],stage_group[4*g+:4],stage_addr[2*LWB*g+:2*LWB],
          scalar[2*g+:2],word_sel[6*g+:6]}=meta_q;
  reg [1:0] drain_round_q,drain_expected;
  reg [31:0] drain_sector_q;
  reg [1:0] write_expected[0:WRITE_RETURN+1];
  reg [1:0] write_v;
  reg write_collision;
  reg fault_q;
  assign group_fault[g]=fault_q;
  always @*begin
   write_v=0;write_collision=0;
   for(integer s=0;s<2;s=s+1)
    if(drain_expected[s] && drain_sector_q[16*s+1+:2]==g)begin
     if(write_v[drain_sector_q[16*s]])write_collision=1;
     write_v[drain_sector_q[16*s]]=1;
    end
  end
  always @(posedge clk_lg[g])begin
   drain_sector_q<=dr_sector;drain_round_q<=dr_round;
   write_q<=0;
   for(integer s=0;s<2;s=s+1)
    if(drain_expected[s] && drain_sector_q[16*s+1+:2]==g)
     write_q[281*drain_sector_q[16*s]+:281]<=
      {1'b1,drain_sector_q[16*s+:16],round_sector(dr_data[256*s+:256],drain_round_q[s]),8'hff};
  end
  always @(posedge clk_lg[g] `OT_SFU_ARST(rst_lg_n[g]))begin
   if(!rst_lg_n[g])begin
    fault_q<=0;drain_expected<=0;
    for(integer i=0;i<=WRITE_RETURN+1;i=i+1)write_expected[i]<=0;
   end else begin
    drain_expected<=dr_v;
    write_expected[0]<=write_v;
    for(integer i=1;i<=WRITE_RETURN+1;i=i+1)write_expected[i]<=write_expected[i-1];
    for(integer b=0;b<2;b=b+1)begin
     if(prefetch_v[2*g+b]&&prefetch_sector[16*(2*g+b)+:3]!=(2*g+b))fault_q<=1;
     if(expect_v[2*g+b]!=local_rr[(2*g+b)*257+256])fault_q<=1;
     if(write_expected[WRITE_RETURN+1][b]!=local_w_done[2*g+b])fault_q<=1;
    end
    if(dr_result_v!=drain_expected || write_collision)fault_q<=1;
   end
  end
 end
 always @(posedge clk `OT_SFU_ARST(rst_n))begin
  if(!rst_n)begin
   fault<=0;
  end else begin
   if(|group_fault || scalar_collision)fault<=1;
  end
 end
endmodule
`default_nettype wire
`timescale 1ns/1ps
`default_nettype none
// L2H-SU-FB k9x (10-19): fixed D-edge delay (q after edge k = d sampled at edge k-D+1, i.e. a D-stage register chain
// cleared by rst_n) as a ring buffer in one ot_sram_1r1w_128x256_m1_r2c2 (registered read = last stage) + fill counter.
// D in 2..127, W <= 256. Unused SRAM bit lanes are write-masked off; repair ports unused (no spare mapped).
module ot_hgi_sfu_delay_sram #(parameter integer W=44, parameter integer D=65) (
 input wire clk, rst_n,
 input wire [W-1:0] d,
 output wire [W-1:0] q
);
 if(D<2 || D>127 || W>256)begin:g_bad
  ot_hgi_sfu_delay_sram_bad_params u_refuse();
 end
 localparam [6:0] RD=7'(D-1);
 localparam [6:0] FULL=7'(D);
 reg [6:0] wp, fill;
 always @(posedge clk `OT_SFU_ARST(rst_n))
  if(!rst_n)begin wp<=7'd0;fill<=7'd0;end
  else begin wp<=wp+7'd1;if(fill!=FULL)fill<=fill+7'd1;end
 reg ok;   // output stage valid: the read issued at this edge returns a word written after reset release
 always @(posedge clk `OT_SFU_ARST(rst_n))
  if(!rst_n)ok<=1'b0;else ok<=(fill>=7'(D-1));
 wire [255:0] rd;
 wire [255:0] wd=256'(d);
 wire [255:0] wm={{(256-W){1'b0}},{W{1'b1}}};
`ifdef OT_SFU_BRIDGE_MUT_BRING
 wire [6:0] ra=wp-RD+7'd1;   // bench negative control: every ring reads one edge early (must FAIL)
`else
 wire [6:0] ra=wp-RD;
`endif
 ot_sram_1r1w_128x256_m1_r2c2 u_ram(.clk(clk),.r_ce_in(1'b1),.r_addr_in(ra),.rd_out(rd),
  .w_ce_in(1'b1),.w_addr_in(wp),.wd_in(wd),.w_mask_in(wm),
  .rr_en(2'b00),.rr_addr(14'd0),.cr_en(2'b00),.cr_sel(16'd0));
 assign q=ok ? rd[W-1:0] : {W{1'b0}};
endmodule
`default_nettype wire
