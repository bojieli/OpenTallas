// Actual Qwen norm namespace: baseword0, q1024-word spans selected by QID.
// Full owner74/op64/PC/query/session receipt context; SRAM encoding unchanged.
`timescale 1ns/1ps
// Source-sized additive full4096 FP32 publication. The parent grants an actual
// stable VM read lease after matching write ACK and visibility completion.
// req337={write,byteaddr32,data256,byteMask32,tag16};
// rsp273={tag16,writeEcho,data256}. Fault transport is separate, not writeEcho.
// No same-edge memory fiction: injector indexed reads return four edges later.
module ot_hbm_collective_vm_publication_query #(parameter ENABLE=0,OWNER_W=74,OP_W=64)(
 input wire clk,rst_n,warm_abort,service_fault,service_quiet,
 input wire start_valid,output wire start_ready,
 input wire[OWNER_W-1:0] owner,input wire[OP_W-1:0] operation,
 input wire[11:0] pc,input wire[1:0] query_slot,
 input wire[31:0] base_word,input wire[23:0] session,
 output wire[3:0] req_valid,input wire[3:0] req_ready,
 output wire[4*337-1:0] req,
 input wire[3:0] rsp_valid,output wire[3:0] rsp_ready,
 input wire[4*273-1:0] rsp,
 output wire published,output wire quiet,output wire fault,
output wire read_pending,output wire[OWNER_W+OP_W+12+2+24-1:0] published_frame,
 input wire release_lease,
 input wire[1:0] inj_rd,input wire[31:0] inj_idx,
 output wire[1:0] inj_valid,output wire[1023:0] inj_data
);
 generate if(ENABLE)begin:g_on
 localparam IDLE=0,REQUEST=1,RESPONSE=2,SETTLE=3,PUBLISHED=4,ABORT=5;
 reg[2:0] state;reg bad,pending;reg[8:0] sector;
 reg[13:0] tagseq[0:3];reg[15:0] expected;
 reg[OWNER_W-1:0] bound_owner;reg[OP_W-1:0] bound_op;reg[31:0] bound_base;
 reg[11:0] bound_pc;reg[1:0] bound_query;reg[23:0] bound_session;
 reg[1:0] settle;
 `ifdef OT_HBM_PUBLICATION_MUT_QID
 wire[1:0] qid=0;
