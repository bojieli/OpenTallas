`timescale 1ns/1ps
`default_nettype none
// One independently hardened bank, six read replicas, one canonical write.
// The caller supplies compiler-assigned bank slots. No queues/arbitration or
// producer handshakes exist. All replicas see identical writes, including
// masked-word semantics inside the REAL provider SRAM. Read address conflicts
// between consumers must be resolved by the compiler before this boundary.
module ot_hbm_su_static_replicated_bank #(
 parameter integer READERS=6,RB=9,MUT_COHERENCE=0
)(
 input wire clk,
 input wire[READERS-1:0]read_v,
 input wire[READERS*RB-1:0]read_addr,
 output wire[READERS*32-1:0]read_data,
 input wire write_v,input wire[RB-1:0]write_addr,input wire[31:0]write_data
);
 for(genvar r=0;r<READERS;r=r+1)begin:g_read
  ot_hgi_su_lbank #(.RB(RB),.MACRO(1))u_bank(
   .clk(clk),.re(read_v[r]),.ra(read_addr[r*RB+:RB]),.rd(read_data[r*32+:32]),
   .we(write_v && !(MUT_COHERENCE!=0&&r==READERS-1)),.wa(write_addr),.wd(write_data));
 end
endmodule

// Full aggregate N512/LWB18 data capacity, partitioned into four quarters.
// Global word address decomposition preserves FOUR frames, each quartered:
// frame=a[17:16], quadrant=a[15:14], bank=a[6:0], row={a[17:16],a[13:7]}.
// Each q contains128 bank leaves; each leaf has its own compensated clock pin.
// Payload wiring is explicit and there is no memory model in this parent.
module ot_hbm_su_static_data_store #(
 parameter integer QUARTERS=4,BANKS_PER_QUARTER=128,READERS=6,RB=9,MUT_COHERENCE=0
)(
 input wire[QUARTERS*BANKS_PER_QUARTER-1:0]clk_bank,
 input wire[QUARTERS*BANKS_PER_QUARTER*READERS-1:0]read_v,
 input wire[QUARTERS*BANKS_PER_QUARTER*READERS*RB-1:0]read_addr,
 output wire[QUARTERS*BANKS_PER_QUARTER*READERS*32-1:0]read_data,
 input wire[QUARTERS*BANKS_PER_QUARTER-1:0]write_v,
 input wire[QUARTERS*BANKS_PER_QUARTER*RB-1:0]write_addr,
 input wire[QUARTERS*BANKS_PER_QUARTER*32-1:0]write_data
);
 for(genvar q=0;q<QUARTERS;q=q+1)begin:g_q
  for(genvar b=0;b<BANKS_PER_QUARTER;b=b+1)begin:g_bank
   localparam I=q*BANKS_PER_QUARTER+b;
   ot_hbm_su_static_replicated_bank #(.READERS(READERS),.RB(RB),.MUT_COHERENCE(MUT_COHERENCE))u_bank(
    .clk(clk_bank[I]),.read_v(read_v[I*READERS+:READERS]),
    .read_addr(read_addr[I*READERS*RB+:READERS*RB]),.read_data(read_data[I*READERS*32+:READERS*32]),
    .write_v(write_v[I]),.write_addr(write_addr[I*RB+:RB]),.write_data(write_data[I*32+:32]));
  end
 end
endmodule
`default_nettype wire
