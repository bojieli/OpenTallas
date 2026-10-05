`timescale 1ps/1fs
// DS-only additive parent. Clocks are real INPUTS, never averaged/generated here.
// Model: hbm_pcwb_actual_parent_20261005 plus parent_implementation model_delta.
// POR is cold whole-provider reset; warm reset cannot erase externally accepted debt.
module ot_hbm_accel_pcwb_service_stack #(
 parameter integer ENABLE=0,CMD_MATCH_CUT=0,STACK=0,CRED=64,WQ=8
)(
 input wire service_clk,core_clk,por_n,
 input wire owner_v,output wire owner_r,
 input wire [63:0] producer,input wire [31:0] transport,irs_serial,
 input wire [6:0] rank,input wire [1:0] stack,
 output wire owner_held,output wire [63:0] held_producer,
 output wire [31:0] held_transport,held_irs_serial,
 output wire [6:0] held_rank,output wire [1:0] held_stack,
 input wire [6:0] die,input wire [19:0] pos,
 input wire row_v,output wire row_r,input wire [1:0] row_kind,
 input wire [5:0] row_slot,input wire row_r2,input wire [4351:0] row_data,
 input wire sh_v,output wire sh_r,input wire [2:0] sh_slot,input wire [4351:0] sh_data,
 input wire [31:0] desc_v,output wire [31:0] desc_r,
 input wire [607:0] desc_row,input wire [351:0] desc_n,
 input wire [31:0] go,next_posted,notice,
 input wire [15:0] ca_ready,output wire [15:0] ca_valid,ca_pc_lsb,
 output wire [47:0] ca_op,output wire [79:0] ca_bank,output wire [303:0] ca_row,
 output wire [31:0] phy_col_v,input wire [31:0] phy_col_r,
 output wire [31:0] phy_we,output wire [159:0] phy_bank,phy_col,
 output wire [607:0] phy_row,output wire [8191:0] phy_data,
 output wire [6367:0] phy_receipt,
 input wire [31:0] visible_v,output wire [31:0] visible_r,input wire [6367:0] visible_receipt,
 input wire [31:0] rd_return_v,output wire [31:0] rd_return_r,input wire [8191:0] rd_return_data,
 output wire [31:0] read_v,input wire [31:0] read_r,output wire [8191:0] read_data,
 output wire [31:0] pc_busy,output wire [15:0] issued,acked,
 output wire fence_ok,output wire fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
  assign owner_r=0;assign owner_held=0;assign held_producer=0;assign held_transport=0;
  assign held_irs_serial=0;assign held_rank=0;assign held_stack=0;assign row_r=0;assign sh_r=0;
  assign desc_r=0;assign ca_valid=0;assign ca_pc_lsb=0;assign ca_op=0;assign ca_bank=0;assign ca_row=0;
  assign phy_col_v=0;assign phy_we=0;assign phy_bank=0;assign phy_col=0;assign phy_row=0;assign phy_data=0;
  assign phy_receipt=0;assign visible_r=0;assign rd_return_r=0;assign read_v=0;assign read_data=0;
  assign pc_busy=0;assign issued=0;assign acked=0;assign fence_ok=0;assign fault=0;
 end else begin:on
  initial if(CRED!=64||WQ!=8||STACK<0||STACK>3)$fatal(1,"PCWB priced parent requires CRED64/WQ8/STACK0..3");
  // {producer64,transport32,generation32,rank7,stack2,owned,fence,sticky}.
  reg [139:0] frame_q,frame_n;reg [215:0] frame_seal;reg frame_bad;
  assign owner_held=frame_q[2];assign held_producer=frame_q[139:76];
  assign held_transport=frame_q[75:44];assign held_irs_serial=frame_q[43:12];
  assign held_rank=frame_q[11:5];assign held_stack=frame_q[4:3];
  wire [31:0] adapter_fault,pc_fault,wq_empty,wr_drained,landing_empty,landing_full;
  wire [31:0] row_req,col_v,col_we,ctrl_wr_ack,raw_desc_r,wq_v,wq_r;
  wire [95:0] row_op,cred_ret;
  wire [31:0] row_grant;
  wire [159:0] row_bank,col_bank,col_col;
  wire [607:0] row_row,col_row;
  wire [8191:0] col_wdata;
  wire ca_fault;
  wire [31:0] wr_visible_v;
  wire [6367:0] wr_visible_receipt;
  wire [223:0] queued;
  reg [32:0] read_state[0:31],read_next[0:31];reg [71:0] read_seal[0:31];
  reg read_bad,read_event_bad;reg all_read_drained;
  wire [31:0] rd_to_land=rd_return_v&rd_return_r;
  reg [5:0] ack_n;
  wire wb_fence,wb_row_r,wb_wq_v;
  wire [4:0] wb_pc,wb_bank,wb_col;
  wire [18:0] wb_row;wire [255:0] wb_data;
  wire all_column_drained=(queued==0);
  wire all_drained=all_column_drained&&(&wr_drained)&&(&wq_empty)&&
    all_read_drained&&(&landing_empty)&&!(|pc_busy);
  assign owner_r=!fault&&all_drained&&(!owner_held||frame_q[1])&&(stack==2'(STACK));
  wire bind_owner=owner_v&&owner_r;
  wire active=owner_held&&!fault&&!bind_owner;
  wire descriptor_safe=active&&frame_q[1]&&wb_fence&&(&wr_drained)&&(&wq_empty)&&all_column_drained;
  assign desc_r=raw_desc_r&{32{descriptor_safe}};
  assign row_r=active&&wb_row_r;
  // The existing fence proves writer idle and all previous writes visible.
  // row_r suppresses sh_v, so it cannot feed shadow ready without a loop.
  assign sh_r=active&&wb_fence&&!row_v;
  wire [31:0] adapter_wr_r;
  // There is no ready override: the selected adapter reserves a real lease and PC WQ seat.
  wire writer_queue_ready=active&&adapter_wr_r[wb_pc];
  assign fence_ok=owner_held&&frame_q[1]&&!fault;
  assign fault=frame_q[0]||frame_bad||read_bad||ca_fault||(|adapter_fault)||(|pc_fault);
  always @* begin
   reg [191:0] pad;pad={52'b0,frame_q};frame_bad=0;
   for(integer w=0;w<3;w=w+1)begin
    reg [65:0] d;d=decode64(frame_seal[w*72+:72]);
    if(d[65]||d[63:0]!=pad[w*64+:64])frame_bad=1;
   end
  end
  // Decode checks depend only on retained words, never on admission or fault.
  // Keep these independent from next-state to avoid an artificial ready/fault
  // scheduling cycle in the enclosing combinational process.
  always @* begin
   all_read_drained=1;read_bad=0;
   for(integer n=0;n<32;n=n+1)begin
    reg [65:0] d;
    d=decode64(read_seal[n]);if(d[65]||d[63:0]!={31'b0,read_state[n]})read_bad=1;
    if(read_state[n][6:0]!=0||read_state[n][13:7]!=0)all_read_drained=0;
   end
  end
  always @* begin
   ack_n=0;
   for(integer n=0;n<32;n=n+1)
    if(wr_visible_v[n]&&active)ack_n=ack_n+6'd1;
  end
  always @* begin
   read_event_bad=0;
   for(integer n=0;n<32;n=n+1)begin
    integer total_n,phy_n;
    read_next[n]=read_state[n];
    total_n=int'(read_state[n][6:0])+int'(col_v[n]&&!col_we[n])-int'(cred_ret[n*3+:3]);
    phy_n=int'(read_state[n][13:7])+int'(phy_col_v[n]&&phy_col_r[n]&&!phy_we[n])-int'(rd_to_land[n]);
    if(total_n<0||total_n>64||phy_n<0||phy_n>64||phy_n>total_n)read_event_bad=1;
    if(rd_return_v[n]&&read_state[n][13:7]==0)read_event_bad=1;
    read_next[n][6:0]=7'(total_n);read_next[n][13:7]=7'(phy_n);
    if(desc_v[n]&&desc_r[n])read_next[n][32:14]=desc_row[n*19+:19];
   end
  end
  always @* begin
   frame_n=frame_q;
   if(bind_owner)frame_n[139:2]={producer,transport,irs_serial,rank,stack,1'b1};
   frame_n[1]=owner_held&&wb_fence&&(&wr_drained)&&(&wq_empty)&&all_column_drained&&!bind_owner;
   frame_n[0]=fault||read_event_bad;
  end
  always @(posedge service_clk or negedge por_n)
   if(!por_n)begin
    frame_q<=0;frame_seal<=0;
    for(integer n=0;n<32;n=n+1)begin read_state[n]<=0;read_seal[n]<=0;end
   end else begin
    reg [191:0] pad;pad={52'b0,frame_n};frame_q<=frame_n;
    for(integer w=0;w<3;w=w+1)frame_seal[w*72+:72]<=encode64(pad[w*64+:64]);
    if(!read_bad&&!read_event_bad)for(integer n=0;n<32;n=n+1)begin
     read_state[n]<=read_next[n];read_seal[n]<=encode64({31'b0,read_next[n]});
    end
   end
  ot_hbm_accel_dskv_wb #(.ENABLE(1),.STACK(STACK)) u_writer(
   .clk(service_clk),.rst_n(por_n),.die(die),.pos(pos),
   .row_v(row_v&&active),.row_kind(row_kind),.row_slot(row_slot),.row_r2(row_r2),.row_data(row_data),.row_r(wb_row_r),
   .sh_v(sh_v&&sh_r),.sh_slot(sh_slot),.sh_data(sh_data),
   .wq_v(wb_wq_v),.wq_pc(wb_pc),.wq_bank(wb_bank),.wq_row(wb_row),.wq_col(wb_col),.wq_data(wb_data),
   .wq_r(writer_queue_ready),.ack_n(ack_n),.issued(issued),.acked(acked),.fence_ok(wb_fence));
  ot_hbm_pcwb_ca_slots #(.ENABLE(1),.NCH(16)) u_ca(
   .service_clk(service_clk),.por_n(por_n),.run_enable(!fault),.row_req(row_req),.row_op(row_op),
   .row_bank(row_bank),.row_row(row_row),.ca_ready(ca_ready),.row_grant(row_grant),
   .ca_valid(ca_valid),.ca_pc_lsb(ca_pc_lsb),.ca_op(ca_op),.ca_bank(ca_bank),.ca_row(ca_row),.fault(ca_fault));
  for(genvar pc=0;pc<32;pc=pc+1)begin:channel
   wire [18:0] actual_col_row=col_we[pc]?col_row[pc*19+:19]:read_state[pc][32:14];
   assign rd_return_r[pc]=active&&!landing_full[pc]&&read_state[pc][13:7]!=0;
   ot_hbm_accel_cdc_fifo #(.W(256),.AW(6)) u_landing(
    .wclk(service_clk),.wrst_n(por_n),.we(rd_to_land[pc]),.wdata(rd_return_data[pc*256+:256]),.full(landing_full[pc]),
    .rd_freed(cred_ret[pc*3+:3]),.rclk(core_clk),.rrst_n(por_n),.re(read_v[pc]&&read_r[pc]),
    .rdata(read_data[pc*256+:256]),.empty(landing_empty[pc]));
   assign read_v[pc]=!landing_empty[pc];
   ot_hbm_pcwb_prepaid_column #(.ENABLE(1),.PC(pc)) u_prepaid(
    .service_clk(service_clk),.por_n(por_n),.context_valid(active),.operation(held_producer),.phase(held_transport),.generation(held_irs_serial),
    .wr_v(wb_wq_v&&(wb_pc==5'(pc))),.wr_r(adapter_wr_r[pc]),.wr_bank(wb_bank),.wr_row(wb_row),.wr_col(wb_col),.wr_data(wb_data),
    .wq_v(wq_v[pc]),.wq_r(wq_r[pc]),.col_v(col_v[pc]),.col_we(col_we[pc]),.col_bank(col_bank[pc*5+:5]),
    .col_row(actual_col_row),.col_col(col_col[pc*5+:5]),.col_data(col_wdata[pc*256+:256]),
    .phy_col_v(phy_col_v[pc]),.phy_col_r(phy_col_r[pc]),.phy_we(phy_we[pc]),.phy_bank(phy_bank[pc*5+:5]),
    .phy_row(phy_row[pc*19+:19]),.phy_col(phy_col[pc*5+:5]),.phy_data(phy_data[pc*256+:256]),.phy_receipt(phy_receipt[pc*199+:199]),
    .visible_v(visible_v[pc]),.visible_r(visible_r[pc]),.visible_receipt(visible_receipt[pc*199+:199]),
    .wr_visible_v(wr_visible_v[pc]),.wr_visible_r(active),.wr_visible_receipt(wr_visible_receipt[pc*199+:199]),
    .queued(queued[pc*7+:7]),.inflight(),.visible_not_returned(),.all_writes_drained(wr_drained[pc]),.fault(adapter_fault[pc]));
   if(CMD_MATCH_CUT)begin:candidate
    ot_hbm_accel_stream_pc_wb_command_match #(.ENABLE(1),.REF_MODE(1),.PC(pc),.CRED(CRED),.WB_EN(1),.WQ(WQ),.REF_PHASE((pc*118)/32%118),.WA_LATE(1),.DIGEST_CUT(1),.CMD_MATCH_CUT(1)) u_controller(
    .clk(service_clk),.rst_n(por_n),.desc_v(desc_v[pc]&&descriptor_safe),.desc_r(raw_desc_r[pc]),
    .desc_row(desc_row[pc*19+:19]),.desc_n(desc_n[pc*11+:11]),.go(go[pc]&&active),.next_posted(next_posted[pc]),.notice(notice[pc]),
    .row_v(row_req[pc]),.row_prio(),.row_gnt(row_grant[pc]),.row_op(row_op[pc*3+:3]),.row_bank(row_bank[pc*5+:5]),.row_row(row_row[pc*19+:19]),
    .col_v(col_v[pc]),.col_bank(col_bank[pc*5+:5]),.col_col(col_col[pc*5+:5]),.cred_ret(cred_ret[pc*3+:3]),.busy(pc_busy[pc]),.ref_fault(pc_fault[pc]),
    .wq_v(wq_v[pc]),.wq_bank(wb_bank),.wq_row(wb_row),.wq_col(wb_col),.wq_data(wb_data),.wq_r(wq_r[pc]),
    .col_we(col_we[pc]),.col_wdata(col_wdata[pc*256+:256]),.col_row(col_row[pc*19+:19]),.wr_ack(ctrl_wr_ack[pc]),.wq_empty(wq_empty[pc]));
   end else begin:original
    ot_hbm_accel_stream_pc_wb #(.ENABLE(1),.REF_MODE(1),.PC(pc),.CRED(CRED),.WB_EN(1),.WQ(WQ),.REF_PHASE((pc*118)/32%118)) u_controller(
    .clk(service_clk),.rst_n(por_n),.desc_v(desc_v[pc]&&descriptor_safe),.desc_r(raw_desc_r[pc]),
    .desc_row(desc_row[pc*19+:19]),.desc_n(desc_n[pc*11+:11]),.go(go[pc]&&active),.next_posted(next_posted[pc]),.notice(notice[pc]),
    .row_v(row_req[pc]),.row_prio(),.row_gnt(row_grant[pc]),.row_op(row_op[pc*3+:3]),.row_bank(row_bank[pc*5+:5]),.row_row(row_row[pc*19+:19]),
    .col_v(col_v[pc]),.col_bank(col_bank[pc*5+:5]),.col_col(col_col[pc*5+:5]),.cred_ret(cred_ret[pc*3+:3]),.busy(pc_busy[pc]),.ref_fault(pc_fault[pc]),
    .wq_v(wq_v[pc]),.wq_bank(wb_bank),.wq_row(wb_row),.wq_col(wb_col),.wq_data(wb_data),.wq_r(wq_r[pc]),
    .col_we(col_we[pc]),.col_wdata(col_wdata[pc*256+:256]),.col_row(col_row[pc*19+:19]),.wr_ack(ctrl_wr_ack[pc]),.wq_empty(wq_empty[pc]));
   end
  end
 end endgenerate
endmodule
