// ND8 checks the package on role0; ND1 checks only the peer's genuine own boot.
module qkd_host_rst_role_pins #(parameter NL=6,ND=8,T_LINK=200000,T_HBM=200000)(
 input wire clk,por_n,soft_rst,input wire[2:0]die_id,input wire[NL-1:0]link_up,
 input wire[ND-1:0]boot_done,boot_ok,
 output reg host_rst_n,link_rst_n,hbm_rst_n,boot_go,die_rst_n,sys_ready,boot_fault,
 output reg[3:0]boot_state,boot_err,output reg[31:0]boot_cycles
);
 reg soft_q,role_valid,role_fault;reg[2:0]role_q,die_q;reg[1:0]strap_samples;
 reg[NL-1:0]links_q;reg[ND-1:0]done_q,ok_q;
 always @(posedge clk or negedge por_n)if(!por_n)begin
 soft_q<=0;role_valid<=0;role_fault<=0;role_q<=0;die_q<=0;strap_samples<=0;links_q<=0;done_q<=0;ok_q<=0;
 end else begin
 soft_q<=soft_rst;die_q<=die_id;links_q<=link_up;done_q<=boot_done;ok_q<=boot_ok;
 if(!role_valid)begin
  if(strap_samples==1)begin role_q<=die_q;role_valid<=1;end else strap_samples<=strap_samples+1'b1;
 end else if(die_q!=role_q)role_fault<=1;
 end
 wire[1:0]hr,lr,mr,bg,dr,sr,bf;wire[7:0]bs,be;wire[63:0]bc;
 ot_qwen_sys_rst_seq #(.NL(NL),.ND(8),.T_LINK(T_LINK),.T_HBM(T_HBM))u_global(
 .clk(clk),.por_n(por_n),.soft_rst(soft_q),.link_up(links_q),.boot_done(done_q),.boot_ok(ok_q),
 .host_rst_n(hr[0]),.link_rst_n(lr[0]),.hbm_rst_n(mr[0]),.boot_go(bg[0]),.die_rst_n(dr[0]),.sys_ready(sr[0]),.boot_fault(bf[0]),
 .boot_state(bs[3:0]),.boot_err(be[3:0]),.boot_cycles(bc[31:0]));
 ot_qwen_sys_rst_seq #(.NL(NL),.ND(1),.T_LINK(T_LINK),.T_HBM(T_HBM))u_local(
 .clk(clk),.por_n(por_n),.soft_rst(soft_q),.link_up(links_q),.boot_done(done_q[role_q]),.boot_ok(ok_q[role_q]),
 .host_rst_n(hr[1]),.link_rst_n(lr[1]),.hbm_rst_n(mr[1]),.boot_go(bg[1]),.die_rst_n(dr[1]),.sys_ready(sr[1]),.boot_fault(bf[1]),
 .boot_state(bs[7:4]),.boot_err(be[7:4]),.boot_cycles(bc[63:32]));
 wire peer=(role_q!=0);
 always @(posedge clk or negedge por_n)if(!por_n)begin
 host_rst_n<=0;link_rst_n<=0;hbm_rst_n<=0;boot_go<=0;die_rst_n<=0;sys_ready<=0;boot_fault<=0;boot_state<=0;boot_err<=0;boot_cycles<=0;
 end else begin
 host_rst_n<=role_valid && hr[peer];
 link_rst_n<=role_valid && !role_fault && lr[peer];hbm_rst_n<=role_valid && !role_fault && mr[peer];
 boot_go<=role_valid && !role_fault && bg[peer];die_rst_n<=role_valid && !role_fault && dr[peer];sys_ready<=role_valid && !role_fault && sr[peer];
 boot_fault<=role_fault || bf[peer];boot_state<=role_fault?4'd6:bs[peer*4+:4];
 boot_err<=role_fault?4'd4:be[peer*4+:4];boot_cycles<=bc[peer*32+:32];
 end
 initial if(ND!=8)$fatal(1,"role reset requires genuine ND8 package vector");
endmodule
