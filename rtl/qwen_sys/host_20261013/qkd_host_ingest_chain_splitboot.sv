// Wires-only four-stack/32-logical-PC native static ingest parent. Every
// station and arbiter has its own child clock entry. All clocks belong to
// the same synchronous die phase family with per-child insertion correction.
// Actual controller static port and JEDEC retirement observer remain external;
// early er259 frees scheduler capacity while ordered completion is separate.
module qkd_host_ingest_chain_splitboot #(parameter integer MUT=0,ORDER_MUT=0)(
 input wire ck_map,ck_sum,ck_order,input wire[127:0]ck_station,ck_static,input wire rst_n,
 input wire[289:0]ing,output wire ing_cr,
 input wire[36863:0]land_es,output wire[33407:0]land_er,
 output wire[36863:0]ctrl_es,input wire[33407:0]ctrl_er,
 input wire[127:0]completion_v,completion_we,
 output wire[127:0]all_acks,output wire marker_v,output wire[65:0]marker,input wire marker_cr,
 output wire[31:0]issued,landed,output wire map_fault,output wire[3:0]chain_fault,output wire[7:0]ack_n,physical_ack_n,output wire order_fault
);
 wire[1163:0]map_out;wire[127:0]credits,acks;wire issue_v,prefix_v;wire[6:0]issue_pc;wire[31:0]prefix_count;
 assign ack_n={7'd0,prefix_v};
 qkd_host_ack_sum u_sum(.ck(ck_sum),.rst_n(rst_n),.acks(acks),.ack_n(physical_ack_n));
 qkd_host_commit_order #(.MUT(ORDER_MUT))u_order(.ck(ck_order),.rst_n(rst_n),.issue_v(issue_v),.issue_pc(issue_pc),.acks(acks),.prefix_v(prefix_v),.prefix_count(prefix_count),.fault(order_fault));
 qkd_host_ingest_map #(.ORDERED(1))u_map(.ck(ck_map),.rst_n(rst_n),.ing(ing),.ing_cr(ing_cr),.out(map_out),.out_cr(credits),.ack_n(ack_n),
 .marker_v(marker_v),.marker(marker),.marker_cr(marker_cr),.fault(map_fault),.issued(issued),.landed(landed),.ord_cr(prefix_v),.issue_v(issue_v),.issue_pc(issue_pc));
 for(genvar st=0;st<4;st=st+1)begin:g_stack
  wire[290:0]f[0:32];wire[31:0]c[0:32],a[0:32];wire[32:0]fault;
  assign f[0]=map_out[st*291+:291];assign c[32]=0;assign a[32]=0;assign fault[32]=0;
  assign credits[st*32+:32]=c[0];assign acks[st*32+:32]=a[0];assign chain_fault[st]=fault[0];
  for(genvar pc=0;pc<32;pc=pc+1)begin:g_pc
   localparam integer ID=st*32+pc;
   wire[287:0]host_es;wire host_cr,host_ack,land_ack,host_fault;
   assign all_acks[ID]=host_ack|land_ack;
   qkd_host_ingest_station u_station(.ck(ck_station[ID]),.rst_n(rst_n),.lpc(5'(pc)),.fi(f[pc]),.fo(f[pc+1]),
   .host_es(host_es),.host_cr(host_cr),.host_ack(host_ack),.host_fault(host_fault),
   .ci(c[pc+1]),.co(c[pc]),.ai(a[pc+1]),.ao(a[pc]),.fault_i(fault[pc+1]),.fault_o(fault[pc]));
   qkd_host_static_pc_emback #(.MUT(ID==127?MUT:0))u_static(.ck(ck_static[ID]),.rst_n(rst_n),
   .land_es(land_es[ID*288+:288]),.land_er(land_er[ID*261+:261]),.host_es(host_es),.host_cr(host_cr),.host_ack(host_ack),.land_ack(land_ack),
   .ctrl_es(ctrl_es[ID*288+:288]),.ctrl_er(ctrl_er[ID*261+:261]),.completion_v(completion_v[ID]),.completion_we(completion_we[ID]),.fault(host_fault));
  end
 end
endmodule
