`timescale 1ps/1fs
module tb_ring_face_bridge;
reg clk=0;always #416.5 clk=~clk;
reg rst_n=1;integer cycle=0,checks=0,known_ports=0,nonzero_ports=0;integer seed=32'h5ac931e7;
reg [279:0] pr_ccw_i=0;
reg [279:0] pr_cw_i=0;
reg [0:0] ra_add_rhs_acc=0;
reg [1:0] ra_add_src=0;
reg [2:0] ra_add_tag=0;
reg [0:0] ra_add_v=0;
reg [255:0] ra_lp_data=0;
reg [2:0] ra_lp_tag=0;
reg [0:0] ra_lp_we=0;
reg [0:0] ra_rr_local=0;
reg [2:0] ra_rr_local_tag=0;
reg [3:0] ra_rx_kind=0;
reg [1:0] ra_rx_slot=0;
reg [3:0] ra_rx_src=0;
reg [5:0] ra_rx_tag=0;
reg [0:0] ra_state_add_rhs_acc=0;
reg [1:0] ra_state_add_src=0;
reg [2:0] ra_state_add_tag=0;
reg [0:0] ra_state_read_add=0;
reg [0:0] ra_state_read_rr=0;
reg [0:0] ra_state_read_tx=0;
reg [2:0] ra_state_rr_tag=0;
reg [0:0] ra_state_tx_acc=0;
reg [2:0] ra_state_tx_tag=0;
reg [0:0] ra_tx_acc=0;
reg [1:0] ra_tx_dst=0;
reg [1:0] ra_tx_forward=0;
reg [0:0] ra_tx_gather=0;
reg [1:0] ra_tx_inject=0;
reg [0:0] ra_tx_result=0;
reg [2:0] ra_tx_tag=0;
reg [3:0] ra_tx_ttl=0;
genvar q;generate for(q=0;q<2;q=q+1)begin:g_q
localparam [1:0] QID=q+2;
wire [511:0] a_ag_d;
wire [511:0] b_ag_d;
wire [3:0] a_ag_src;
wire [3:0] b_ag_src;
wire [5:0] a_ag_tag;
wire [5:0] b_ag_tag;
wire [1:0] a_ag_v;
wire [1:0] b_ag_v;
wire [279:0] a_pr_ccw_o;
wire [279:0] b_pr_ccw_o;
wire [279:0] a_pr_cw_o;
wire [279:0] b_pr_cw_o;
wire [255:0] a_rr_d;
wire [255:0] b_rr_d;
wire [2:0] a_rr_tag;
wire [2:0] b_rr_tag;
wire [0:0] a_rr_v;
wire [0:0] b_rr_v;
wire [0:0] a_u_ring_fault;
wire [0:0] b_u_ring_fault;
physical_ot_hfd_coll_q2_hard_v8g__ring_ag u_a(.ag_d(a_ag_d),.ag_src(a_ag_src),.ag_tag(a_ag_tag),.ag_v(a_ag_v),.clk(clk),.pr_ccw_i(pr_ccw_i),.pr_ccw_o(a_pr_ccw_o),.pr_cw_i(pr_cw_i),.pr_cw_o(a_pr_cw_o),.ra_add_rhs_acc(ra_add_rhs_acc),.ra_add_src(ra_add_src),.ra_add_tag(ra_add_tag),.ra_add_v(ra_add_v),.ra_lp_data(ra_lp_data),.ra_lp_tag(ra_lp_tag),.ra_lp_we(ra_lp_we),.ra_rr_local(ra_rr_local),.ra_rr_local_tag(ra_rr_local_tag),.ra_rx_kind(ra_rx_kind),.ra_rx_slot(ra_rx_slot),.ra_rx_src(ra_rx_src),.ra_rx_tag(ra_rx_tag),.ra_state_add_rhs_acc(ra_state_add_rhs_acc),.ra_state_add_src(ra_state_add_src),.ra_state_add_tag(ra_state_add_tag),.ra_state_read_add(ra_state_read_add),.ra_state_read_rr(ra_state_read_rr),.ra_state_read_tx(ra_state_read_tx),.ra_state_rr_tag(ra_state_rr_tag),.ra_state_tx_acc(ra_state_tx_acc),.ra_state_tx_tag(ra_state_tx_tag),.ra_tx_acc(ra_tx_acc),.ra_tx_dst(ra_tx_dst),.ra_tx_forward(ra_tx_forward),.ra_tx_gather(ra_tx_gather),.ra_tx_inject(ra_tx_inject),.ra_tx_result(ra_tx_result),.ra_tx_tag(ra_tx_tag),.ra_tx_ttl(ra_tx_ttl),.rr_d(a_rr_d),.rr_tag(a_rr_tag),.rr_v(a_rr_v),.rst_n(rst_n),.u_ring_fault(a_u_ring_fault),.strap_qid(QID));
current_native_ring_face u_b(.ag_d(b_ag_d),.ag_src(b_ag_src),.ag_tag(b_ag_tag),.ag_v(b_ag_v),.clk(clk),.pr_ccw_i(pr_ccw_i),.pr_ccw_o(b_pr_ccw_o),.pr_cw_i(pr_cw_i),.pr_cw_o(b_pr_cw_o),.ra_add_rhs_acc(ra_add_rhs_acc),.ra_add_src(ra_add_src),.ra_add_tag(ra_add_tag),.ra_add_v(ra_add_v),.ra_lp_data(ra_lp_data),.ra_lp_tag(ra_lp_tag),.ra_lp_we(ra_lp_we),.ra_rr_local(ra_rr_local),.ra_rr_local_tag(ra_rr_local_tag),.ra_rx_kind(ra_rx_kind),.ra_rx_slot(ra_rx_slot),.ra_rx_src(ra_rx_src),.ra_rx_tag(ra_rx_tag),.ra_state_add_rhs_acc(ra_state_add_rhs_acc),.ra_state_add_src(ra_state_add_src),.ra_state_add_tag(ra_state_add_tag),.ra_state_read_add(ra_state_read_add),.ra_state_read_rr(ra_state_read_rr),.ra_state_read_tx(ra_state_read_tx),.ra_state_rr_tag(ra_state_rr_tag),.ra_state_tx_acc(ra_state_tx_acc),.ra_state_tx_tag(ra_state_tx_tag),.ra_tx_acc(ra_tx_acc),.ra_tx_dst(ra_tx_dst),.ra_tx_forward(ra_tx_forward),.ra_tx_gather(ra_tx_gather),.ra_tx_inject(ra_tx_inject),.ra_tx_result(ra_tx_result),.ra_tx_tag(ra_tx_tag),.ra_tx_ttl(ra_tx_ttl),.rr_d(b_rr_d),.rr_tag(b_rr_tag),.rr_v(b_rr_v),.rst_n(rst_n),.u_ring_fault(b_u_ring_fault),.strap_qid(QID));
always @(posedge clk) begin #1;
 if({a_ag_d,a_ag_src,a_ag_tag,a_ag_v,a_pr_ccw_o,a_pr_cw_o,a_rr_d,a_rr_tag,a_rr_v,a_u_ring_fault} !== {b_ag_d,b_ag_src,b_ag_tag,b_ag_v,b_pr_ccw_o,b_pr_cw_o,b_rr_d,b_rr_tag,b_rr_v,b_u_ring_fault}) begin $display("RING_FACE_DIFF cycle%0d qid%0d",cycle,QID);
 if(a_ag_d !== b_ag_d) $display("PORT ag_d A=%h B=%h",a_ag_d,b_ag_d);
 if(a_ag_src !== b_ag_src) $display("PORT ag_src A=%h B=%h",a_ag_src,b_ag_src);
 if(a_ag_tag !== b_ag_tag) $display("PORT ag_tag A=%h B=%h",a_ag_tag,b_ag_tag);
 if(a_ag_v !== b_ag_v) $display("PORT ag_v A=%h B=%h",a_ag_v,b_ag_v);
 if(a_pr_ccw_o !== b_pr_ccw_o) $display("PORT pr_ccw_o A=%h B=%h",a_pr_ccw_o,b_pr_ccw_o);
 if(a_pr_cw_o !== b_pr_cw_o) $display("PORT pr_cw_o A=%h B=%h",a_pr_cw_o,b_pr_cw_o);
 if(a_rr_d !== b_rr_d) $display("PORT rr_d A=%h B=%h",a_rr_d,b_rr_d);
 if(a_rr_tag !== b_rr_tag) $display("PORT rr_tag A=%h B=%h",a_rr_tag,b_rr_tag);
 if(a_rr_v !== b_rr_v) $display("PORT rr_v A=%h B=%h",a_rr_v,b_rr_v);
 if(a_u_ring_fault !== b_u_ring_fault) $display("PORT u_ring_fault A=%h B=%h",a_u_ring_fault,b_u_ring_fault);$fatal(1,"current-native face candidate differs from actual physical shell");end
end
end endgenerate
always @(negedge clk)begin
cycle=cycle+1;
 pr_ccw_i={$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
 pr_cw_i={$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
 ra_add_rhs_acc={$random(seed)};
 ra_add_src={$random(seed)};
 ra_add_tag={$random(seed)};
 ra_add_v={$random(seed)};
 ra_lp_data={$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
 ra_lp_tag={$random(seed)};
 ra_lp_we={$random(seed)};
 ra_rr_local={$random(seed)};
 ra_rr_local_tag={$random(seed)};
 ra_rx_kind={$random(seed)};
 ra_rx_slot={$random(seed)};
 ra_rx_src={$random(seed)};
 ra_rx_tag={$random(seed)};
 ra_state_add_rhs_acc={$random(seed)};
 ra_state_add_src={$random(seed)};
 ra_state_add_tag={$random(seed)};
 ra_state_read_add={$random(seed)};
 ra_state_read_rr={$random(seed)};
 ra_state_read_tx={$random(seed)};
 ra_state_rr_tag={$random(seed)};
 ra_state_tx_acc={$random(seed)};
 ra_state_tx_tag={$random(seed)};
 ra_tx_acc={$random(seed)};
 ra_tx_dst={$random(seed)};
 ra_tx_forward={$random(seed)};
 ra_tx_gather={$random(seed)};
 ra_tx_inject={$random(seed)};
 ra_tx_result={$random(seed)};
 ra_tx_tag={$random(seed)};
 ra_tx_ttl={$random(seed)};
if(cycle==66||cycle==310||cycle==755)rst_n=1;
if(cycle==244||cycle==689)rst_n=0;
if(cycle%29==0)begin ra_lp_data[7:0]=8'bxzxz0101;pr_cw_i[31:24]=8'bzxxz1001;end
if(cycle==1600)begin $display("RING_FACE_PASS edges%0d full_output_bits1345 qids2_3 no_valid_mask POR66 repeated_reset XZ",cycle);$finish;end
end
initial begin #1;rst_n=0;end
endmodule
