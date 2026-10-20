`timescale 1ns/1ps
module tb_fp32_add_fan32_firstuse;
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0,valid_in=0;
  reg [31:0] a=0,b=0;
  integer cyc=0,errors=0,checked=0;
  reg [31:0] rng=32'h51f0a32;
  function automatic [31:0] step(input [31:0] x);
    reg [31:0] z;
    begin z=x^(x<<13);z=z^(z>>17);step=z^(z<<5);end
  endfunction
  genvar k;
  generate for(k=0;k<10;k=k+1) begin:g_cfg
    localparam integer L=3+(k/2),R=k%2;
    wire [31:0] yg,yd,y0;
    wire [1:0] eg,ed,e0;
    wire vg,vd,v0;
    ot_hdc_fp32_add_lat #(.LAT(L),.DRST(R)) gold (.clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(yg),.err(eg),.valid_out(vg));
    ot_hdc_fp32_add_lat_fan32 #(.LAT(L),.DRST(R),.SAFE_DIST(1)) dut (.clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(yd),.err(ed),.valid_out(vd));
    ot_hdc_fp32_add_lat_fan32 #(.LAT(L),.DRST(R),.SAFE_DIST(0)) legacy (.clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(y0),.err(e0),.valid_out(v0));
    always @(negedge clk) if(cyc>1) begin
      if(vg!==vd || vg!==v0 || ((vg||vd||v0) && ({yg,eg}!=={yd,ed} || {yg,eg}!=={y0,e0}))) begin
        $display("FAN32_MISMATCH cyc=%0d LAT=%0d DRST=%0d gold=%h/%h/%b dist=%h/%h/%b",cyc,L,R,yg,eg,vg,yd,ed,vd);errors=errors+1;
      end
      checked=checked+1;
    end
  end endgenerate
  initial begin
    repeat(5000) begin
      @(posedge clk); #1;cyc=cyc+1;
      rst_n=(cyc>3 && (cyc%311)!=0 && (cyc%311)!=1);
      rng=step(rng);a=rng;rng=step(rng);b=rng;
      case(cyc%13)
        0: a=32'h00000000;
        1: a=32'h80000000;
        2: a=32'h7f800000;
        3: a=32'h7fc00001;
        4: a=32'h00000001;
        5: begin a=32'h7f7fffff;b=a;end
        6: b=a^32'h80000000;
        7: begin a=32'h00800000;b=32'h807fffff;end
      endcase
      valid_in=(rng[3:0]!=0);
    end
    @(negedge clk);#1;
    if(errors) $fatal(1,"FAN32_EQ_FAIL errors=%0d",errors);
    $display("FAN32_FIRSTUSE_PASS comparisons=%0d LAT3..7 DRST0+1 with in-flight reset",checked);$finish;
  end
endmodule
