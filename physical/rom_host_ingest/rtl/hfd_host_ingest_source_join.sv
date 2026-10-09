`timescale 1ns/1ps
// Actual host engine/translator -> existing K-port map -> per-stack source1.
// Its descriptor fence receives the GLOBAL accepted prefix, never sum4ACK.
module hfd_host_ingest_source_join #(parameter integer ENABLE=0,IQ=4,MUT_SUM_ACK=0)(
 input wire rst_n,clk_h,h_v,input wire[1:0]h_cls,input wire[511:0]h_d,
 output wire[4:0]h_crn,output wire t_v,output wire[63:0]t_d,input wire t_cr,
 input wire clk_i,ck,output wire[3:0]stack_v,input wire[3:0]stack_r,
 output wire[1163:0]stack_packet,input wire[23:0]ingest_stack_ack_n,
 output wire slot_done_v,output wire[7:0]slot_done_tag,
 output wire eop_v,output wire[63:0]eop_d,output wire pending,fault
);
 generate if(!ENABLE)begin:off
 assign h_crn=0;assign t_v=0;assign t_d=0;assign stack_v=0;assign stack_packet=0;
 assign slot_done_v=0;assign slot_done_tag=0;assign eop_v=0;assign eop_d=0;
 assign pending=0;assign fault=0;
 end else begin:on
 wire wv,wr;wire[1:0]ws;wire[4:0]pc,bank,col;wire[18:0]row;
 wire[255:0]data;wire[29:0]sector;wire host_fault,map_fault,order_fault,order_rdy;
 wire[5:0]global_ack_n;
 hfd_host_ingest #(.IQ(IQ),.FENCE(1)) actual_host(
 .rst_n(rst_n),.clk_h(clk_h),.h_v(h_v),.h_cls(h_cls),.h_d(h_d),.h_crn(h_crn),
 .t_v(t_v),.t_d(t_d),.t_cr(t_cr),.clk_i(clk_i),.ck(ck),
 .wq_v(wv),.wq_stack(ws),.wq_pc(pc),.wq_bank(bank),.wq_row(row),.wq_col(col),
 .wq_data(data),.wq_r(wr),.ack_n(global_ack_n),.slot_done_v(slot_done_v),
 .slot_done_tag(slot_done_tag),.eop_v(eop_v),.eop_d(eop_d),.fault(host_fault));
 ot_hbm_kport_map actual_map(.pc(pc),.bank(bank),.row(row),.col(col),.s(sector),.fault(map_fault));
 wire healthy=!host_fault&&!order_fault&&!(wv&&map_fault);
 assign wr=order_rdy&&stack_r[ws]&&healthy;
 for(genvar s=0;s<4;s=s+1)begin
 assign stack_v[s]=wv&&order_rdy&&healthy&&ws==s;
 assign stack_packet[291*s+:291]={data,sector,pc};
 end
 ot_hbm_ingest_global_prefix #(.ENABLE(1),.DEPTH(1024),.MUT_SUM_ACK(MUT_SUM_ACK)) actual_prefix(
 .ck(ck),.rst_n(rst_n),.issue_v(wv&&wr),.issue_stack(ws),.issue_rdy(order_rdy),
 .stack_ack_n(ingest_stack_ack_n),.ack_n(global_ack_n),.pending(pending),.fault(order_fault));
 assign fault=host_fault||order_fault||(wv&&map_fault);
 end endgenerate
endmodule
