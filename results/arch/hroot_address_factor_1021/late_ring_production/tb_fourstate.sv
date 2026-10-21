module tb;
reg[330:0] stimulus,base;
wire[255:0] st_d=stimulus[255:0];wire[31:0] st_row=stimulus[287:256],s_gs=stimulus[319:288];wire[2:0] s_stk=stimulus[322:320],st_ph=stimulus[325:323];wire[4:0] st_sec=stimulus[330:326];
wire[127:0] refaddr,gotaddr;
original o(st_d,st_row,s_gs,s_stk,st_ph,st_sec,refaddr);
production_projection c(st_d,st_row,s_gs,s_stk,st_ph,st_sec,gotaddr);
integer n,i,t,k,checks=0;
task check;begin #1;if(gotaddr!==refaddr)$fatal(1,"n=%0d bit=%0d type=%0d stim=%h ref=%h got=%h",n,i,t,stimulus,refaddr,gotaddr);checks=checks+4;end endtask
initial begin
for(n=0;n<8;n=n+1)begin
 for(k=0;k<11;k=k+1)base[k*30+:30]=$random;
 base[330]=$random;
 case(n)0:base=0;1:base='1;2:base[143:112]=0;3:base[143:112]=128;endcase
 stimulus=base;check;
 for(i=0;i<331;i=i+1)for(t=0;t<2;t=t+1)begin stimulus=base;stimulus[i]=t?1'bz:1'bx;check;end
end
for(n=0;n<1024;n=n+1)begin for(k=0;k<11;k=k+1)stimulus[k*30+:30]=$random;stimulus[330]=$random;check;end
$display("PRODUCTION_PROJECTION_4STATE_PASS vectors=%0d address_comparisons=%0d",checks/4,checks);$finish;
end endmodule
