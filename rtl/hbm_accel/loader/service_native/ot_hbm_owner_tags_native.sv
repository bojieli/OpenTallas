`default_nettype none
(* keep_hierarchy = "yes" *)
module ot_hbm_owner_tags_first_reset(input wire clk,rst_n,output reg q);
 always @(posedge clk or negedge rst_n)if(!rst_n)q<=0;else q<=1;
endmodule

(* keep_hierarchy = "yes" *)
module ot_hbm_owner_tag_entry #(parameter integer J=0,MUT=0)(
 input wire clk,first_rst_n,alloc_v,input wire [16:0] alloc_tag,input wire [2:0] alloc_len,
 input wire return_v,input wire [16:0] return_tag,input wire [3:0] return_beat,input wire stop,
 output reg accepted,output reg live,output reg fault
);
 reg rst_q;always @(posedge clk or negedge first_rst_n)if(!first_rst_n)rst_q<=0;else rst_q<=1;
 (* keep = "yes" *) reg [16:0] at_q,rt_q;
 reg [2:0] al_q;reg [3:0] beat_q;reg av_q,rv_q,stop_q;
 reg [11:0] generation;reg [2:0] length;reg [3:0] seen;
 always @(posedge clk)begin at_q<=alloc_tag;rt_q<=return_tag;al_q<=alloc_len;beat_q<=return_beat;end
 wire alloc_here=av_q&&at_q[4:0]==5'(J);
 wire return_here=rv_q&&rt_q[4:0]==5'(J);
 wire [3:0] mask=(length==4)?4'hf:4'h1;
 wire legal=live&&((generation==rt_q[16:5])||(MUT==1))&&beat_q<length&&beat_q<4&&
             ((!seen[beat_q[1:0]])||(MUT==2))&&!fault&&!stop_q;
 always @(posedge clk or negedge rst_q)
  if(!rst_q)begin av_q<=0;rv_q<=0;stop_q<=0;accepted<=0;live<=0;fault<=0;end
  else begin
   av_q<=alloc_v;rv_q<=return_v;stop_q<=stop;accepted<=0;
   if(alloc_here)begin
    if(live||(al_q!=1&&al_q!=4)||fault||stop_q)fault<=1;
    else begin live<=1;generation<=at_q[16:5];length<=al_q;seen<=0;end
   end
   if(return_here)begin
    if(!legal||alloc_here)fault<=1;
    else begin accepted<=1;seen<=seen|(4'b1<<beat_q[1:0]);
     if((seen|(4'b1<<beat_q[1:0]))==mask)live<=0;
    end
   end
  end
endmodule

module ot_hbm_owner_tags_native #(parameter integer MUT=0)(
 input wire clk,rst_n,alloc_v,input wire [16:0] alloc_tag,input wire [2:0] alloc_len,
 input wire return_v,input wire [16:0] return_tag,input wire [3:0] return_beat,input wire stop,
 output wire [31:0] accepted_entry,live,output reg response_ok,output reg fault
);
 wire [1:0] first_rst;wire [31:0] entry_fault;
 for(genvar b=0;b<2;b=b+1)begin:g_first
  ot_hbm_owner_tags_first_reset u_first(.clk(clk),.rst_n(rst_n),.q(first_rst[b]));
 end
 for(genvar j=0;j<32;j=j+1)begin:g_entry
  ot_hbm_owner_tag_entry #(.J(j),.MUT(MUT)) u_entry(.clk(clk),.first_rst_n(first_rst[j/16]),
   .alloc_v(alloc_v),.alloc_tag(alloc_tag),.alloc_len(alloc_len),.return_v(return_v),
   .return_tag(return_tag),.return_beat(return_beat),.stop(stop),
   .accepted(accepted_entry[j]),.live(live[j]),.fault(entry_fault[j]));
 end
 reg ctrl_rst;always @(posedge clk or negedge first_rst[0])if(!first_rst[0])ctrl_rst<=0;else ctrl_rst<=1;
 always @(posedge clk or negedge ctrl_rst)
  if(!ctrl_rst)begin response_ok<=0;fault<=0;end
  else begin response_ok<=|accepted_entry;fault<=|entry_fault;end
endmodule
`default_nettype wire
