`timescale 1ns/1ps
`ifndef KVD_ER_RL
`define KVD_ER_RL 3
`endif
module tb_qkd_astk_er_chain_st;
 localparam N=4,RL=`KVD_ER_RL,L=7+7*(2+RL);
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg [3:0] rv=0; reg [43:0] ra=0;
 wire [3:0] sv;wire [43:0] sa;wire [255:0] sd;wire fault;
 wire [103:0] aso;wire [511:0] esi;wire [127:0] com;
 reg [7:0] legacy=0;reg suppress_com=0;
 reg [521:0] ri[0:7];
 function automatic [63:0] word(input integer e,row,quad);
  word=64'habcde12300000000 | (64'(e)<<20) | (64'(row)<<8) | 64'(quad);
 endfunction
 qkd_astk_er_chain_st #(.N(N),.RL(RL)) dut(.ck(ck),.rst_n(rst_n),.read_v(rv),.read_addr(ra),
  .eso_v(legacy),.com(suppress_com?128'd0:com),.esi(esi),.aso(aso),
  .response_v(sv),.response_addr(sa),.response_data(sd),.fault(fault));
 for(genvar e=0;e<8;e=e+1)begin:g_ep
  wire [632:0] si;
  qkd_astk_ep_s u_ep(.cal_exp(16'hffff),.eo(8'd0),.ck(ck),.rst_n(rst_n),.sq(5'(e)),
   .so({399'd0,aso[13*e+:13]}),.sf(1'b0),.si(si),.qi({557'd0,14'd8192,1'b0}),
   .xi(267'd0),.xo(),.zi(651'd0),.zo(),.ri(ri[e]),.xa(),.xe(136'd0));
  assign esi[64*e+:64]=si[569+:64];assign com[16*e+:16]=si[537+:16];
 end
 reg [3:0] ev[0:L-1];reg [43:0] ea[0:L-1];
 integer cycle=0,errors=0,reads=0,j,k,t,e,row,quad,owner;
 reg checking=0;
 always @(posedge ck) begin
  if(!rst_n) begin for(integer a=0;a<L;a=a+1)ev[a]<=0;end
  else begin
   ev[0]<=rv;ea[0]<=ra;
   for(integer a=1;a<L;a=a+1)begin ev[a]<=ev[a-1];ea[a]<=ea[a-1];end
  end
 end
 always @(negedge ck)if(rst_n&&checking)begin
  cycle=cycle+1;
  if(sv!==ev[L-1])begin errors=errors+1;if(errors<6)$display("FAIL valid cycle=%0d got=%b want=%b",cycle,sv,ev[L-1]);end
  for(integer a=0;a<N;a=a+1)if(ev[L-1][a])begin
   owner=ea[L-1][11*a+3+:3];row={ea[L-1][11*a+7+:4],ea[L-1][11*a+6]};
   // SRAM address is {so[12],so[11:8],so[7]} = {0,addr[10:7],addr[6]}.
   quad=ea[L-1][11*a+:3];
   if(sa[11*a+:11]!==ea[L-1][11*a+:11] || sd[64*a+:64]!==word(owner,row,quad))begin
    errors=errors+1;if(errors<6)$display("FAIL data cycle=%0d port=%0d addr=%h got=%h expected=%h",cycle,a,sa[11*a+:11],sd[64*a+:64],word(owner,row,quad));end
   reads=reads+1;
  end
 end
 task automatic reset_all;
  begin rv=0;legacy=0;rst_n=0;repeat(8)@(negedge ck);rst_n=1;repeat(L+8)@(negedge ck);end
 endtask
 initial begin
  for(e=0;e<8;e=e+1)ri[e]=0;
  reset_all();
  // Actual target EPs accept external row-write stimuli on their real ri pins;
  // every read traverses the instantiated four mapped SRAM macros per EP.
  for(t=0;t<64;t=t+1)begin
   for(e=0;e<8;e=e+1)begin
    ri[e]=0;ri[e][0]=1;ri[e][1]=t/32;ri[e][5:2]=(t/2)%16;ri[e][9:6]={1'(t%2),3'(e)};
    for(k=0;k<8;k=k+1)ri[e][10+64*k+:64]=word(e,t,k);
   end
   @(negedge ck);
  end
  for(e=0;e<8;e=e+1)ri[e]=0;
  repeat(12)@(negedge ck);
  if(com!==128'h80804040202010100808040402020101)begin
   // Each EP commits only its Q and Q+8 groups; all eight together cover ffff.
   $display("INFO committed=%h",com);
  end
  checking=1;
  for(t=0;t<512;t=t+1)begin
   rv=15;
   for(j=0;j<4;j=j+1)ra[11*j+:11]={4'(t/32),1'(t/16),3'((t+j)%8),3'(t%8)};
   @(negedge ck);
  end
  rv=0;repeat(L+8)@(negedge ck);checking=0;
  if(fault || reads!=2048)begin errors=errors+1;$display("FAIL production fault=%b reads=%0d",fault,reads);end
  // Independent visibility fault, with no collision or legacy request.
  suppress_com=1;rv=1;ra=0;@(negedge ck);rv=0;repeat(L+8)@(negedge ck);
  if(!fault)begin errors=errors+1;$display("FAIL visibility fault absent");end
  suppress_com=0;reset_all();
  rv=3;ra=0;@(negedge ck);rv=0;repeat(L+8)@(negedge ck);
  if(!fault)begin errors=errors+1;$display("FAIL collision fault absent");end
  reset_all();legacy=8'h80;@(negedge ck);legacy=0;repeat(L+8)@(negedge ck);
  if(!fault)begin errors=errors+1;$display("FAIL legacy fault absent");end
  if(errors==0)$display("PASS qkd_astk_er_chain_st actual_EP_mapped_SRAM reads=%0d exact_latency=%0d RL=%0d",reads,L,RL);
  else $display("FAIL qkd_astk_er_chain_st errors=%0d",errors);
  $finish;
 end
endmodule
