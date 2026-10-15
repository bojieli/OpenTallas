`timescale 1ns/1ps
module tb_hgi_coll_bridge_program_network;
 parameter integer MUT_DATA=0,MUT_WRAP=0;
 localparam CYCLES=700,WORDS=70;
 reg clk=0,rst_n=0;always #0.5 clk=~clk;
 reg cfg_v=0,desc_v=0,launch_v=0;reg [7:0] target=56;reg [11:0] addr=0;reg [255:0] cfg_data=0;
 wire [3:0] configured,init_busy,busy,done,fault,pfault;
 wire cw_v[0:3],ccw_v[0:3],cwr_v[0:3],ccwr_v[0:3];
 wire [544:0] cw_d[0:3],ccw_d[0:3],cwr_d[0:3],ccwr_d[0:3];
 wire [2:0] phy_v[0:3],rx_v[0:3];wire [1634:0] phy_d[0:3],rx_d[0:3];
 reg inj_v[0:3];reg [544:0] inj_d[0:3];
 reg [48:0] code[0:CYCLES-1][0:3];
 reg plan_iv[0:CYCLES-1][0:3];reg [544:0] plan_id[0:CYCLES-1][0:3];
 reg [7:0] checks_v[0:CYCLES-1][0:3];reg [4359:0] checks_d[0:CYCLES-1][0:3];
 reg check_rv[0:CYCLES-1][0:3];reg [544:0] check_rd[0:CYCLES-1][0:3];
 integer total=0,checked=0,rxchecked=0;
 function automatic integer nextq(input integer q);case(q)0:return 1;1:return 3;3:return 2;default:return 0;endcase endfunction
 function automatic integer prevq(input integer q);case(q)0:return 2;2:return 3;3:return 1;default:return 0;endcase endfunction
 for(genvar q=0;q<4;q=q+1)begin:g_q
  localparam N=q==0?3:2,ND=2*N+2,PREV=q==0?2:q==1?0:q==3?1:3,NEXT=q==0?1:q==1?3:q==3?2:0;
  if(N<3)begin assign phy_v[q][2]=0;assign rx_v[q][2]=0;assign phy_d[q][1634:1090]=0;assign rx_d[q][1634:1090]=0;end
  ot_hgi_coll_quarter_bridge_programmed #(.QID(2'(q)),.MUT_DATA(MUT_DATA),.MUT_WRAP(MUT_WRAP)) u_q(
   .rst_n(rst_n),.clk_program(clk),.clk_mem({2{clk}}),.clk_bridge({ND{clk}}),.clk_rx({N{clk}}),
   .cfg_v(cfg_v),.cfg_target(target),.cfg_addr(addr),.cfg_data(cfg_data),.desc_v(desc_v),
   .desc_base(12'd0),.desc_limit(13'(CYCLES)),.desc_loops(16'd1),.launch_v(launch_v),.program_active(1'b0),
   .local_tx_v({{(N-1){1'b0}},inj_v[q]}),.local_tx_d({{((N-1)*545){1'b0}},inj_d[q]}),
   .cw_in_v(cwr_v[PREV]),.cw_in_d(cwr_d[PREV]),.ccw_in_v(ccwr_v[NEXT]),.ccw_in_d(ccwr_d[NEXT]),
   .phy_rx_v({N{1'b0}}),.phy_rx_d({(N*545){1'b0}}),
   .phy_tx_v(phy_v[q][N-1:0]),.phy_tx_d(phy_d[q][N*545-1:0]),
   .local_rx_v(rx_v[q][N-1:0]),.local_rx_d(rx_d[q][N*545-1:0]),
   .cw_out_v(cw_v[q]),.cw_out_d(cw_d[q]),.ccw_out_v(ccw_v[q]),.ccw_out_d(ccw_d[q]),
   .configured(configured[q]),.init_busy(init_busy[q]),.busy(busy[q]),.done(done[q]),.program_fault(pfault[q]),.fault(fault[q]));
  ot_hgi_coll_quarter_bridge_relay u_cw(.clk(clk),.rst_n(rst_n),.in_v(cw_v[q]),.in_d(cw_d[q]),.out_v(cwr_v[q]),.out_d(cwr_d[q]));
  ot_hgi_coll_quarter_bridge_relay u_ccw(.clk(clk),.rst_n(rst_n),.in_v(ccw_v[q]),.in_d(ccw_d[q]),.out_v(ccwr_v[q]),.out_d(ccwr_d[q]));
 end
 task transfer(input integer start,input integer src,input integer dst,input integer seed);
  integer q,n,ns,nd,sw,t,input_sel,output_sel,direction,rxbase;reg [544:0] flit;
  begin:move
   for(integer b=0;b<545;b=b+1)flit[b]=((32'(b)*32'h9e3779b1)^(32'(seed)*32'h85ebca6b)^(32'(b*seed)>>7))>>(b%23)&1;
   flit[544:512]={1'b1,8'hff,8'(src),16'(seed)};
   q=src;t=start;input_sel=0;direction=seed&1;plan_iv[t][q]=1;plan_id[t][q]=flit;
   while(1)begin
    n=q==0?3:2;ns=n+2;nd=2*n+2;sw=$clog2(ns);rxbase=ns+nd+nd*sw;
    output_sel=q==dst?((seed&2)?n:0):2*n+direction;
    code[t][q][input_sel]=1;
    if(code[t][q][ns+output_sel])$fatal(1,"compiler resourcecollision");
    code[t][q][ns+output_sel]=1;
    for(integer bit_=0;bit_<sw;bit_++)code[t][q][ns+nd+output_sel*sw+bit_]=(input_sel>>bit_)&1;
    checks_v[t+1][q][output_sel]=1;checks_d[t+1][q][output_sel*545+:545]=flit;
    if(q==dst)begin
     if(output_sel==n)begin code[t+2][q][rxbase+:4]=4'he;check_rv[t+3][q]=1;check_rd[t+3][q]=flit;end
     total++;disable move;
    end
    q=direction==0?nextq(q):prevq(q);n=q==0?3:2;input_sel=n+direction;t+=3;
   end
  end
 endtask
 task config_frame(input integer q,input integer w,input integer half,input [255:0] value);
  @(negedge clk);cfg_v=1;target=8'(56+q);addr=12'(w*2+half);cfg_data=value;
 endtask
 integer launch_edge,cycle=0;
 always @(posedge clk)cycle<=cycle+1;
 initial begin
  for(integer t=0;t<CYCLES;t++)for(integer q=0;q<4;q++)begin
   code[t][q]=0;plan_iv[t][q]=0;plan_id[t][q]=0;checks_v[t][q]=0;checks_d[t][q]=0;check_rv[t][q]=0;check_rd[t][q]=0;
  end
  for(integer q=0;q<4;q++)begin inj_v[q]=0;inj_d[q]=0;end
  for(integer src=0;src<4;src++)for(integer dst=0;dst<4;dst++)for(integer k=0;k<16;k++)
   transfer(2+(src*4+dst)*40+k,src,dst,src*1000+dst*100+k);
  repeat(4)@(negedge clk);rst_n=1;
  for(integer q=0;q<4;q++)begin
   for(integer w=0;w<WORDS;w++)begin
    reg [511:0] catalog_word;catalog_word=0;for(integer i=0;i<10;i++)catalog_word[i*49+:49]=code[w*10+i][q];
    config_frame(q,w,0,catalog_word[255:0]);config_frame(q,w,1,catalog_word[511:256]);
    @(negedge clk);cfg_v=0;repeat(2)@(negedge clk);
   end
   @(negedge clk);target=8'(56+q);desc_v=1;
   @(negedge clk);desc_v=0;repeat(130)@(negedge clk);
   if(!configured[q] || pfault[q])$fatal(1,"nativecatalogue initialization failed q%0d",q);
  end
  @(negedge clk);launch_v=1;launch_edge=cycle+1;
  @(negedge clk);launch_v=0;
  // Real issuer first control appears L+5, actual bridge captures row0 atL+6.
  while(cycle<launch_edge+5)@(negedge clk);
  for(integer t=0;t<CYCLES+4;t++)begin
   for(integer q=0;q<4;q++)begin inj_v[q]=t<CYCLES?plan_iv[t][q]:0;inj_d[q]=t<CYCLES?plan_id[t][q]:0;end
   @(posedge clk);#0.01;
   if(|fault || |pfault)$fatal(1,"programmednetwork fault t%0d flags%h/%h",t,fault,pfault);
   if(t<CYCLES)for(integer q=0;q<4;q++)begin
    integer n;n=q==0?3:2;
    if(phy_v[q]!=={(3){1'b0}} && phy_v[q]!==3'b001)$fatal(1,"unexpectedPHYport");
    if(phy_v[q][0]!==checks_v[t][q][0] || cw_v[q]!==checks_v[t][q][2*n] || ccw_v[q]!==checks_v[t][q][2*n+1])$fatal(1,"networkvalid mismatch t%0d q%0d",t,q);
    if(phy_v[q][0])begin if(phy_d[q][544:0]!==checks_d[t][q][0+:545])$fatal(1,"PHYpayload mismatch");checked++;end
    if(cw_v[q])begin if(cw_d[q]!==checks_d[t][q][2*n*545+:545])$fatal(1,"CWpayload mismatch");checked++;end
    if(ccw_v[q])begin if(ccw_d[q]!==checks_d[t][q][(2*n+1)*545+:545])$fatal(1,"CCWpayload mismatch");checked++;end
    if(rx_v[q][0]!==check_rv[t][q])$fatal(1,"RXfacecycle mismatch t%0d q%0d",t,q);
    if(rx_v[q][0])begin if(rx_d[q][544:0]!==check_rd[t][q])$fatal(1,"RXpayload mismatch");rxchecked++;end
   end
   @(negedge clk);
  end
  if(total!=256 || rxchecked!=128 || checked==0)$fatal(1,"networkcoverage");
  $display("BRIDGE_PROGRAM_NETWORK PASS quarters4 native_catalogue_macros8 relay_stations8 RXfaces9 routes256 received128 checked_bridge_outputs%0d bits545 calendar700 first_bridge_captureLplus6",checked);$finish;
 end
endmodule
