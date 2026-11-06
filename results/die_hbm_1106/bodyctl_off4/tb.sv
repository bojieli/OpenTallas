module tb;reg clk=0;always #5 clk=~clk;reg[31:0] a;reg[15:0] b;reg[31:0] aq;reg[15:0]bq;wire[15:0] bp0,bp1,bp2,bp3,bp4,bp5,bp6;reg[15:0] bq0,bq1,bq2,bq3,bq4,bq5,bq6;wire[31:0] gold;reg[31:0] g;
always@(posedge clk)begin aq<=a;bq<=b;bq0<=bp0;bq1<=bp1;bq2<=bp2;bq3<=bp3;bq4<=bp4;bq5<=bp5;bq6<=bp6;g<=gold;end
base2 bu(aq,bq,bp0,bp1,bp2,bp3,bp4,bp5,bp6);base3 bc(bq0,bq1,bq2,bq3,bq4,bq5,bq6,gold);
wire[7:0] np0,np1,np2,np3,np4,np5,np6,np7,np8,np9,np10,np11,np12,np13,np14,np15,np16,np17,np18,np19,np20,np21,np22,np23,np24,np25;reg[7:0] nq0,nq1,nq2,nq3,nq4,nq5,nq6,nq7,nq8,nq9,nq10,nq11,nq12,nq13,nq14,nq15,nq16,nq17,nq18,nq19,nq20,nq21,nq22,nq23,nq24,nq25;
new1 nu(a,b,np0,np1,np2,np3,np4,np5,np6,np7,np8,np9,np10,np11,np12,np13,np14,np15,np16,np17,np18,np19,np20,np21,np22,np23,np24,np25);always@(posedge clk)begin nq0<=np0;nq1<=np1;nq2<=np2;nq3<=np3;nq4<=np4;nq5<=np5;nq6<=np6;nq7<=np7;nq8<=np8;nq9<=np9;nq10<=np10;nq11<=np11;nq12<=np12;nq13<=np13;nq14<=np14;nq15<=np15;nq16<=np16;nq17<=np17;nq18<=np18;nq19<=np19;nq20<=np20;nq21<=np21;nq22<=np22;nq23<=np23;nq24<=np24;nq25<=np25;end
wire[15:0] lo,h0,h1;wire carry;reg[15:0]lq,hq0,hq1;reg cq;wire[31:0] z;reg[31:0] c,drop,phase,flip;
split2 ns(nq0,nq1,nq2,nq3,nq4,nq5,nq6,nq7,nq8,nq9,nq10,nq11,nq12,nq13,nq14,nq15,nq16,nq17,nq18,nq19,nq20,nq21,nq22,nq23,nq24,nq25,lo,h0,h1,carry);split3 nc(lq,hq0,hq1,cq,z);
wire[31:0] px,py;reg[31:0]pqx,pqy;wire[31:0]pz;reg[31:0]pureres;
pure2 ps(nq0,nq1,nq2,nq3,nq4,nq5,nq6,nq7,nq8,nq9,nq10,nq11,nq12,nq13,nq14,nq15,nq16,nq17,nq18,nq19,nq20,nq21,nq22,nq23,nq24,nq25,px,py);pure3 pc(pqx,pqy,pz);
wire[15:0] ml,mh0,mh1;wire mc;reg[15:0]mlq,mhq0,mhq1;reg mcq;wire[31:0]mz;wire[7:0]mutp=nq0^8'h01;
split2 ms(mutp,nq1,nq2,nq3,nq4,nq5,nq6,nq7,nq8,nq9,nq10,nq11,nq12,nq13,nq14,nq15,nq16,nq17,nq18,nq19,nq20,nq21,nq22,nq23,nq24,nq25,ml,mh0,mh1,mc);split3 mt(mlq,mhq0,mhq1,mcq,mz);
always@(posedge clk)begin mlq<=ml;mhq0<=mh0;mhq1<=mh1;mcq<=mc;end
always@(posedge clk)begin lq<=lo;hq0<=h0;hq1<=h1;cq<=carry;c<=z;pqx<=px;pqy<=py;pureres<=pz;drop<={16'(hq0+hq1),lq};phase<=a*b;flip<=mz;end
integer i,bad=0,m0=0,m1=0,m2=0,car=0;reg[63:0]rng=64'h123456789abcdef1;
initial begin a=0;b=0;repeat(5)@(negedge clk);for(i=0;i<200040;i=i+1)begin
if(i<8)begin a=32'hffffffff>>i;b=16'hffff;end
else if(i<24)begin a=32'hffffffff;b=16'h1<<(i-8);end
else if(i<40)begin a=32'h1<<(i-24);b=16'hffff;end
else begin rng=rng^(rng<<13);rng=rng^(rng>>7);rng=rng^(rng<<17);a=rng[31:0];b=rng[63:48];end
@(negedge clk);if(g!==c||g!==pureres)bad=bad+1;if(g!==drop)m0=m0+1;if(g!==phase)m1=m1+1;if(g!==flip)m2=m2+1;if(cq)car=car+1;
end
$display("STREAM samples=%0d mismatch=%0d droppedcarry_caught=%0d wrongphase_caught=%0d bitflip_caught=%0d carry16=%0d",i,bad,m0,m1,m2,car);if(bad||!m0||!m1||!m2)$fatal;$finish;end endmodule