`else
 wire[1:0] qid=sector[8:7];
`endif
 wire[31:0] address=(bound_base+{20'b0,sector,3'b0})<<2;
 wire[15:0] tag={qid,tagseq[qid]};
 wire[272:0] response=rsp[273*qid+:273];
 wire matched=response[272:257]==expected && !response[256];
 wire take_rsp=pending && rsp_valid[qid] && rsp_ready[qid];
 wire write_sector=take_rsp && matched && state==RESPONSE && !warm_abort && !service_fault && !bad;
 wire header_same=owner==bound_owner && operation==bound_op && pc==bound_pc &&
 query_slot==bound_query && base_word==bound_base && session==bound_session;
 assign start_ready=state==IDLE && service_quiet && !bad && !service_fault && !warm_abort;
 assign read_pending=|read_pipe;
 assign published_frame={bound_owner,bound_op,bound_pc,bound_query,bound_session};
 assign published=state==PUBLISHED && !bad && !service_fault && !warm_abort;
 assign quiet=state==IDLE && !pending;
 assign fault=bad || service_fault;
 for(genvar q=0;q<4;q=q+1)begin:g_service
 assign req_valid[q]=state==REQUEST && qid==q && !bad && !service_fault && !warm_abort;
 assign req[337*q+:337]={1'b0,address,256'b0,32'hffffffff,tag};
 assign rsp_ready[q]=pending && qid==q;
 end
 wire[1:0] read_bad;
 reg[4:0] read_pipe;
 wire read_busy=|read_pipe || (published && |inj_rd);
 for(genvar i=0;i<2;i=i+1)begin:g_injector
 wire[15:0] idx=inj_idx[16*i+:16];wire fetch=published && inj_rd[i] && idx<256;
 wire[1:0] valid,ce,ue;wire[511:0] data;
 for(genvar h=0;h<2;h=h+1)begin:g_sector
 localparam HALF=h;
 ot_hbm_replay_sram #(.W(256),.SW(12),.EW(24),.DEPTH(256)) u_store(
 .clk(clk),.rst_n(rst_n),.w_valid(write_sector && sector[0]==HALF),.w_data(response[255:0]),
 .w_seq({4'b0,sector[8:1]}),.w_session(bound_session),
 .r_valid(fetch),.r_seq(idx[11:0]),.r_session(bound_session),
 .o_valid(valid[HALF]),.o_data(data[256*HALF+:256]),.o_seq(),.o_session(),.o_ce(ce[HALF]),.o_ue(ue[HALF]));
 end
 assign read_bad[i]=|ue || (published && inj_rd[i] && idx>=256);
 assign inj_valid[i]=&valid && !fault && !warm_abort && state==PUBLISHED && !(|ue);
 assign inj_data[512*i+:512]=data;
 end
 always@(posedge clk or negedge rst_n)begin
 if(!rst_n)begin
 state<=IDLE;bad<=0;pending<=0;sector<=0;settle<=0;expected<=0;
 read_pipe<=0;bound_owner<=0;bound_op<=0;bound_base<=0;bound_pc<=0;bound_query<=0;bound_session<=0;
 for(integer q=0;q<4;q=q+1)tagseq[q]<=0;
 end else begin
 read_pipe<={read_pipe[3:0],published && |inj_rd};
 if(service_fault || |read_bad)bad<=1;
 if(state!=IDLE && state!=ABORT && !header_same && !warm_abort)bad<=1;
 for(integer q=0;q<4;q=q+1)
 if(rsp_valid[q] && (!pending || qid!=q))bad<=1;
 if(start_valid && !start_ready)bad<=1;
 if(warm_abort)state<=ABORT;
 else if(!bad && !service_fault)case(state)
 IDLE:if(start_valid && start_ready)begin
 bound_owner<=owner;bound_op<=operation;bound_pc<=pc;bound_query<=query_slot;
 bound_base<=base_word;bound_session<=session;sector<=0;state<=REQUEST;
 // Base+4096 words must fit the actual32-bit byte-address ABI.
 if(base_word>32'd258048 || base_word[2:0]!=0)bad<=1;
 end
 REQUEST:if(req_valid[qid] && req_ready[qid])begin
 pending<=1;expected<=tag;tagseq[qid]<=tagseq[qid]+1'b1;state<=RESPONSE;end
 RESPONSE:if(take_rsp)begin
 pending<=0;
 if(!matched)bad<=1;
 else if(sector==511)begin settle<=0;state<=SETTLE;end
 else begin sector<=sector+1'b1;state<=REQUEST;end
 end
 SETTLE:if(settle==1)state<=PUBLISHED;else settle<=settle+1'b1;
 PUBLISHED:if(release_lease)begin if(read_busy)bad<=1;else state<=IDLE;end
 ABORT:begin
 if(take_rsp)begin pending<=0;if(!matched)bad<=1;end
 if(service_quiet && !pending)state<=IDLE;
 end
 endcase
 // An abort must still drain the one held response; transaction counters
 // survive warm abort. Parent service_quiet forbids stale replies at restart.
 if(warm_abort && take_rsp)begin pending<=0;if(!matched)bad<=1;end
 end end
 end else begin:g_off
 assign start_ready=0;assign req_valid=0;assign req=0;assign rsp_ready=0;
 assign read_pending=0;assign published_frame=0;assign published=0;assign quiet=1;assign fault=0;assign inj_valid=0;assign inj_data=0;
 end endgenerate
endmodule
