`timescale 1ns/1ps
// Registered 128-bit ACK reduction leaf; no combinational parent popcount.
module qkd_host_ack_sum(input wire ck,rst_n,input wire[127:0]acks,output reg[7:0]ack_n);
 reg[127:0]aq;reg[23:0]parts;
 function automatic[5:0]count32(input[31:0]a);integer k;begin count32=0;for(k=0;k<32;k=k+1)count32=count32+a[k];end endfunction
 always @(posedge ck or negedge rst_n)if(!rst_n)begin aq<=0;parts<=0;ack_n<=0;end else begin
 aq<=acks;for(integer k=0;k<4;k=k+1)parts[k*6+:6]<=count32(aq[k*32+:32]);
 ack_n<={2'd0,parts[5:0]}+{2'd0,parts[11:6]}+{2'd0,parts[17:12]}+{2'd0,parts[23:18]};end
endmodule
// Wires-only four-stack/32-logical-PC native static ingest parent. Every
// station and arbiter has its own child clock entry. All clocks belong to
// the same synchronous die phase family with per-child insertion correction.
// Actual controller static port and JEDEC retirement observer remain external;
// early er259 frees scheduler capacity while ordered completion is separate.
module qkd_host_ingest_chain #(parameter integer MUT=0)(
 input wire ck_map,ck_sum,input wire[127:0]ck_station,ck_static,input wire rst_n,
 input wire[289:0]ing,output wire ing_cr,
 input wire[36863:0]land_es,output wire[33407:0]land_er,
 output wire[36863:0]ctrl_es,input wire[33407:0]ctrl_er,
 input wire[127:0]completion_v,completion_we,
 output wire marker_v,output wire[65:0]marker,input wire marker_cr,
 output wire[31:0]issued,landed,output wire map_fault,output wire[3:0]chain_fault
);
 wire[1163:0]map_out;wire[127:0]credits,acks;wire[7:0]ack_n;
 qkd_host_ack_sum u_sum(.ck(ck_sum),.rst_n(rst_n),.acks(acks),.ack_n(ack_n));
 qkd_host_ingest_map u_map(.ck(ck_map),.rst_n(rst_n),.ing(ing),.ing_cr(ing_cr),.out(map_out),.out_cr(credits),.ack_n(ack_n),
 .marker_v(marker_v),.marker(marker),.marker_cr(marker_cr),.fault(map_fault),.issued(issued),.landed(landed));
 for(genvar st=0;st<4;st=st+1)begin:g_stack
  wire[290:0]f[0:32];wire[31:0]c[0:32],a[0:32];wire[32:0]fault;
  assign f[0]=map_out[st*291+:291];assign c[32]=0;assign a[32]=0;assign fault[32]=0;
  assign credits[st*32+:32]=c[0];assign acks[st*32+:32]=a[0];assign chain_fault[st]=fault[0];
  for(genvar pc=0;pc<32;pc=pc+1)begin:g_pc
   localparam integer ID=st*32+pc;
   wire[287:0]host_es;wire host_cr,host_ack,host_fault;
   qkd_host_ingest_station u_station(.ck(ck_station[ID]),.rst_n(rst_n),.lpc(5'(pc)),.fi(f[pc]),.fo(f[pc+1]),
   .host_es(host_es),.host_cr(host_cr),.host_ack(host_ack),.host_fault(host_fault),
   .ci(c[pc+1]),.co(c[pc]),.ai(a[pc+1]),.ao(a[pc]),.fault_i(fault[pc+1]),.fault_o(fault[pc]));
   qkd_host_static_pc #(.MUT(ID==127?MUT:0))u_static(.ck(ck_static[ID]),.rst_n(rst_n),
   .land_es(land_es[ID*288+:288]),.land_er(land_er[ID*261+:261]),.host_es(host_es),.host_cr(host_cr),.host_ack(host_ack),
   .ctrl_es(ctrl_es[ID*288+:288]),.ctrl_er(ctrl_er[ID*261+:261]),.completion_v(completion_v[ID]),.completion_we(completion_we[ID]),.fault(host_fault));
  end
 end
endmodule
