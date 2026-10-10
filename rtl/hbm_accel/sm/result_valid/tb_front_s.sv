module tb_front_s;
  parameter integer RV = 1;   // RV 0 = the released unqualified front (negative control: must FAIL)
  reg clk=0,rst_n=0;
  always #5 clk=~clk;
  reg [367:0] landing=0;
  wire rv,fault,fsv;
  wire [11:0] rrow;
  wire [255:0] rdata;
  reg [1:0] expected_v=0,expected_f=0;
  reg sticky=0;
  reg [267:0] data_pipe0=0,data_pipe1=0;
  integer checks=0,c;
  ot_hbm_accel_smh_front_s #(.RESULT_VALID(RV),.NC(8)) dut(
    .clk(clk),.rst_n(rst_n),.rv(rv),.fault(fault),.rrow(rrow),.rdata(rdata),.fsv(fsv));
  task tick(input [7:0] v,input [7:0] f,input [11:0] row);
    reg [255:0] expected_data;
    begin
      @(negedge clk);
      for(c=0;c<8;c=c+1) begin
        landing[c*46 +: 46]={v[c],f[c],32'h10000000+c+row,row};
        expected_data[c*32 +: 32]=32'h10000000+c+row;
      end
      expected_v={expected_v[0],(&v)};
      expected_f={expected_f[0],sticky};
      sticky=sticky || ((|(f&v)) || ((|v)&&!(&v)));
      data_pipe1=data_pipe0;data_pipe0={row,expected_data};
      @(posedge clk);#1;
      if(rv!==expected_v[1] || fsv!==(&v) || fault!==expected_f[1])
        $fatal(1,"FRONT_QUALIFY_FAIL v=%h got=%b/%b/%b exp=%b/%b/%b",v,rv,fsv,fault,expected_v[1],(&v),expected_f[1]);
      if(rv && {rrow,rdata}!==data_pipe1) $fatal(1,"FRONT_DATA_FAIL");
      checks=checks+1;
    end
  endtask
  initial begin
    force dut.al=landing;
    repeat(2) @(posedge clk);#1;rst_n=1;
    repeat(10) tick(0,8'hff,0); // stale held fault from every gated idle column
    tick(8'hff,0,12'h321);tick(0,8'hff,0);tick(0,8'hff,0);
    tick(8'hff,0,12'h322);tick(8'hff,8'h20,12'h323);tick(0,8'hff,0);tick(0,8'hff,0);
    tick(8'h01,0,12'h324);tick(0,0,0);tick(0,0,0); // partial row must not retire
    $display("SM_FRONT_VALID_PASS checks=%0d NC=8 unchanged_data_and_latency=1",checks);$finish;
  end
endmodule
