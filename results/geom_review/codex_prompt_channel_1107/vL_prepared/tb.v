module tb;reg ck=0,rst=0,e=0,mb=0;reg[3:0]st=0;wire[31:0] g,n,m;
gold G(ck,rst,e,mb,st,g);cand N(ck,rst,e,mb,st,n);mutant M(ck,rst,e,mb,st,m);
integer i,j,diffs=0;reg[31:0]seeds[0:11];
always #5 ck=~ck;
task check;begin @(posedge ck);#1;if(g!==n)$fatal(1,"mismatch %h %h",g,n);if(g!==m)diffs=diffs+1;end endtask
initial begin
seeds[0]=0;seeds[1]='hfd;seeds[2]='hfe;seeds[3]='hff;seeds[4]='hfffd;seeds[5]='hfffe;seeds[6]='hffff;seeds[7]='hfffffd;seeds[8]='hfffffe;seeds[9]='hffffff;seeds[10]='hfffffffe;seeds[11]='hffffffff;
#1;rst=1;#1;rst=0;check();@(negedge ck);rst=1;
for(j=0;j<12;j=j+1)begin
@(negedge ck);G.count=seeds[j];N.count=seeds[j];M.count=seeds[j];
N.ot_creq_c8=&seeds[j][7:0];N.ot_creq_c16=&seeds[j][15:0];N.ot_creq_c24=&seeds[j][23:0];
M.ot_creq_c8=&seeds[j][7:0];M.ot_creq_c16=&seeds[j][15:0];M.ot_creq_c24=&seeds[j][23:0];
for(i=0;i<40;i=i+1)begin e=1;mb=1;st=11;check();@(negedge ck);end
end
for(i=0;i<10000;i=i+1)begin e=$random;mb=$random;st=$random;check();@(negedge ck);end
rst=0;#1;if(g!==0 || n!==0)$fatal(1,"async reset");check();@(negedge ck);rst=1;
for(i=0;i<100;i=i+1)begin e=1;mb=1;st=11;check();@(negedge ck);end
if(diffs==0)$fatal(1,"mutant not distinguished");$display("PASS exact extracted sequential blocks; mutant %0d differences",diffs);$finish;
end endmodule
