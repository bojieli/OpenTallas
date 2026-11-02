module tb;
 reg clk=0;always #5 clk=~clk;
 reg arst_n=0; wire[44:0] a,b,m;wire ao,bo,mo;
 old_tree old(.clk(clk),.arst_n(arst_n),.observations(a),.rst_o_0(ao));
 new_tree good(.clk(clk),.arst_n(arst_n),.observations(b),.rst_o_0(bo));
 mutant_tree bad(.clk(clk),.arst_n(arst_n),.observations(m),.rst_o_0(mo));
 reg[6:0] expected=0; integer cycle=0,checks=0,mutants=0,i,j,p;reg trace=0;reg[44:0] pa=0,pb=0;
 always @(posedge clk)begin
  expected<={expected[5:0],arst_n};cycle=cycle+1;
  #1;
  if(cycle>=64)begin
   for(i=0;i<45;i=i+1)begin
    if(a[i]!==b[i] || a[i]!==expected[6])$fatal(1,"LOCKSTEP idx=%0d cycle=%0d old=%b new=%b expected=%b",i,cycle,a[i],b[i],expected[6]);
    if(m[i]!==a[i])mutants=mutants+1;
    if(trace && (a[i]!==pa[i] || b[i]!==pb[i]))$display("EDGE %0d %0d %b %b",i,cycle,a[i],b[i]);
    checks=checks+1;
   end
   if(ao!==bo || ao!==expected[6])$fatal(1,"DEDICATED_OUT mismatch cycle%0d",cycle);
  end
  pa=a;pb=b;
 end
 task drive(input reg value,input integer n);integer k;begin
  for(k=0;k<n;k=k+1)begin @(negedge clk);arst_n=value;end
 end endtask
 initial begin
  drive(0,64);trace=1;drive(1,32);drive(0,5);drive(1,32);drive(0,64);drive(1,32);drive(0,10);drive(1,32);trace=0;
  for(p=0;p<512;p=p+1)begin
   for(j=0;j<9;j=j+1)drive((p>>j)&1,1);
  end
  drive(0,16);#2;if(mutants==0)$fatal(1,"MUTANT_NOT_CAUGHT");
  $display("PASS all45_plus_dedicatedout checks=%0d cycles=%0d mutant_mismatches=%0d",checks,cycle,mutants);$finish;
 end
endmodule
