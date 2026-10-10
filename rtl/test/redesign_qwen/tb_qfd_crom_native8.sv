`timescale 1ns/1ps
module tb_qfd_crom_native8 #(parameter integer MUT=0,N=6000,STRAP=0);
 reg clk=0,rst_n=0;
 reg [63:0] re=0;
 reg [1535:0] addr=0;
 reg [5:0] st=0;
 wire [4095:0] qr,qd;
 wire fr,fd;
 wire [1:0] cr,cd;
 ot_qfd_crom ref_(.clk(clk),.rst_n(rst_n),.crom_re(re),.crom_addr(addr),
  .crom_stage(st),.crom_q(qr),.fault(fr),.fault_code(cr));
 ot_qfd_crom_native8 #(.MUT(MUT),.STRAP(STRAP)) dut(.clk(clk),.rst_n(rst_n),.crom_re(re),
  .crom_addr(addr),.crom_stage(st),.crom_q(qd),.fault(fd),.fault_code(cd));
 integer checks=0,qscale=0,head=0,episodes=0,cycle=0,l,n,k,r,s,e;
 reg [31:0] rs=32'h13579bdf;
 reg [23:0] rb;
 task automatic rnd;begin rs=rs^(rs<<13);rs=rs^(rs>>17);rs=rs^(rs<<5);end endtask
 task automatic tick;begin
  #0.400;clk=1;#0.0166665;cycle=cycle+1;
  if(rst_n) begin
   checks=checks+1;
   if(qd!==qr||fd!==fr||cd!==cr)
    $fatal(1,"MISMATCH native8 cycle=%0d fault=%0b/%0b code=%0d/%0d",cycle,fd,fr,cd,cr);
  end
  #0.4166665;clk=0;
 end endtask
 task automatic reset_;begin
  rst_n=0;re=0;repeat(3) tick();rst_n=1;repeat(3) tick();
 end endtask
 task automatic read_(input integer stage_,region_,row_);begin
  st=stage_;
  case(region_)
   0:rb=4096;
   1:rb=533761;
   2:rb=537857;
   3:rb=9473;
   4:rb=0;
   5:rb=9472;
   default:rb=5376;
  endcase
  for(l=0;l<64;l=l+1) begin
   re[l]=1;
   addr[24*l+:24]=(region_==5)?rb:rb+64*row_+l;
  end
  if(region_==5) qscale=qscale+1;
  if(stage_==36) head=head+1;
  tick();
 end endtask
 task automatic finish_;begin re=0;repeat(10) tick();end endtask
 task automatic fault_episode(input integer mode_);begin
  reset_();episodes=episodes+1;
  st=0;re='1;
  for(l=0;l<64;l=l+1) addr[24*l+:24]=4096+l;
  case(mode_)
   0:addr[24*8+:24]=541953;                      // range in group1
   1:addr[24*11+:24]=4096+12;                   // lane misalignment
   2:addr[24*5+:24]=4096+64+5;                  // narrow column disagrees
   3:st=37;                                   // stage out of range
   4:begin st=36;addr[24*35+:24]=4096+35;end    // HEAD out of range
   5:begin addr[24*0+:24]=4097;addr[24*8+:24]=541953;
     addr[24*21+:24]=4096+64+21;end              // priority1 over2 over3
   6:begin addr[24*0+:24]=4097;addr[24*21+:24]=4096+64+21;end // priority2 over3
   7:addr[24*0+:24]=4097;                      // first2, then1 in another group
   8:addr[24*5+:24]=4096+64+5;                 // first3, then1 in another group
   default:begin
    for(l=0;l<64;l=l+1) addr[24*l+:24]=9473+l;
    addr[24*10+:24]=9473+64+10;                // wide column disagrees
   end
  endcase
  tick();finish_();
  if(!fr) $fatal(1,"FAULT stimulus missing mode=%0d",mode_);
  if(mode_==7||mode_==8) begin
   re=0;re[8]=1;st=0;addr[24*8+:24]=541953;
   tick();finish_();
  end
 end endtask
 initial begin
  reset_();
  // Fill output stations with zero then measure actual5-edge QSCALE answer.
  read_(0,4,0);finish_();
  st=0;re='1;for(l=0;l<64;l=l+1) addr[24*l+:24]=9472;
  for(e=1;e<=5;e=e+1) begin
   tick();
   if(e<5&&qd!==0) $fatal(1,"LATENCY earlier than5 edges");
   if(e==5&&qd!={64{64'h3db504f3_00000000}}) $fatal(1,"LATENCY not5 edges");
  end
  qscale=qscale+1;finish_();
  for(s=0;s<36;s=s+1) begin
   read_(s,0,19);read_(s,1,63);read_(s,2,63);
   read_(s,3,8191);read_(s,4,63);read_(s,5,0);read_(s,6,63);
  end
  for(r=0;r<64;r=r+1) read_(36,4,r);
  finish_();
  for(n=0;n<N;n=n+1) begin
   rnd();s=rs%37;rnd();k=rs%7;rnd();
   if(s==36) begin k=4;r=rs%64;end
   else case(k)
    0:r=rs%20;
    3:r=rs%8192;
    default:r=rs%64;
   endcase
   st=s;
   case(k) 0:rb=4096;1:rb=533761;2:rb=537857;3:rb=9473;
    4:rb=0;5:rb=9472;default:rb=5376;endcase
   for(l=0;l<64;l=l+1) begin
    rnd();re[l]=rs[0];addr[24*l+:24]=(k==5)?rb:rb+64*r+l;
   end
   if(k==5) qscale=qscale+1;if(s==36) head=head+1;
   tick();
  end
  finish_();
  if(fr) $fatal(1,"Unexpected valid-read fault");
  for(k=0;k<10;k=k+1) fault_episode(k);
  if(qscale<36||head<64||episodes!=10) $fatal(1,"COVERAGE missing");
  $display("PASS native8 checks=%0d QSCALE=%0d HEAD=%0d fault_episodes=%0d read_edges=5",checks,qscale,head,episodes);
  $finish;
 end
endmodule
