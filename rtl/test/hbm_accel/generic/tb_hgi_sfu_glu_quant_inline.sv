`timescale 1ns/1ps
module tb_hgi_sfu_glu_quant_inline #(parameter integer MUT=0);
 reg clk=0;always #0.4166665 clk=~clk;
 reg rst_n=0,glu_issue=0,quant_launch=0,emit_v=0;
 reg [31:0] gate=0,up=0,route=0,word_id=0;
 reg [6:0] quant_block=0;reg [4:0] emit_addr=0;reg [3:0] emit_group=0;
 wire xw_en,glu_valid,aq_valid,fault;
 wire [6:0] xw_addr,xw_grp;wire [2047:0] xw_data;
 wire [31:0] glu_data,glu_tag;wire [255:0] aq_codes;wire signed [9:0] aq_exp;wire [511:0] aq_dequant;
 ot_hgi_sfu_glu_quant_inline #(.MUT(MUT)) dut(.clk_math({3{clk}}),.clk_control(clk),
  .clk_aq_core(clk),.clk_aq_delay(clk),.clk_aq_encode(clk),.clk_code({4{clk}}),.rst_n(rst_n),
  .glu_issue(glu_issue),.gate(gate),.up(up),.route(route),.word_id(word_id),.quant_launch(quant_launch),.quant_block(quant_block),
  .emit_v(emit_v),.emit_addr(emit_addr),.emit_group(emit_group),.xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
  .glu_valid(glu_valid),.glu_data(glu_data),.glu_tag(glu_tag),.aq_valid(aq_valid),.aq_codes(aq_codes),.aq_exp(aq_exp),.aq_dequant(aq_dequant),.fault(fault));
 reg [31:0] gates[0:3071],ups[0:3071],routes[0:0],gold[0:3071];
 reg [265:0] qgold[0:95];reg [511:0] dgold[0:95];reg [2047:0] xgold[0:311];
 reg [1023:0] data_dir;
 integer c=-1,ng=0,nq=0,nx=0,first_q=-1,last_q=-1,first_x=-1,last_x=-1;
 always @(posedge clk)begin
  if(rst_n)begin
   if(fault)$fatal(1,"INLINE_FAULT c=%d",c);
   if(glu_valid)begin
    if(glu_tag!==ng||glu_data!==gold[ng])$fatal(1,"INLINE_GLU_WORD");ng=ng+1;
   end
   if(aq_valid)begin
    if({aq_exp,aq_codes}!==qgold[nq])$fatal(1,"INLINE_AQ_WORD block=%d actual=%h expected=%h",nq,{aq_exp,aq_codes},qgold[nq]);
    if(aq_dequant!==dgold[nq])$fatal(1,"INLINE_DEQUANT_WORD");
    if(first_q<0)first_q=c;last_q=c;nq=nq+1;
   end
   if(xw_en)begin
    if(xw_addr!==7'(nx/13)||xw_grp!==7'(nx%13)||xw_data!==xgold[nx])$fatal(1,"INLINE_XWRITE beat=%d addr=%d group=%d actual=%h expected=%h",nx,xw_addr,xw_grp,xw_data,xgold[nx]);
    if(first_x<0)first_x=c;last_x=c;nx=nx+1;
   end
  end
 end
 initial begin
  if(!$value$plusargs("DATA=%s",data_dir))$fatal(1,"DATA");
  $readmemh({data_dir,"/gate.hex"},gates);$readmemh({data_dir,"/up.hex"},ups);$readmemh({data_dir,"/route.hex"},routes);$readmemh({data_dir,"/gold.hex"},gold);
  $readmemh({data_dir,"/quant.hex"},qgold);$readmemh({data_dir,"/dequant.hex"},dgold);$readmemh({data_dir,"/xwrite.hex"},xgold);
  repeat(5)@(negedge clk);rst_n=1;
  for(integer cycle=0;cycle<3530;cycle=cycle+1)begin
   @(negedge clk);c=cycle;
   glu_issue=cycle<3072;
   if(glu_issue)begin gate=gates[cycle];up=ups[cycle];route=routes[0];word_id=cycle;end
   quant_launch=cycle>=140&&cycle<=3180&&(cycle-140)%32==0;
   quant_block=7'((cycle-140)/32);
   emit_v=cycle>=3210&&cycle<3522;
   if(emit_v)begin emit_addr=5'((cycle-3210)/13);emit_group=4'((cycle-3210)%13);end
  end
  @(negedge clk);glu_issue=0;quant_launch=0;emit_v=0;
  if(ng!=3072||nq!=96||nx!=312)$fatal(1,"INLINE_COUNT %d %d %d",ng,nq,nx);
  $display("PASS actualGLU3072BF16→unchangedAQ96blocks3072codes96exps3072dequant→8realSRAM→312SMxwrite col0only aq_first=%0d aq_last=%0d xwrite_first=%0d xwrite_last=%0d full8contextsOPEN physicalUNQUALIFIED",first_q,last_q,first_x,last_x);$finish;
 end
endmodule
