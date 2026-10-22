`default_nettype none
// Real finite holding banks. Local decoder boundaries survive mapping so a
// dynamic predicate never fans through every payload feedback mux at once.
module dsdv_hostb_hold_enable #(parameter integer ID=0)(input wire sample,permit,output wire en);
 assign en=sample&&permit;
endmodule
module dsdv_hostb_header_enable #(parameter integer ID=0,LOCAL_ONLY=0)(
 input wire hv,pending,host0,match,output wire en);
 assign en=hv&&!pending&&host0&&(!LOCAL_ONLY||match);
endmodule
module dsdv_hostb_header_address #(parameter integer ID=0)(
 input wire [7:0] stage_id,local_stage,input wire [1:0] rank_id,local_rank,output wire match);
 assign match=stage_id==local_stage&&rank_id==local_rank;
endmodule
module dsdv_hostb_hold_bits #(parameter integer ID=0,W=12)(input wire ck,en,input wire [W-1:0] d,output reg [W-1:0] q);
 always @(posedge ck)if(en)q<=d;
endmodule
module dsdv_hostb_header_bank #(parameter integer ID=0,W=12,LOCAL_ONLY=0)(
 input wire ck,hv,pending,host0,input wire [7:0] stage_id,local_stage,
 input wire [1:0] rank_id,local_rank,input wire [W-1:0] local_d,transit_d,output wire [W-1:0] q);
 wire match,en;wire [W-1:0] d=LOCAL_ONLY?local_d:(match?local_d:transit_d);
 (* keep_hierarchy="yes" *) dsdv_hostb_header_address #(.ID(ID)) u_addr(.stage_id(stage_id),.local_stage(local_stage),.rank_id(rank_id),.local_rank(local_rank),.match(match));
 (* keep_hierarchy="yes" *) dsdv_hostb_header_enable #(.ID(ID),.LOCAL_ONLY(LOCAL_ONLY)) u_en(.hv(hv),.pending(pending),.host0(host0),.match(match),.en(en));
 (* keep_hierarchy="yes" *) dsdv_hostb_hold_bits #(.ID(ID),.W(W)) u_bits(.ck(ck),.en(en),.d(d),.q(q));
endmodule
module dsdv_hostb_return_bank #(parameter integer ID=0,W=15)(
 input wire ck,sample,permit,input wire [W-1:0] d,output wire [W-1:0] q);
 wire en;
 (* keep_hierarchy="yes" *) dsdv_hostb_hold_enable #(.ID(ID)) u_en(.sample(sample),.permit(permit),.en(en));
 (* keep_hierarchy="yes" *) dsdv_hostb_hold_bits #(.ID(ID),.W(W)) u_bits(.ck(ck),.en(en),.d(d),.q(q));
endmodule
`default_nettype wire
