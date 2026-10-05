`timescale 1ps/1fs
// Changed-boundary gate. One representative lane, actual NC8/PF384 capacity,
// eight receive ports and original pairwise RTL reference; not whole-token proof.
module tb_ha2_tu_owner_adapter;
  reg clk=0; always #416.666667 clk=~clk;
  reg rst_n=0,ref_rst=0,active=0,arm=0;
  reg [15:0] pf=64;
  reg [1:0] hv=0; reg [127:0] hd=0;
  reg [7:0] pv=0;reg [519:0] pd=0;
  wire [95:0] ref_hd={hd[64+:48],hd[0+:48]};
  wire [455:0] ref_pd;
  for(genvar p=0;p<8;p=p+1) assign ref_pd[57*p+:57]={pd[65*p+64],pd[65*p+:56]};
  wire cv,cdup,ci,cquiet;wire [15:0] cm;wire [31:0] cd;
  ot_ha2_tu_owner_adapter #(.LANES(1)) dut(.clk(clk),.rst_n(rst_n),.active(active),.arm(arm),
    .rank(8'd19),.pf(pf),.h_v(hv),.h_d(hd),.p_v(pv),.p_flit(pd),
    .r_v(cv),.r_m(cm),.r_d(cd),.dupe(cdup),.issue_o(ci),.quiet(cquiet));
  wire [1:0] rv,dup,issue; wire [15:0] rm[0:1];wire [31:0] rd[0:1];
  for(genvar b=0;b<2;b=b+1)begin:g_ref
    ot_ha2_owner_reduce #(.LANES(1),.E(b==0?64:384),.NC(8),.NP(8),.INJ(2),.SLOTREG(1)) ref_dut
      (.clk(clk),.rst_n(ref_rst),.rank(8'd19),.h_v(hv),.h_d(ref_hd),.p_v(pv),.p_flit(ref_pd),
       .r_v(rv[b]),.r_m(rm[b]),.r_d(rd[b]),.dupe(dup[b]),.issue_o(issue[b]));
  end
  integer phase=0,results=0,cycles=0,first_issue=-1,first_result=-1,last_result=-1;
  reg checking=0;
  always @(posedge clk)begin
    cycles=cycles+1;
    if(checking)begin
      if(ci&&first_issue<0)first_issue=cycles;
      #1;
      if(cdup||dup[phase])$fatal(1,"unexpected fault");
      if(cv!==rv[phase] || ci!==issue[phase])$fatal(1,"strobe mismatch cycle=%0d",cycles);
      if(cv)begin
        if(cm!==rm[phase]||cd!==rd[phase])$fatal(1,"numeric/index mismatch");
        if(first_result<0)first_result=cycles;
        last_result=cycles;results=results+1;
      end
    end
  end
  function automatic [31:0] operand(input integer c,f);
    // Cancellation and BF16 tie boundaries exercise all golden tree levels.
    case((c+f)%8)
      0:operand=32'h3f808000;1:operand=32'hbf800000;
      2:operand=32'h3f818000;3:operand=32'h33800000;
      4:operand=32'h4b000000;5:operand=32'hcb000000;
      6:operand=32'h3eaaaaab;default:operand=32'hbeaaaaab;
    endcase
  endfunction
  task automatic run_phase(input integer ph);
    integer ofl;
    phase=ph;ofl=(ph==0?64:384)/8;
    ref_rst=0;checking=0;results=0;first_issue=-1;first_result=-1;last_result=-1;
    repeat(3)@(negedge clk);
    if(!cquiet)$fatal(1,"arm before drained reducer");
    arm=1;pf=ph==0?64:384;@(negedge clk);arm=0;active=1;ref_rst=1;checking=1;
    for(integer f=0;f<ofl;f=f+1)begin
      hv=1;hd[0+:64]={16'(100+f),16'(3*ofl+f),operand(3,f)};
      pv=8'hf7;
      for(integer c=0;c<8;c=c+1)pd[65*c+:65]={1'b0,8'd19,8'(c),16'(f),operand(c,f)};
      @(negedge clk);
    end
    hv=0;pv=0;
    repeat(40)@(negedge clk);
    if(results!=ofl/2||!cquiet)$fatal(1,"result/debt count %0d",results);
    $display("PHASE PASS pf=%0d results=%0d first_issue=%0d first_result=%0d last_result=%0d first_latency_cycles=%0d period_ps=833.333334",pf,results,first_issue,first_result,last_result,first_result-first_issue);
    checking=0;
  endtask
  initial begin
    repeat(4)@(negedge clk);rst_n=1;
    run_phase(0);run_phase(1);
    // The TU destination is rejected before header stripping/slot writes.
    active=0;rst_n=0;repeat(3)@(negedge clk);rst_n=1;pf=384;active=1;
    pv=1;pd[0+:65]={1'b0,8'd18,8'd0,16'd0,32'h3f800000};
    @(negedge clk);pv=0;@(negedge clk);
    if(!cdup||dut.u_reduce.pres[0][0])$fatal(1,"foreign dst accepted");
    $display("DESTINATION PASS no slot write");
    $display("PASS changed adapter 28 packed words exact; runtime rearm and header validation");$finish;
  end
endmodule
