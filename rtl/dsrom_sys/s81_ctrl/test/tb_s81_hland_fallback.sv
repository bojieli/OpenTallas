`timescale 1ns/1ps
module tb_s81_hland_fallback #(parameter integer MUT=0);
reg clk=0,rst=0;always #1 clk=~clk;
reg lv=0;reg [13:0] la=0;reg[511:0]ld=0;
reg[1:0]hrv=0;reg[27:0]hra=0;
wire[1:0]hsv,vqv;wire[1023:0]hsd;wire[27:0]vqa;
reg[1:0]vrv=0;reg[1023:0]vrd=0;
wire fault;wire[3:0]fc;wire[31:0]sc,vc;
reg[511:0]mem[0:1279];reg[1279:0]written=0;
integer early=0,bad=0,got=0,expected_base=0,epoch=0;
ot_s81_hc_hland #(.FD(16),.MUT(MUT==1?1:0)) dut(
.clk(clk),.rst_n(rst),.lw_v(lv),.lw_a(la),.lw_d(ld),
.h_rq_v(hrv),.h_rq_row(hra),.h_rs_v(hsv),.h_rs_d(hsd),
.v_rq_v(vqv),.v_rq_row(vqa),.v_rs_v(vrv),.v_rs_d(vrd),
.fault(fault),.fault_code(fc),.st_stream(sc),.st_vm(vc));
function automatic[511:0]word(input integer a,input integer e);
for(integer j=0;j<16;j=j+1)word[j*32+:32]=a*1777+j+e*65536;
endfunction
always @(posedge clk)if(rst)begin
 if(lv)begin mem[la]=ld;written[la]=1;end
 vrv<=vqv;
 for(integer s=0;s<2;s=s+1)begin
   if(vqv[s])begin
    if(!written[vqa[s*14+:14]])early=early+1;
    vrd[s*512+:512]<=mem[vqa[s*14+:14]]^(MUT==2?512'd1:512'd0);
   end
   if(hsv[s])begin
     if(hsd[s*512+:512]!==word(expected_base+got,epoch))bad=bad+1;
     got=got+1;
   end
 end
end
 task automatic land(input integer base,input integer e);
 for(integer i=0;i<640;i=i+1)begin
   @(negedge clk);lv=1;la=base+i;ld=word(base+i,e);
 end
 @(negedge clk);lv=0;
 endtask
 task automatic request(input integer base,input integer gap);
 repeat(gap)@(negedge clk);
 for(integer i=0;i<640;i=i+2)begin
 @(negedge clk);hrv=3;hra={14'(base+i+1),14'(base+i)};
 end
 @(negedge clk);hrv=0;
 endtask
initial begin
 repeat(5)@(negedge clk);rst=1;
 // FIFO overflows before the consumer asks; all requests arrive before landing
 // completes. A fresh slot1 then lands while slot0 fallback remains queued.
 fork land(0,0);request(0,40);join
 fork land(640,0);begin repeat(400)@(negedge clk);end join
 if(got!=640)bad=bad+1;
 got=0;expected_base=640;
 request(640,0);repeat(400)@(negedge clk);
 if(got!=640)bad=bad+1;
 got=0;expected_base=0;epoch=1;
 written[639:0]=0;
 fork land(0,1);request(0,0);join
 repeat(400)@(negedge clk);
 if(got!=640 || fault || early!=0 || sc!=1 || vc!=2)bad=bad+1;
 $display("HLAND_FALLBACK mut=%0d got=%0d early=%0d bad=%0d stream=%0d vm=%0d fault=%b code=%0d %s",MUT,got,early,bad,sc,vc,fault,fc,bad==0?"PASS":"FAIL");
 $finish;
end
endmodule
