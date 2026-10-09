`timescale 1ns/1ps
module tb_mtp_p2_ordered_rows;
  parameter integer MUT_ORDER=0;
  reg clk=0;always #0.416667 clk=~clk;
  reg rst_n=0,start_v=0,sink_abort=0;
  wire start_r,done,fault;
  reg [73:0] identity=74'h123456789;
  reg [26:0] ids={9'd127,9'd65,9'd3};
  reg [1:0] iv=0,ish=0,ilast=0;
  wire [1:0] ir;
  reg [147:0] itag=0;
  reg [17:0] ie=0;
  reg [13:0] iw=0;
  reg [1023:0] idata=0;
  wire ov,osh,orl,otl;
  reg oready=0;
  wire [73:0] otag;wire [8:0] oe;wire [6:0] ow;
  wire [575:0] oq;
  integer received=0,cycles=0,bank,word,slice;
  reg checking=0;
  ot_mtp_p2_ordered_rows #(.ENABLE(1),.MUT_ORDER(MUT_ORDER)) dut(
    .clk(clk),.rst_n(rst_n),.start_v(start_v),.start_r(start_r),
    .start_identity(identity),.start_ids(ids),.in_v(iv),.in_r(ir),
    .in_identity(itag),.in_expert(ie),.in_shared(ish),.in_last(ilast),
    .in_word(iw),.in_data(idata),.out_v(ov),.out_r(oready),
    .out_identity(otag),.out_expert(oe),.out_shared(osh),.out_row_last(orl),
    .out_transaction_last(otl),.out_word(ow),.out_secded(oq),
    .sink_abort(sink_abort),.done(done),.fault(fault));
  function automatic [63:0] payload(input integer b,w,s);
    payload=64'hbad0000012345678^(b<<24)^(w<<8)^s;
  endfunction
  function automatic [511:0] flit(input integer b,w);
    integer s;begin for(s=0;s<8;s=s+1)flit[64*s+:64]=payload(b,w,s);end
  endfunction
  function automatic [8:0] expert(input integer b);
    case(b)0:expert=3;1:expert=65;2:expert=127;default:expert=0;endcase
  endfunction
  `include "ot_secded_cols.svh"
  function automatic [7:0] checks(input [63:0] d);
    reg [256*16-1:0] cols;integer i;
    begin cols=cols_all(64,8);checks=0;for(i=0;i<64;i=i+1)if(d[i])checks=checks^cols[16*i+:8];end
  endfunction
  always @(negedge clk) oready<=rst_n&&(cycles%7!=0)&&(cycles%7!=1);
  always @(posedge clk) begin
    cycles=cycles+1;
    if(checking&&ov&&oready) begin
      bank=received/80;word=received%80;
      if(otag!==identity||oe!==expert(bank)||osh!==(bank==3)||
         ow!==word||orl!==(word==79)||otl!==((bank==3)&&(word==79)))
        $fatal(1,"P2 FAIL identity/order at result%0d",received);
      for(slice=0;slice<8;slice=slice+1)
        if(oq[72*slice+:64]!==payload(bank,word,slice)||
           oq[72*slice+64+:8]!==checks(payload(bank,word,slice)))
          $fatal(1,"P2 FAIL protected payload result%0d slice%0d",received,slice);
      received=received+1;
    end
    if(checking&&fault)$fatal(1,"P2 FAIL unexpected fault");
    if(cycles>3000)$fatal(1,"P2 FAIL watchdog");
  end
  task automatic reset_start;
    begin
      @(negedge clk);checking=0;rst_n=0;iv=0;start_v=0;sink_abort=0;
      repeat(3)@(negedge clk);rst_n=1;
      @(negedge clk);start_v=1;
      @(negedge clk);start_v=0;
      if(fault)$fatal(1,"P2 FAIL start");
    end
  endtask
  task automatic send_pair(input integer b0,b1,w);
    begin
      @(negedge clk);iv=3;ish={(b1==3),(b0==3)};ilast={(w==79),(w==79)};
      itag={identity,identity};ie={expert(b1),expert(b0)};iw={7'(w),7'(w)};
      idata={flit(b1,w),flit(b0,w)};
      @(posedge clk);if(ir!==3)$fatal(1,"P2 FAIL input readiness");
      @(negedge clk);iv=0;
    end
  endtask
  task automatic negative(input integer kind);
    begin
      reset_start();@(negedge clk);iv=1;ish=0;ilast=0;
      itag={identity,identity};ie={9'd0,9'd3};iw=0;idata={512'd0,flit(0,0)};
      case(kind)
        0:itag[0]=~itag[0];
        1:ie[8:0]=9'd4;
        2:iw[6:0]=1;
        3:ilast[0]=1;
      endcase
      @(negedge clk);iv=0;
      repeat(3)@(negedge clk);
      if(!fault||ov)$fatal(1,"P2 FAIL negative%0d not rejected",kind);
    end
  endtask
  integer w,k;
  initial begin
    reset_start();checking=1;
    // Parallel B/A arrivals deliberately opposite to the golden drain order.
    for(w=0;w<80;w=w+1)send_pair(2,0,w);
    for(w=0;w<80;w=w+1)send_pair(3,1,w);
    wait(done);@(negedge clk);
    if(received!=320)$fatal(1,"P2 FAIL receipt count%0d",received);
    checking=0;
    for(k=0;k<4;k=k+1)negative(k);
    reset_start();send_pair(0,1,0);
    // Duplicate first word of row0 must poison, rather than overwrite silently.
    @(negedge clk);iv=1;ish=0;ilast=0;itag={identity,identity};
    ie={9'd0,9'd3};iw=0;idata={512'd0,flit(0,0)};
    @(negedge clk);iv=0;repeat(3)@(negedge clk);
    if(!fault)$fatal(1,"P2 FAIL duplicate not rejected");
    reset_start();sink_abort=1;@(negedge clk);sink_abort=0;
    if(!fault)$fatal(1,"P2 FAIL consumer UE abort not held");
    $display("P2 PASS full320flits exact ID/order/SECDED, wrong-ID/epoch/word/last/duplicate/UE-abort rejected cycles%0d",cycles);
    $finish;
  end
endmodule
