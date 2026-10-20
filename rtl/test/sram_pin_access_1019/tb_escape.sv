module tb_escape #(parameter integer MUT=0);
  localparam WORDS=32,BITS=64;
  localparam AW=$clog2(WORDS);
  reg rclk=0,wclk=0,rce=0,wce=0;
  reg [AW-1:0] ra=0,wa=0;
  reg [BITS-1:0] wd=0,wm=0;
  wire [BITS-1:0] rd;
  reg [BITS-1:0] refmem[0:WORDS-1];
  reg [BITS-1:0] expect_rd=0;
  integer checks=0;
  wire clk = rclk | wclk;
  ot_sram_escape64_1019 dut(.clk(clk),.rst_n(1'b1),.r_ce_in(rce),.w_ce_in(wce),
    .r_addr_in(ra),.w_addr_in(wa),.wd_in(wd),
    .w_mask_in(MUT==1 ? ~wm : wm),.rd_out(rd));
  task automatic write_word(input integer addr,input integer seed);
    wa=AW'(addr); wce=1;
    for(integer k=0;k<BITS;k=k+1) begin
      wd[k]=((k*17+seed*13+(k>>4))%11)<5;
      wm[k]=((k+seed)%5)!=0;
    end
    #3; wclk=1; #1;
    refmem[addr]=(refmem[addr]&~wm)|(wd&wm);
    wclk=0;wce=0;#2;
  endtask
  task automatic read_word(input integer addr,input integer enable_read);
    ra=AW'(addr);rce=1'(enable_read);
    if(enable_read) expect_rd=refmem[addr];
    #7;rclk=1;#1;
    if(rd!==expect_rd) $fatal(1,"ESCAPE_MISMATCH words=%0d bits=%0d addr=%0d check=%0d",WORDS,BITS,addr,checks);
    checks=checks+1;rclk=0;rce=0;#2;
  endtask
  initial begin
    for(integer a=0;a<WORDS;a=a+1) refmem[a]=0;
    // Populate every physical logical slot with masked writes, then wrap twice.
    for(integer e=0;e<3;e=e+1) begin
      for(integer a=0;a<WORDS;a=a+1) write_word(a,a+e*31);
      for(integer a=WORDS-1;a>=0;a=a-1) begin
        read_word(a,1);read_word((a+1)%WORDS,0);
      end
    end
    // Independent clock interleave; never same-address simultaneous collision.
    for(integer n=0;n<1200;n=n+1) begin
      write_word((n*7)%WORDS,n+79);
      read_word((n*11+1)%WORDS,1);
    end
    $display("ESCAPE_COUPON_PASS words=%0d bits=%0d checks=%0d read_edges=1",WORDS,BITS,checks);
    $finish;
  end
endmodule
