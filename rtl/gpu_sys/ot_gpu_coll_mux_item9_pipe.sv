`timescale 1ns/1ps
// Additive successor: PIPE=0 delegates byte-identical TREE source.
// PIPE=1 reserves one owner, captures local four-leaf banks, then holds a
// registered root transaction until downstream accepts. Source credit is
// returned at bank capture, never before payload/descriptor are stored.
module ot_gpu_coll_mux_item9_pipe #(
 parameter integer ENABLE=0, NSM=32, NL=128, ODUP=64, TREE=0, PIPE=0
)(
 input wire clk,rst_n,
 input wire [NSM-1:0] s_req_v, output wire [NSM-1:0] s_req_rdy,
 input wire [NSM-1:0] s_mode, input wire [NSM*8-1:0] s_count,
 input wire [NSM*NL*32-1:0] s_data,
 output wire [NSM-1:0] s_rsp_v, input wire [NSM-1:0] s_rsp_rdy,
 output wire [NL*32-1:0] s_rsp_data,
 output wire m_req_v, input wire m_req_rdy,
 output wire m_mode, output wire [7:0] m_count, output wire [NL*32-1:0] m_data,
 input wire m_rsp_v, output wire m_rsp_rdy, input wire [NL*32-1:0] m_rsp_data
);
generate if(PIPE==0)begin:g_original
 ot_gpu_coll_mux_item9_tree #(.ENABLE(ENABLE),.NSM(NSM),.NL(NL),.ODUP(ODUP),.TREE(TREE)) u_original(.*);
end else if(ENABLE==0)begin:g_off
 assign s_req_rdy='0;assign s_rsp_v='0;assign s_rsp_data='0;
 assign m_req_v=0;assign m_mode=0;assign m_count=0;assign m_data='0;assign m_rsp_rdy=0;
end else begin:g_on
 localparam integer W=NL*32, SB=(NSM>1)?$clog2(NSM):1, NB=(NSM+3)/4;
 localparam [2:0] IDLE=0,CAPTURE=1,JOIN=2,SEND=3,RESPONSE=4;
 reg[2:0] state;
 reg[SB-1:0] owner;
 reg any;reg[SB-1:0] pick;
 always @* begin
  any=0;pick=0;
  for(integer s=NSM-1;s>=0;s=s-1)if(s_req_v[s])begin any=1;pick=SB'(s);end
 end
 wire capture=(state==CAPTURE)&&s_req_v[owner];
 // Unreset payload is safe only after CAPTURE and JOIN. Reset clears validity.
 (* keep = 1 *) reg[W-1:0] bank_data[0:NB-1];
 reg[W-1:0] held_data;
 reg held_mode;reg[7:0] held_count;
 for(genvar b=0;b<NB;b=b+1)begin:g_bank
  for(genvar d=0;d<ODUP;d=d+1)begin:g_slice
   localparam integer LO=d*((W+ODUP-1)/ODUP);
   localparam integer HI=((d+1)*((W+ODUP-1)/ODUP)>W)?W:(d+1)*((W+ODUP-1)/ODUP);
   if(LO<W)begin:g_valid
    wire[SB-1:0] local_owner;
    ot_gpu_kreg_oh #(.W(SB),.RV(0)) u_owner(.clk(clk),.rst_n(rst_n),
      .d(state==IDLE&&any?pick:owner),.q(local_owner));
    wire[HI-LO-1:0] leaf[0:3];
    for(genvar k=0;k<4;k=k+1)begin:g_leaf
     if(b*4+k<NSM)begin:g_present
      assign leaf[k]=s_data[(b*4+k)*W+LO+:HI-LO]&{(HI-LO){local_owner==SB'(b*4+k)}};
     end else begin:g_pad
      assign leaf[k]='0;
     end
    end
    always @(posedge clk)bank_data[b][LO+:HI-LO]<=(leaf[0]|leaf[1])|(leaf[2]|leaf[3]);
   end
  end
 end
 reg[W-1:0] joined;
 always @* begin
  joined='0;
  for(integer b=0;b<NB;b=b+1)joined=joined|bank_data[b];
 end
 always @(posedge clk)begin
  if(capture)begin held_mode<=s_mode[owner];held_count<=s_count[owner*8+:8];end

 end
 for(genvar d=0;d<ODUP;d=d+1)begin:g_root_capture
  localparam integer LO=d*((W+ODUP-1)/ODUP);
  localparam integer HI=((d+1)*((W+ODUP-1)/ODUP)>W)?W:(d+1)*((W+ODUP-1)/ODUP);
  if(LO<W)begin:g_valid
   wire join_local;
   ot_gpu_kreg_oh #(.W(1),.RV(0)) u_join(.clk(clk),.rst_n(rst_n),.d(capture),.q(join_local));
   always @(posedge clk)if(join_local)held_data[LO+:HI-LO]<=joined[LO+:HI-LO];
  end
 end
 assign m_req_v=state==SEND;assign m_data=held_data;
 assign m_mode=held_mode;assign m_count=held_count;
 for(genvar s=0;s<NSM;s=s+1)begin:g_caller
  assign s_req_rdy[s]=capture&&(owner==SB'(s));
  assign s_rsp_v[s]=(state==RESPONSE)&&(owner==SB'(s))&&m_rsp_v;
 end
 assign s_rsp_data=m_rsp_data;
 assign m_rsp_rdy=(state==RESPONSE)&&s_rsp_rdy[owner];
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;owner<=0;end
  else case(state)
   IDLE:if(any)begin owner<=pick;state<=CAPTURE;end
   CAPTURE:if(capture)state<=JOIN;else state<=IDLE;
   JOIN:state<=SEND;
   SEND:if(m_req_rdy)state<=RESPONSE;
   RESPONSE:if(m_rsp_v&&m_rsp_rdy)state<=IDLE;
   default:state<=IDLE;
  endcase
 end
end endgenerate
endmodule
