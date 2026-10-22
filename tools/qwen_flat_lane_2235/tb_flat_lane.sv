`timescale 1ns/1ps
// One authentic current lane. Expected data is supplied by hdc_golden.py.
module tb_flat_lane;
  reg clk=0; always #0.5 clk=~clk;
  reg rst_n=0,emit0=0,live=1,accept=0;
  reg [17:0] i=0; reg [2:0] cls=0,i_sfu=0;
  reg [23:0] addr=0; reg last=0;
  wire ar,br,cr,wr,rr,vm_we,kv_we,ov,retire,fault,l_last,redsq;
  wire [23:0] aa,ba,ca,wa,ra,vm_addr,kv_addr,raddr;
  wire [31:0] vm_data,kv_data,out; wire [1:0] red;
  reg [31:0] aq0=0,bq0=0,cq0=0,aq=0,bq=0,cq=0;
  reg [31:0] av[0:159],bv[0:159],cv[0:159],expected[0:159];
  integer cyc=0,got=0,writes=0,bad=0,issued=0,issue_edge[0:159],seen[0:159];
  reg [8191:0]dir;
  function automatic integer delta(input integer c);
    case(c) 0:delta=19;1:delta=68;2:delta=47;3:delta=56;default:delta=99;endcase
  endfunction
  ot_hdc_vstream_lane #(.WR(16),.AW(24),.NW(18),.LANE(0),.KV_FP8(1),.ML(1),.TLS(1),.QLA(3),.QLM(3),.SFH(0)) dut(
    .clk(clk),.rst_n(rst_n),.emit0(emit0),.live(live),.i(i),.fin_th(19'd15),.i_last_r(last),
    .cura0(addr),.curb0(addr),.curc0(addr),.curd0(addr),.rrow(addr+24'd7),
    .asi(24'd1),.bsi(24'd1),.csi(24'd1),.dsi(24'd1),
    .asrc(1'b0),.bsrc(1'b0),.csrc(1'b0),.mc(1'b1),.md(1'b1),.redsq(1'b0),
    .ma(2'd0),.mb(2'd0),.dst(2'd1),.red(2'd0),.ad(3'd0),.imm1(32'd0),.imm2(32'd0),.cls(cls),.accept(accept),.i_sfu(i_sfu),
    .va_re(ar),.va_addr(aa),.va_q(aq),.vb_re(br),.vb_addr(ba),.vb_q(bq),.vc_re(cr),.vc_addr(ca),.vc_q(cq),
    .wrom_re(wr),.wrom_addr(wa),.wrom_q(256'd0),.crom_re(rr),.crom_addr(ra),.crom_q(64'd0),
    .vm_we(vm_we),.vm_waddr(vm_addr),.vm_wdata(vm_data),.kv_we(kv_we),.kv_waddr(kv_addr),.kv_wdata(kv_data),
    .l_ov(ov),.l_out(out),.l_red(red),.l_redsq(redsq),.l_raddr(raddr),.l_last(l_last),.retire(retire),.l_fault(fault),
    .sx_exp_v(),.sx_exp_x(),.sy_exp_y(32'd0),.sy_exp_vo(1'b0),.sy_exp_f(1'b0),
    .sx_rcp_v(),.sx_rcp_x(),.sy_rcp_y(32'd0),.sy_rcp_f(1'b0),
    .sx_rsq_v(),.sx_rsq_x(),.sy_rsq_y(32'd0),.sy_rsq_f(1'b0));
  // ML1 memory contract: two sampling edges from request to visible answer.
  always @(posedge clk) begin
    if(ar)aq0<=av[aa];if(br)bq0<=bv[ba];if(cr)cq0<=cv[ca];
    aq<=aq0;bq<=bq0;cq<=cq0;
  end
  always @(posedge clk)begin
    cyc=cyc+1;
    if(rst_n&&emit0)begin issue_edge[addr]=cyc;issued=issued+1;end
    #0.001;
    if(rst_n)begin
      if(fault||kv_we||wr||rr)begin bad=bad+1;$display("UNEXPECTED_FLAG edge=%0d",cyc);end
      if(ov!==retire)begin bad=bad+1;$display("RETIRE_VALID_MISMATCH");end
      if(retire)begin
        integer a;a=raddr-7;got=got+1;
        if(a<0||a>159||seen[a]||out!==expected[a]||red!=0||redsq||l_last!==(a%32==15)||cyc-issue_edge[a]!=delta(a/32))begin
          bad=bad+1;$display("OUTPUT_MISMATCH edge=%0d addr=%0d got=%08h want=%08h age=%0d",cyc,a,out,expected[a],cyc-issue_edge[a]);
        end
        seen[a]=1;
        $display("RETIRE edge=%0d class=%0d row=%0d age=%0d value=%08h",cyc,a/32,a,cyc-issue_edge[a],out);
      end
      if(vm_we)begin
        writes=writes+1;
        if(vm_data!==expected[vm_addr]||cyc-issue_edge[vm_addr]!=delta(vm_addr/32)+1)begin bad=bad+1;$display("WRITE_MISMATCH edge=%0d row=%0d",cyc,vm_addr);end
      end
    end
  end
  task automatic run_class(input integer c);
    begin
      accept=1;i_sfu=c;@(negedge clk);accept=0;cls=c;
      repeat(140)@(negedge clk);
      for(integer k=0;k<16;k=k+1)begin addr=32*c+k;i=k;last=(k==15);emit0=1;@(negedge clk);end
      emit0=0;last=0;repeat(150)@(negedge clk);
    end
  endtask
  initial begin
    if(!$value$plusargs("DIR=%s",dir))$fatal;
    $readmemh({dir,"/a.hex"},av);$readmemh({dir,"/b.hex"},bv);$readmemh({dir,"/c.hex"},cv);$readmemh({dir,"/expected.hex"},expected);
    for(integer k=0;k<160;k=k+1)begin seen[k]=0;issue_edge[k]=-1;end
    repeat(8)@(negedge clk);rst_n=1;
    for(integer c=0;c<5;c=c+1)run_class(c);
    // Reset after populated TLS history and repeat sigmoid without zeroing SRAM.
    rst_n=0;repeat(8)@(negedge clk);
    for(integer k=128;k<144;k=k+1)seen[k]=0;
    rst_n=1;run_class(4);
    if(got!=96||issued!=96||writes!=96)begin bad=bad+1;$display("COUNT_MISMATCH got=%0d issued=%0d writes=%0d",got,issued,writes);end
    if(bad)$fatal(1,"FLAT_LANE_FAIL bad=%0d",bad);
    $display("FLAT_LANE_PASS values=%0d five_classes=1 dirty_reset=1",got);$finish;
  end
endmodule
