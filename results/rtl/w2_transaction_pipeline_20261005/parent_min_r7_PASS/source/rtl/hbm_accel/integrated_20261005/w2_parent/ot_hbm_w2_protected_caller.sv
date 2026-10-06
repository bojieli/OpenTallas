`timescale 1ns/1ps
// Same NC8/RMAX256/PIO2 three-edge output topology and NCTX11 identity FIFO.
// Mutable payload, valid, status, identity and counters have one W6 backing.
// No callback ready is invented. If an arriving readyless row cannot be held
// during a protection repair, fail closed and retain the accepted transaction.
module ot_hbm_w2_protected_caller(
 input wire clk,rst_n,producer_cv,producer_fault,
 input wire [7:0] producer_crow,input wire [255:0] producer_cy,
 input wire producer_busy,producer_arrive,producer_released,
 input wire caller_start,caller_sm_ready,caller_pair,caller_bound,
 input wire [8:0] caller_rows,input wire [31:0] caller_op_a,caller_op_b,
 output wire ctx_ready,rv,output wire [7:0] rrow,output wire [31:0] rop,
 output wire [255:0] rdata,output wire busy,arrive,released,fault,quiet
);
 wire [319:0] stage[0:2];wire [2:0] stage_normal,stage_fault;
 wire [895:0] identity;wire id_normal,id_fault;
 wire normal=(&stage_normal)&&id_normal;
 // Extra bits retain the source sticky producer fault; all three stages hold
 // atomically when any protected representation is undergoing correction.
 wire [271:0] ingress={1'b0,producer_cv,producer_fault,producer_busy,producer_arrive,producer_released,(producer_cv?producer_crow:8'b0),(producer_cv?producer_cy:256'b0),2'b0};
 // All source bits except the producer fault are independently priced. The
 // sticky identity fault below preserves an upstream fault across the pipe.
 for(genvar g=0;g<3;g=g+1)begin:output_stage
  wire [319:0] d=g==0?{48'b0,ingress}:stage[g-1];
  ot_hbm_w2_protected_bank #(.WORDS(5)) u_state(
   .clk(clk),.por_n(rst_n),.load(normal),.load_encoded(1'b0),
   .fatal(!normal&&producer_cv),.d(d),.encoded_d(360'b0),.q(stage[g]),
   .encoded_q(),.normal(stage_normal[g]),.fault(stage_fault[g]),.repairing());
 end
 wire sm_rv=stage[2][270],sm_fault=stage[2][269];
 wire [7:0] sm_row=stage[2][265:258];
 assign rdata=stage[2][257:2];
 assign busy=!normal||stage[1][268];
 assign arrive=normal&&stage[1][267];
 assign released=normal&&stage[1][266];
 wire [31:0] qa[0:10],qb[0:10];wire [8:0] qr[0:10];wire [10:0] qp,qbnd;
 for(genvar g=0;g<11;g=g+1)begin:context_row
  assign {qa[g],qb[g],qr[g],qp[g],qbnd[g]}=identity[g*75+:75];
 end
 wire [3:0] wp=identity[828:825],rp=identity[832:829],cnt=identity[836:833];
 wire [8:0] next_row=identity[845:837];
 // 825 context bits +4wp+4rp+4cnt+9row+4seen+1failed =851.
 wire [3:0] seen=identity[849:846];wire failed=identity[850];
 wire config_ok=caller_bound&&caller_rows!=0&&(!caller_pair||caller_rows==4);
 assign ctx_ready=normal&&cnt<11&&config_ok&&!failed;
 wire push=caller_start&&caller_sm_ready&&ctx_ready;
 wire have=cnt!=0;wire pair=have&&qp[rp];
 wire good=have&&qbnd[rp]&&{1'b0,sm_row}<qr[rp]&&{1'b0,sm_row}==next_row&&
           (!pair||(sm_row<4&&!seen[sm_row[1:0]]))&&!failed;
 assign rv=normal&&sm_rv&&good;
 assign rrow=pair&&sm_row>=2?sm_row-2:sm_row;
 assign rop=pair&&sm_row>=2?qb[rp]:qa[rp];
 wire last=rv&&next_row+1'b1==qr[rp];
 reg [895:0] next_identity;
 always @*begin
  next_identity=identity;
  if((caller_start&&caller_sm_ready&&!config_ok)||(sm_rv&&!good)||sm_fault||producer_fault)next_identity[850]=1;
  case({push,last})
   2'b10:next_identity[836:833]=cnt+1'b1;
   2'b01:next_identity[836:833]=cnt-1'b1;
   default:;
  endcase
  if(push)begin
   next_identity[wp*75+:75]={caller_op_a,caller_op_b,caller_rows,caller_pair,caller_bound};
   next_identity[828:825]=wp==10?0:wp+1'b1;
  end
  if(last)begin next_identity[832:829]=rp==10?0:rp+1'b1;next_identity[845:837]=0;next_identity[849:846]=0;end
  else if(rv)begin next_identity[845:837]=next_row+1'b1;if(pair)next_identity[846+sm_row[1:0]]=1;end
 end
 ot_hbm_w2_protected_bank #(.WORDS(14)) u_identity(
  .clk(clk),.por_n(rst_n),.load(normal),.load_encoded(1'b0),.fatal(!normal&&producer_cv),
  .d(next_identity),.encoded_d(1008'b0),.q(identity),.encoded_q(),.normal(id_normal),.fault(id_fault),.repairing());
 assign quiet=normal&&cnt==0&&!stage[0][270]&&!stage[1][270]&&!stage[2][270]&&!busy&&!arrive;
 assign fault=(|stage_fault)||id_fault||failed||(normal&&sm_rv&&!good);
endmodule
