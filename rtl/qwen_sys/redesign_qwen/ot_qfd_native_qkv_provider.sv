`timescale 1ns/1ps
// Default-off full native provider surface. Reservation precedes the first
// real accepted V instruction. Other SU computation may continue while this
// epoch is live; never gate every SU op on KVcommitted. Accepted issue_kind
// must be decoded from the source-bound actual instruction (V,Klo,Khi).
// q_start requires actual QR VM writes committed for this identity.
module ot_qfd_native_qkv_provider #(parameter integer ENABLE=0)(
 input wire clk,rst_n,
 input wire epoch_begin,input wire [15:0] epoch,input wire [5:0] layer,input wire [17:0] pos,
 output wire epoch_ready,
 input wire kv_issue_accepted,input wire [1:0] kv_issue_kind,input wire [17:0] kv_issue_nout,kv_issue_nin,
 output wire kv_admit_ready,
 input wire [63:0] kv_we,input wire [1535:0] kv_waddr,input wire [2047:0] kv_wdata,
 output wire formatter_emitted,
 output wire row_v,input wire row_ready,output wire row_kind,output wire [15:0] row_epoch,
 output wire [5:0] row_layer,output wire [17:0] row_pos,output wire [1023:0] row_data,
 input wire [3:0] store_ack_v,store_ack_kind,input wire [63:0] store_ack_epoch,
 input wire [23:0] store_ack_layer,input wire [71:0] store_ack_pos,
 output wire [3:0] store_ack_credit,output wire kv_committed,
 input wire q_start,input wire qr_vm_committed,input wire [23:0] q_base,
 output wire q_start_ready,
 output wire vm_req_v,input wire vm_req_ready,output wire [15:0] vm_req_epoch,
 output wire [2:0] vm_req_chunk,output wire [23:0] vm_req_a0,vm_req_a1,
 input wire vm_rsp_v,input wire [15:0] vm_rsp_epoch,input wire [2:0] vm_rsp_chunk,input wire [2047:0] vm_rsp_data,
 output wire q_v,input wire q_ready,output wire [5:0] q_beat,output wire [511:0] q_data,
 output wire [15:0] q_epoch,output wire q_emitted_done,output wire fault
);
 reg reserved,admission_fault;reg [1:0] settling;reg [2:0] admitted;
 reg [15:0] held_epoch;wire fs,ps,qs,ff,pf,qf,word_v,word_ready;wire [10:0] word_tag;wire [511:0] word_data;wire [7:0] formatter_fault_code;
 assign fault=admission_fault||ff||pf||qf;
 assign epoch_ready=ENABLE!=0&&fs&&ps&&qs&&!fault;
 assign kv_admit_ready=ENABLE!=0&&reserved&&settling==0&&kv_issue_kind<3&&!admitted[kv_issue_kind]&&!fault&&!kv_committed;
 assign q_start_ready=ENABLE!=0&&reserved&&qs&&qr_vm_committed&&!fault;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin reserved<=0;admission_fault<=0;settling<=0;admitted<=0;held_epoch<=0;end
  else if(ENABLE!=0)begin
   if(epoch_begin)begin
    if(!epoch_ready)admission_fault<=1;
    else begin reserved<=1;settling<=2;admitted<=0;held_epoch<=epoch;end
   end else if(settling!=0)settling<=settling-1'b1;
   if(kv_issue_accepted)begin
    if(!kv_admit_ready)admission_fault<=1;
    else admitted[kv_issue_kind]<=1;
   end
   if(q_start&&!q_start_ready)admission_fault<=1;
  end
 end
 ot_qfd_su_kv_native_posted #(.ENABLE(ENABLE),.HEADS(1)) u_formatter(
 .clk(clk),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch_pos(pos),.issue_v(kv_issue_accepted),.issue_kind(kv_issue_kind),
 .issue_nout(kv_issue_nout),.issue_nin(kv_issue_nin),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),
 .epoch_ready(fs),.drained(formatter_emitted),.word_v(word_v),.word_tag(word_tag),.word_data(word_data),.word_ready(word_ready),.fault(ff),.fault_code(formatter_fault_code));
 ot_qfd_native_kv_row_provider #(.ENABLE(ENABLE)) u_rows(
 .clk(clk),.rst_n(rst_n),.begin_v(epoch_begin),.begin_epoch(epoch),.begin_layer(layer),.begin_pos(pos),.begin_ready(ps),
 .word_v(word_v),.word_tag(word_tag),.word_data(word_data),.word_ready(word_ready),.formatter_emitted(formatter_emitted),
 .row_v(row_v),.row_ready(row_ready),.row_kind(row_kind),.row_epoch(row_epoch),.row_layer(row_layer),.row_pos(row_pos),.row_data(row_data),
 .ack_v(store_ack_v),.ack_kind(store_ack_kind),.ack_epoch(store_ack_epoch),.ack_layer(store_ack_layer),.ack_pos(store_ack_pos),.ack_credit(store_ack_credit),.committed(kv_committed),.fault(pf));
 ot_qfd_native_q_reader #(.ENABLE(ENABLE)) u_q(
 .clk(clk),.rst_n(rst_n),.start_v(q_start&&q_start_ready),.start_epoch(held_epoch),.start_base(q_base),.start_ready(qs),
 .req_v(vm_req_v),.req_ready(vm_req_ready),.req_epoch(vm_req_epoch),.req_chunk(vm_req_chunk),.req_a0(vm_req_a0),.req_a1(vm_req_a1),
 .rsp_v(vm_rsp_v),.rsp_epoch(vm_rsp_epoch),.rsp_chunk(vm_rsp_chunk),.rsp_data(vm_rsp_data),
 .q_v(q_v),.q_ready(q_ready),.q_beat(q_beat),.q_data(q_data),.q_epoch(q_epoch),.emitted_done(q_emitted_done),.fault(qf));
endmodule
