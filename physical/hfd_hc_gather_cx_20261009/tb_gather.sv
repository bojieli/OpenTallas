`timescale 1ps/1fs
// Full 88-lane physical-envelope mapping gate; arithmetic lane is a stub.
// Independent committed Plan.model vectors, common and phase-varied forwarded
// clocks. No numeric HC / CDC / real PLL qualification is inferred from this.
module tb;
  parameter integer ENABLE=1;
  parameter integer PHASE_MODE=0;
  reg base=0;
  always #416.666666 base=~base;
  wire [7:0] ck;
  for(genvar i=0;i<8;i=i+1) begin:g_ck
    localparam integer P=(PHASE_MODE==0)?0:((PHASE_MODE==1)?i*20:(7-i)*20);
    assign #(P) ck[i]=base;
  end
  reg rst=1;
  reg [1023:0] din=0;
  wire [1023:0] dout;
  reg [1023:0] vin[0:5],vout[0:5];
  integer v,c,bad=0,edges[0:7],first,max_settle=0;
  for(genvar i=0;i<8;i=i+1) begin:g_edges
    initial edges[i]=0;
    always @(posedge ck[i]) edges[i]=edges[i]+1;
  end
  hfd_hc #(.ENABLE_GATHER_COHERENCE(ENABLE)) dut(
    .ck0(ck[0]),.ck1(ck[1]),.ck2(ck[2]),.ck3(ck[3]),
    .ck4(ck[4]),.ck5(ck[5]),.ck6(ck[6]),.ck7(ck[7]),
    .rst(rst),.f_sfu(din),.t_sfu(dout));
  initial begin
    $readmemh("tb_in.mem",vin); $readmemh("tb_out.mem",vout);
    repeat(6) @(negedge base);
    rst=0;
    for(v=0;v<6;v=v+1) begin
      @(negedge base); din=vin[v]; first=-1;
      // 40 cycles from the original composed envelope model, plus 4 edges
      // to cover initial phase offsets. This is stimulus hold, no job timeout.
      for(c=0;c<44;c=c+1) begin
        @(negedge base); #200;
        if(first<0 && dout===vout[v]) first=c+1;
      end
      if(dout!==vout[v]) begin bad=bad+1; $display("MISMATCH vector=%0d",v); end
      if(first>max_settle) max_settle=first;
    end
    for(c=0;c<8;c=c+1) if(edges[c]<260) $fatal(1,"clock did not forward: %0d",c);
    $display("OT_RESULT enable=%0d phase_mode=%0d phase_step_ps=20 vectors=6 mismatches=%0d settle_cycles=%0d",ENABLE,PHASE_MODE,bad,max_settle);
    if(bad!=0) $fatal(1,"mapping FAIL");
    $finish;
  end
endmodule
