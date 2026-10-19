`timescale 1ns/1ps
// Production K bridge: source is the actual ECTL A STATIC_QK scan, never a ready/credit merge.
// One edge rq -> req and one edge rsp -> rs. RESPONSE_LAT is the implemented
// req-pin to rsp-pin latency (edge distance), supplied by the physical calendar.
// Metadata/valid comparison only sets fault. It never gates or moves an event.
module qkd_static_k_issuer #(parameter integer RESPONSE_LAT=0, parameter integer MUT=0)(
 input wire ck,rst_n,
 input wire kgo,input wire [15:0] epoch,input wire [5:0] layer,
 input wire [16:0] rq,
 output reg req_valid,output reg [13:0] req_t,output wire req_v,
 output reg [15:0] req_epoch,output reg [5:0] req_layer,
 input wire rsp_valid,input wire [1023:0] rsp_data,input wire [13:0] rsp_t,
 input wire rsp_v,input wire [15:0] rsp_epoch,input wire [5:0] rsp_layer,
 output reg [1024:0] rs,output reg fault
);
 initial if(RESPONSE_LAT<1) $fatal(1,"RESPONSE_LAT requires measured positive edge latency");
 (* keep *) reg rn;
 always @(posedge ck) rn<=rst_n;
 reg go_q;reg [15:0] ep_q,ep;reg [5:0] ly_q,ly;reg active;
 always @(posedge ck)begin ep_q<=epoch;ly_q<=layer;end
 always @(posedge ck or negedge rn)
  if(!rn)begin go_q<=0;active<=0;ep<=0;ly<=0;end
  else begin go_q<=kgo;if(go_q)begin active<=1;ep<=ep_q;ly<=ly_q;end end
 assign req_v=1'b0;
 // Each boundary port terminates at a flop. Data is always the real response.
 always @(posedge ck) begin
  req_t<={1'b0,rq[15:3]};req_epoch<=ep;req_layer<=(MUT==1)?(ly^6'd1):ly;
  rs[1024:1]<=(MUT==2)?(rsp_data^1024'd1):rsp_data;
 end
 always @(posedge ck or negedge rn)
  if(!rn)begin req_valid<=0;rs[0]<=0;end
  else begin req_valid<=rq[0];rs[0]<=rsp_valid&&!rsp_v;end
 // At edge c+L compare response to request sampled at edge c.  The peer's
 // registered response becomes visible before its next sampling edge.
 reg [RESPONSE_LAT:0] ev;
 reg [35:0] ident[0:RESPONSE_LAT];
 reg [35:0] returned;reg rv_q,vv_q;
 integer j;
 always @(posedge ck)begin
  returned<={rsp_epoch,rsp_layer,rsp_t};
  ident[0]<={req_epoch,req_layer,req_t};
  for(j=1;j<=RESPONSE_LAT;j=j+1)ident[j]<=ident[j-1];
 end
 // The landing return is shared with the V port. Legal V responses belong
 // to that consumer; a V response at a reserved K edge still faults missing K.
 // Request qualifiers captured before diagnostics so their logic is local.
 reg bad_rq;
 always @(posedge ck or negedge rn)
  if(!rn)begin ev<=0;bad_rq<=0;fault<=0;rv_q<=0;vv_q<=0;end
  else begin
   ev<=(ev<<1)|req_valid;rv_q<=rsp_valid;vv_q<=rsp_v;
   bad_rq<=rq[0]&&(!active||rq[2:1]!=0||rq[16]!=ly[0]);
   if(bad_rq || (go_q&&((|ev)||req_valid||rq[0])) || (rv_q&&!vv_q)!=ev[RESPONSE_LAT] ||
      (rv_q&&!vv_q&&returned!=ident[RESPONSE_LAT]))fault<=1;
  end
endmodule
