// Opt-in C4 component transport candidate; no die binding or source adoption.
// ENABLE defaults0. Qualified candidate: ENABLE1, MEALY_COMP1, MUT_BYPASS0.
// Five ingress registers on the pure service passthrough port align its after-edge
// trace with the four-ingress/two-egress sequential paths at exactly six cycles.
// MEALY_COMP0 and MUT_BYPASS1 are negative-control configurations only.
module qkd_kvs_emb_transport #(parameter integer ENABLE=0, parameter integer MUT_BYPASS=0, parameter integer MEALY_COMP=1) (input wire ck,input wire rst_n,
 input wire [173:0] d2d__svc,
 input wire [0:0] d2d__emb_tx_slot,
 output wire [0:0] rowtx__emb_tx_v,
 output wire [547:0] rowtx__emb_tx_payload,
 output wire [17:0] px_tok,
 output wire [15:0] px_tep,
 input wire [72:0] i_ctl,
 input wire [298:0] i_hroot_WS,
 input wire [298:0] i_hroot_WN,
 input wire [298:0] i_hroot_ES,
 input wire [298:0] i_hroot_EN,
 input wire [551:0] i_head_record,
 output wire [173:0] o_ctx_svc,
 output wire [0:0] emb_fault);
generate if(!ENABLE)begin:g_off
qkd_kvs_emb_rope u_core(.ck(ck),.rst_n(rst_n),.d2d__svc(d2d__svc),.d2d__emb_tx_slot(d2d__emb_tx_slot),.rowtx__emb_tx_v(rowtx__emb_tx_v),.rowtx__emb_tx_payload(rowtx__emb_tx_payload),.px_tok(px_tok),.px_tep(px_tep),.i_ctl(i_ctl),.i_hroot_WS(i_hroot_WS),.i_hroot_WN(i_hroot_WN),.i_hroot_ES(i_hroot_ES),.i_hroot_EN(i_hroot_EN),.i_head_record(i_head_record),.o_ctx_svc(o_ctx_svc),.emb_fault(emb_fault));
end else begin:g_on
localparam integer N_d2d__svc=(4+MEALY_COMP);
(* keep=1,dont_touch=1 *) reg [173:0] p_d2d__svc[0:N_d2d__svc-1];
(* keep=1,dont_touch=1 *) reg [N_d2d__svc-1:0] e_d2d__svc;
wire [173:0] c_d2d__svc;
always@(posedge ck or negedge rst_n)if(!rst_n)e_d2d__svc<=0;else e_d2d__svc<=((e_d2d__svc<<1)|1'b1);
always@(posedge ck)begin p_d2d__svc[0]<=d2d__svc;for(integer i=1;i<N_d2d__svc;i=i+1)p_d2d__svc[i]<=p_d2d__svc[i-1];end
assign c_d2d__svc=p_d2d__svc[N_d2d__svc-1];
localparam integer N_d2d__emb_tx_slot=4;
(* keep=1,dont_touch=1 *) reg [0:0] p_d2d__emb_tx_slot[0:N_d2d__emb_tx_slot-1];
(* keep=1,dont_touch=1 *) reg [N_d2d__emb_tx_slot-1:0] e_d2d__emb_tx_slot;
wire [0:0] c_d2d__emb_tx_slot;
always@(posedge ck or negedge rst_n)if(!rst_n)e_d2d__emb_tx_slot<=0;else e_d2d__emb_tx_slot<=((e_d2d__emb_tx_slot<<1)|1'b1);
always@(posedge ck)begin p_d2d__emb_tx_slot[0]<=d2d__emb_tx_slot;for(integer i=1;i<N_d2d__emb_tx_slot;i=i+1)p_d2d__emb_tx_slot[i]<=p_d2d__emb_tx_slot[i-1];end
assign c_d2d__emb_tx_slot=p_d2d__emb_tx_slot[N_d2d__emb_tx_slot-1];
localparam integer N_rowtx__emb_tx_v=(MUT_BYPASS?1:2);
(* keep=1,dont_touch=1 *) reg [0:0] p_rowtx__emb_tx_v[0:N_rowtx__emb_tx_v-1];
(* keep=1,dont_touch=1 *) reg [N_rowtx__emb_tx_v-1:0] e_rowtx__emb_tx_v;
wire [0:0] c_rowtx__emb_tx_v;
always@(posedge ck or negedge rst_n)if(!rst_n)e_rowtx__emb_tx_v<=0;else e_rowtx__emb_tx_v<=((e_rowtx__emb_tx_v<<1)|1'b1);
always@(posedge ck)begin p_rowtx__emb_tx_v[0]<=c_rowtx__emb_tx_v;for(integer i=1;i<N_rowtx__emb_tx_v;i=i+1)p_rowtx__emb_tx_v[i]<=p_rowtx__emb_tx_v[i-1];end
assign rowtx__emb_tx_v=p_rowtx__emb_tx_v[N_rowtx__emb_tx_v-1] & {1{out_live}};
localparam integer N_rowtx__emb_tx_payload=(MUT_BYPASS?1:2);
(* keep=1,dont_touch=1 *) reg [547:0] p_rowtx__emb_tx_payload[0:N_rowtx__emb_tx_payload-1];
(* keep=1,dont_touch=1 *) reg [N_rowtx__emb_tx_payload-1:0] e_rowtx__emb_tx_payload;
wire [547:0] c_rowtx__emb_tx_payload;
always@(posedge ck or negedge rst_n)if(!rst_n)e_rowtx__emb_tx_payload<=0;else e_rowtx__emb_tx_payload<=((e_rowtx__emb_tx_payload<<1)|1'b1);
always@(posedge ck)begin p_rowtx__emb_tx_payload[0]<=c_rowtx__emb_tx_payload;for(integer i=1;i<N_rowtx__emb_tx_payload;i=i+1)p_rowtx__emb_tx_payload[i]<=p_rowtx__emb_tx_payload[i-1];end
assign rowtx__emb_tx_payload=p_rowtx__emb_tx_payload[N_rowtx__emb_tx_payload-1];
localparam integer N_px_tok=(MUT_BYPASS?1:2);
(* keep=1,dont_touch=1 *) reg [17:0] p_px_tok[0:N_px_tok-1];
(* keep=1,dont_touch=1 *) reg [N_px_tok-1:0] e_px_tok;
wire [17:0] c_px_tok;
always@(posedge ck or negedge rst_n)if(!rst_n)e_px_tok<=0;else e_px_tok<=((e_px_tok<<1)|1'b1);
always@(posedge ck)begin p_px_tok[0]<=c_px_tok;for(integer i=1;i<N_px_tok;i=i+1)p_px_tok[i]<=p_px_tok[i-1];end
assign px_tok=p_px_tok[N_px_tok-1];
localparam integer N_px_tep=(MUT_BYPASS?1:2);
(* keep=1,dont_touch=1 *) reg [15:0] p_px_tep[0:N_px_tep-1];
(* keep=1,dont_touch=1 *) reg [N_px_tep-1:0] e_px_tep;
wire [15:0] c_px_tep;
always@(posedge ck or negedge rst_n)if(!rst_n)e_px_tep<=0;else e_px_tep<=((e_px_tep<<1)|1'b1);
always@(posedge ck)begin p_px_tep[0]<=c_px_tep;for(integer i=1;i<N_px_tep;i=i+1)p_px_tep[i]<=p_px_tep[i-1];end
assign px_tep=p_px_tep[N_px_tep-1];
localparam integer N_i_ctl=4;
(* keep=1,dont_touch=1 *) reg [72:0] p_i_ctl[0:N_i_ctl-1];
(* keep=1,dont_touch=1 *) reg [N_i_ctl-1:0] e_i_ctl;
wire [72:0] c_i_ctl;
always@(posedge ck or negedge rst_n)if(!rst_n)e_i_ctl<=0;else e_i_ctl<=((e_i_ctl<<1)|1'b1);
always@(posedge ck)begin p_i_ctl[0]<=i_ctl;for(integer i=1;i<N_i_ctl;i=i+1)p_i_ctl[i]<=p_i_ctl[i-1];end
assign c_i_ctl=p_i_ctl[N_i_ctl-1];
localparam integer N_i_hroot_WS=4;
(* keep=1,dont_touch=1 *) reg [298:0] p_i_hroot_WS[0:N_i_hroot_WS-1];
(* keep=1,dont_touch=1 *) reg [N_i_hroot_WS-1:0] e_i_hroot_WS;
wire [298:0] c_i_hroot_WS;
always@(posedge ck or negedge rst_n)if(!rst_n)e_i_hroot_WS<=0;else e_i_hroot_WS<=((e_i_hroot_WS<<1)|1'b1);
always@(posedge ck)begin p_i_hroot_WS[0]<=i_hroot_WS;for(integer i=1;i<N_i_hroot_WS;i=i+1)p_i_hroot_WS[i]<=p_i_hroot_WS[i-1];end
assign c_i_hroot_WS=p_i_hroot_WS[N_i_hroot_WS-1];
localparam integer N_i_hroot_WN=4;
(* keep=1,dont_touch=1 *) reg [298:0] p_i_hroot_WN[0:N_i_hroot_WN-1];
(* keep=1,dont_touch=1 *) reg [N_i_hroot_WN-1:0] e_i_hroot_WN;
wire [298:0] c_i_hroot_WN;
always@(posedge ck or negedge rst_n)if(!rst_n)e_i_hroot_WN<=0;else e_i_hroot_WN<=((e_i_hroot_WN<<1)|1'b1);
always@(posedge ck)begin p_i_hroot_WN[0]<=i_hroot_WN;for(integer i=1;i<N_i_hroot_WN;i=i+1)p_i_hroot_WN[i]<=p_i_hroot_WN[i-1];end
assign c_i_hroot_WN=p_i_hroot_WN[N_i_hroot_WN-1];
localparam integer N_i_hroot_ES=4;
(* keep=1,dont_touch=1 *) reg [298:0] p_i_hroot_ES[0:N_i_hroot_ES-1];
(* keep=1,dont_touch=1 *) reg [N_i_hroot_ES-1:0] e_i_hroot_ES;
wire [298:0] c_i_hroot_ES;
always@(posedge ck or negedge rst_n)if(!rst_n)e_i_hroot_ES<=0;else e_i_hroot_ES<=((e_i_hroot_ES<<1)|1'b1);
always@(posedge ck)begin p_i_hroot_ES[0]<=i_hroot_ES;for(integer i=1;i<N_i_hroot_ES;i=i+1)p_i_hroot_ES[i]<=p_i_hroot_ES[i-1];end
assign c_i_hroot_ES=p_i_hroot_ES[N_i_hroot_ES-1];
localparam integer N_i_hroot_EN=4;
(* keep=1,dont_touch=1 *) reg [298:0] p_i_hroot_EN[0:N_i_hroot_EN-1];
(* keep=1,dont_touch=1 *) reg [N_i_hroot_EN-1:0] e_i_hroot_EN;
wire [298:0] c_i_hroot_EN;
always@(posedge ck or negedge rst_n)if(!rst_n)e_i_hroot_EN<=0;else e_i_hroot_EN<=((e_i_hroot_EN<<1)|1'b1);
always@(posedge ck)begin p_i_hroot_EN[0]<=i_hroot_EN;for(integer i=1;i<N_i_hroot_EN;i=i+1)p_i_hroot_EN[i]<=p_i_hroot_EN[i-1];end
assign c_i_hroot_EN=p_i_hroot_EN[N_i_hroot_EN-1];
localparam integer N_i_head_record=4;
(* keep=1,dont_touch=1 *) reg [551:0] p_i_head_record[0:N_i_head_record-1];
(* keep=1,dont_touch=1 *) reg [N_i_head_record-1:0] e_i_head_record;
wire [551:0] c_i_head_record;
always@(posedge ck or negedge rst_n)if(!rst_n)e_i_head_record<=0;else e_i_head_record<=((e_i_head_record<<1)|1'b1);
always@(posedge ck)begin p_i_head_record[0]<=i_head_record;for(integer i=1;i<N_i_head_record;i=i+1)p_i_head_record[i]<=p_i_head_record[i-1];end
assign c_i_head_record=p_i_head_record[N_i_head_record-1];
localparam integer N_o_ctx_svc=(MUT_BYPASS?1:2);
(* keep=1,dont_touch=1 *) reg [173:0] p_o_ctx_svc[0:N_o_ctx_svc-1];
(* keep=1,dont_touch=1 *) reg [N_o_ctx_svc-1:0] e_o_ctx_svc;
wire [173:0] c_o_ctx_svc;
always@(posedge ck or negedge rst_n)if(!rst_n)e_o_ctx_svc<=0;else e_o_ctx_svc<=((e_o_ctx_svc<<1)|1'b1);
always@(posedge ck)begin p_o_ctx_svc[0]<=c_o_ctx_svc;for(integer i=1;i<N_o_ctx_svc;i=i+1)p_o_ctx_svc[i]<=p_o_ctx_svc[i-1];end
assign o_ctx_svc=p_o_ctx_svc[N_o_ctx_svc-1];
localparam integer N_emb_fault=(MUT_BYPASS?1:2);
(* keep=1,dont_touch=1 *) reg [0:0] p_emb_fault[0:N_emb_fault-1];
(* keep=1,dont_touch=1 *) reg [N_emb_fault-1:0] e_emb_fault;
wire [0:0] c_emb_fault;
always@(posedge ck or negedge rst_n)if(!rst_n)e_emb_fault<=0;else e_emb_fault<=((e_emb_fault<<1)|1'b1);
always@(posedge ck)begin p_emb_fault[0]<=c_emb_fault;for(integer i=1;i<N_emb_fault;i=i+1)p_emb_fault[i]<=p_emb_fault[i-1];end
assign emb_fault=p_emb_fault[N_emb_fault-1];
wire core_rst_n=rst_n & e_d2d__emb_tx_slot[N_d2d__emb_tx_slot-1] & e_i_ctl[N_i_ctl-1] & e_i_hroot_WS[N_i_hroot_WS-1] & e_i_hroot_WN[N_i_hroot_WN-1] & e_i_hroot_ES[N_i_hroot_ES-1] & e_i_hroot_EN[N_i_hroot_EN-1] & e_i_head_record[N_i_head_record-1];
wire out_live=e_rowtx__emb_tx_v[N_rowtx__emb_tx_v-1] & e_rowtx__emb_tx_payload[N_rowtx__emb_tx_payload-1] & e_px_tok[N_px_tok-1] & e_px_tep[N_px_tep-1] & e_o_ctx_svc[N_o_ctx_svc-1] & e_emb_fault[N_emb_fault-1];
qkd_kvs_emb_rope u_core(.ck(ck),.rst_n(core_rst_n),.d2d__svc(c_d2d__svc),.d2d__emb_tx_slot(c_d2d__emb_tx_slot),.rowtx__emb_tx_v(c_rowtx__emb_tx_v),.rowtx__emb_tx_payload(c_rowtx__emb_tx_payload),.px_tok(c_px_tok),.px_tep(c_px_tep),.i_ctl(c_i_ctl),.i_hroot_WS(c_i_hroot_WS),.i_hroot_WN(c_i_hroot_WN),.i_hroot_ES(c_i_hroot_ES),.i_hroot_EN(c_i_hroot_EN),.i_head_record(c_i_head_record),.o_ctx_svc(c_o_ctx_svc),.emb_fault(c_emb_fault));
end endgenerate
endmodule
