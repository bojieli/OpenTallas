// Generated additive core; baseline SHA256 4a4d0ca08c4c230059f6817ad29f74e6c83ee5a3caca306d51637dc44f4e0ce5
// Candidate SM-local owner. Model precedes RTL: tools/hbm_sm_serial_owner_model.py.
// Program memory: one outstanding 32-bit byte-addressed read, response >=1 edge
// after request, echoing address. Records exactly match dshbm_sm_pq_seq.py.
// Allocation response carries an ACTUAL weight line address; no base_of alias.
// X producer accepts context {record,ring base,extent}, returns ordered 2048-bit
// beats tagged {record,ordinal,group}. Full NC8 shape: 13 beats, final 640 bits.
// Completion requires actual SM arrive AND matching result-publication receipt.
// Collective release remains externally owned. All peers share this local clock;
// upstream CDC/long wires must terminate in real queues, never raw remote ready.
(* keep = 1, keep_hierarchy = 1, dont_touch = 1 *)
module ot_hbm_sm_serial_protected_core #(parameter ENABLE=0, MAX_RECORDS=256)(
 input wire clk,rst_n,
 input wire run_valid,output wire run_ready,input wire[31:0] program_base,
 input wire[32:0] program_limit,input wire[15:0] record_count,
 output wire mem_req_valid,input wire mem_req_ready,output wire[31:0] mem_req_addr,
 input wire mem_rsp_valid,output wire mem_rsp_ready,input wire[31:0] mem_rsp_addr,mem_rsp_data,input wire mem_rsp_error,
 output wire alloc_valid,input wire alloc_ready,output wire[15:0] alloc_record,
 output wire[23:0] alloc_lines,
 input wire alloc_rsp_valid,output wire alloc_rsp_ready,input wire[15:0] alloc_rsp_record,
 input wire[31:0] alloc_rsp_base,input wire alloc_rsp_error,
 output wire x_req_valid,input wire x_req_ready,output wire[15:0] x_req_record,
 output wire[6:0] x_req_base,output wire[7:0] x_req_extent,
 input wire x_valid,output wire x_ready,input wire[15:0] x_record,
 input wire[6:0] x_ordinal,input wire[3:0] x_group,input wire[2047:0] x_data,input wire x_error,
 output reg xw_en,output reg[6:0] xw_addr,xw_grp,output reg[2047:0] xw_data,
 output wire d_valid,input wire d_ready,output wire[31:0] d_base,output wire[23:0] d_lines,
 output wire start,input wire start_ready,output wire[12:0] op_rows,output wire[15:0] op_c,
 output wire[7:0] op_g,output wire op_gs,output wire[1:0] op_fmt,output wire[6:0] op_xb,
 input wire arrive,sm_fault,input wire publication_valid,output wire publication_ready,input wire[15:0] publication_record,
 output wire done,input wire done_ready,output reg fault, output wire state_parity
);
 localparam IDLE=0,READ_REQ=1,READ_WAIT=2,CHECK=3,ALLOC=4,ALLOC_WAIT=5,
            DESC=6,XREQ=7,XLOAD=8,CAPTURE=9,SEND=10,WAIT_DONE=11,COMPLETE=12,FAILED=13;
 reg[4:0] state;
 reg[319:0] record;
 reg[31:0] address;
 reg[32:0] limit;
 reg[15:0] count,index;
 reg[3:0] word_index,group;
 reg[7:0] ordinal;
 reg[31:0] weight_base;
 reg resident;
 reg[6:0] resident_base;
 reg[7:0] resident_extent;
 reg[15:0] resident_c;
 reg[1:0] resident_fmt;
 reg arrive_q,arrived,published,started;
 assign state_parity=^{state,record,address,limit,count,index,word_index,group,ordinal,weight_base,resident,resident_base,resident_extent,resident_c,resident_fmt,arrive_q,arrived,published,started,fault,xw_en,xw_addr,xw_grp,xw_data};
 wire[31:0] rows=record[31:0],cols=record[63:32],groups=record[95:64];
 wire[31:0] fmt=record[127:96],lines=record[159:128],gs=record[191:160];
 wire[31:0] load_x=record[223:192],extent=record[255:224],dep=record[287:256],xb=record[319:288];
 wire valid_record=rows>0 && rows<=4096 && cols>0 && cols<=65535 && groups>0 && groups<=255 &&
  fmt<=2 && lines>0 && lines<=24'hffffff && gs<=1 && load_x<=1 && dep<=1 &&
  extent>0 && extent<=128 && extent==cols*groups && xb<128;
 wire reuse_ok=resident && resident_base==xb[6:0] && resident_extent==extent[7:0] &&
  resident_c==cols[15:0] && resident_fmt==fmt[1:0];
 wire seq_ready,ingress_fault,ingress_start;
 wire protocol_abort=sm_fault || ingress_fault ||
  (mem_rsp_valid && state!=READ_WAIT) || (alloc_rsp_valid && state!=ALLOC_WAIT) ||
  ((arrive!=arrive_q) && (state!=WAIT_DONE || !started)) ||
  (publication_valid && publication_ready && publication_record!=index);
 assign start=ingress_start && ENABLE && !fault && !protocol_abort;
 wire retire=state==WAIT_DONE && arrived && published;
 assign run_ready=ENABLE && state==IDLE && !fault;
 assign mem_req_valid=ENABLE && state==READ_REQ && !fault;
 assign mem_req_addr=address;
 assign mem_rsp_ready=ENABLE && state==READ_WAIT && !fault;
 assign alloc_valid=ENABLE && state==ALLOC && !fault;
 assign alloc_record=index;assign alloc_lines=lines[23:0];
 assign alloc_rsp_ready=ENABLE && state==ALLOC_WAIT && !fault;
 assign d_valid=ENABLE && state==DESC && !fault;
 assign d_base=weight_base;assign d_lines=lines[23:0];
 assign x_req_valid=ENABLE && state==XREQ && !fault;
 assign x_req_record=index;assign x_req_base=xb[6:0];assign x_req_extent=extent[7:0];
 assign x_ready=ENABLE && state==XLOAD && !fault;
 assign publication_ready=ENABLE && state==WAIT_DONE && started && !published && !fault;
 assign done=ENABLE && state==COMPLETE && !fault;
 ot_hbm_sm_seq_ingress #(.ENABLE(ENABLE),.HOPS(0),.DEPTH(1)) ingress(
  .clk(clk),.rst_n(rst_n),.seq_valid(state==SEND && !fault),.seq_ready(seq_ready),.seq_data(record),
  .operand_published(state==SEND),.retired(retire),.start(ingress_start),.start_ready(start_ready && !fault && !protocol_abort),
  .op_rows(op_rows),.op_c(op_c),.op_g(op_g),.op_gs(op_gs),.op_fmt(op_fmt),.op_xb(op_xb),.fault(ingress_fault));
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n)begin
   state<=IDLE;record<=0;address<=0;limit<=0;count<=0;index<=0;word_index<=0;group<=0;ordinal<=0;
   weight_base<=0;resident<=0;resident_base<=0;resident_extent<=0;resident_c<=0;resident_fmt<=0;
   arrive_q<=0;arrived<=0;published<=0;started<=0;fault<=0;xw_en<=0;xw_addr<=0;xw_grp<=0;xw_data<=0;
  end else begin
   xw_en<=0;arrive_q<=arrive;
   if(ENABLE && !fault)begin
    if(start && start_ready)started<=1;
    if(arrive!=arrive_q)begin
     if(state!=WAIT_DONE || !started)begin fault<=1;state<=FAILED;end
     else arrived<=1;
    end
    if(publication_valid && publication_ready)begin
     if(publication_record!=index)begin fault<=1;state<=FAILED;end
     else published<=1;
    end
    if(mem_rsp_valid && state!=READ_WAIT)begin fault<=1;state<=FAILED;end
    if(alloc_rsp_valid && state!=ALLOC_WAIT)begin fault<=1;state<=FAILED;end
    if(ingress_fault)begin fault<=1;state<=FAILED;end
    case(state)
     IDLE:if(run_valid)begin
      if(record_count==0 || record_count>MAX_RECORDS || program_base[1:0]!=0 ||
         program_limit>33'h100000000 || {1'b0,program_base}+record_count*33'd40>program_limit)begin fault<=1;state<=FAILED;end
      else begin address<=program_base;limit<=program_limit;count<=record_count;index<=0;word_index<=0;resident<=0;state<=READ_REQ;end
     end
     READ_REQ:if(mem_req_ready)state<=READ_WAIT;
     READ_WAIT:if(mem_rsp_valid)begin
      if(mem_rsp_error || mem_rsp_addr!=address || {1'b0,address}+33'd4>limit)begin fault<=1;state<=FAILED;end
      else begin
       record[word_index*32+:32]<=mem_rsp_data;
       if(word_index==9)begin word_index<=0;state<=CHECK;end
       else begin word_index<=word_index+1'b1;address<=address+4;state<=READ_REQ;end
      end
     end
     CHECK:if(!valid_record || (!load_x && !reuse_ok))begin fault<=1;state<=FAILED;end
       else state<=ALLOC;
     ALLOC:if(alloc_ready)state<=ALLOC_WAIT;
     ALLOC_WAIT:if(alloc_rsp_valid)begin
      if(alloc_rsp_error || alloc_rsp_record!=index || {1'b0,alloc_rsp_base}+lines>33'h100000000)begin fault<=1;state<=FAILED;end
      else begin weight_base<=alloc_rsp_base;state<=DESC;end
     end
     DESC:if(d_ready)begin
      ordinal<=0;group<=0;arrived<=0;published<=0;started<=0;
      if(load_x)state<=XREQ;else state<=SEND;
     end
     XREQ:if(x_req_ready)state<=XLOAD;
     XLOAD:if(x_valid)begin
      if(x_error || x_record!=index || x_ordinal!=ordinal[6:0] || x_group!=group)begin fault<=1;state<=FAILED;end
      else begin
       xw_en<=1;xw_addr<=xb[6:0]+ordinal[6:0];xw_grp<={3'b0,group};
       xw_data<=group==12 ? {{1408{1'b0}},x_data[639:0]} : x_data;
       if(group==12)begin
        group<=0;
        if(ordinal+1==extent)begin
         resident<=1;resident_base<=xb[6:0];resident_extent<=extent[7:0];resident_c<=cols[15:0];resident_fmt<=fmt[1:0];state<=CAPTURE;
        end else ordinal<=ordinal+1'b1;
       end else group<=group+1'b1;
      end
     end
     CAPTURE:state<=SEND; // final registered X beat is captured by SM on this edge
     SEND:if(seq_ready)state<=WAIT_DONE;
     WAIT_DONE:if(retire)begin
      if(index+1==count)state<=COMPLETE;
      else begin index<=index+1'b1;address<=address+4;word_index<=0;state<=READ_REQ;end
     end
     COMPLETE:if(done_ready)state<=IDLE;
     default:begin end
    endcase
    if(protocol_abort)begin fault<=1;state<=FAILED;xw_en<=0;end
   end
  end
 end
endmodule
