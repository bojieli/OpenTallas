`timescale 1ns/1ps
module tb_s81sl_cap_phase;
reg clk=0,rst_n=0;always #5 clk=~clk;
reg [559:0]stim[0:11899];reg [559:0]i=0;wire [559:0]q;
integer n=-1,mode=0,errors=0,seen=0,e=-1,fd,rc,t,l,p,a,key;reg[31:0]d;reg[159:0]cfg[0:11899];reg[11899:0]cv=0;
reg[31:0]ex[integer];bit taken[integer];string dir;
initial begin
 if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");rc=$value$plusargs("MODE=%d",mode);
 $readmemh({dir,"/stim.hex"},stim);
 for(integer j=0;j<11900;j++)cfg[j]=0;
 fd=$fopen({dir,"/cfg.txt"},"r");rc=$fscanf(fd,"%d %h\n",t,cfg[0]);
 while(rc==2)begin cfg[t]=cfg[0];cv[t]=1;rc=$fscanf(fd,"%d %h\n",t,cfg[0]);end
 fd=$fopen({dir,"/expected.txt"},"r");rc=$fscanf(fd,"%d %d %d %d %h\n",t,l,p,a,d);
 while(rc==5)begin key=t*20480+l*4096+a;if(ex.exists(key))$fatal(1,"duplicate expected address");ex[key]=d;rc=$fscanf(fd,"%d %d %d %d %h\n",t,l,p,a,d);end
end
wire [9:0]wv;wire[119:0]wa;wire[319:0]wd;wire fault;
ot_s81sl_cap_phase #(.ENABLE(1)) phase(.clk(clk),.rst_n(rst_n),.i(i),.o(q));
ot_s81sl_cap cap(.clk(clk),.rst_n(rst_n),.rt_w(mode==1?i[279:0]:q[279:0]),.rt_e(mode==1?i[559:280]:q[559:280]),
 .cfg_v(n>=0&&n<11900?cv[n]:1'b0),.cfg_d(n>=0&&n<11900?cfg[n]:160'd0),
 .cw_s_v(wv[5:0]),.cw_s_a(wa[71:0]),.cw_s_d(wd[191:0]),.cw_n_v(wv[9:6]),.cw_n_a(wa[119:72]),.cw_n_d(wd[319:192]),.fault(fault));
always @(negedge clk)begin
 if(n==0)rst_n=1;
 if(n+1<11900)i=stim[n+1];else i=0;
end
reg first_collision=0;
always @(posedge clk)if(mode==1&&!first_collision&&cap.g_hard.u_tw.u_nc.fwd2)begin
 first_collision=1;
 $display("FIRST_N4_F1 observed_edge=%0d left_tag=%h right_tag=%h left_norm_row=%0d right_norm_row=%0d",n+1,
  cap.g_hard.u_tw.u_nc.wa_t[1],cap.g_hard.u_tw.u_nc.wb_t[1],
  cap.g_hard.u_tw.u_nc.wa_t[1][28:13],cap.g_hard.u_tw.u_nc.wb_t[1][28:13]);
end
always @(posedge clk)begin
 n=n+1;
 if(n>=0&&n<11900&&cv[n])e++;
 #1;
 for(integer z=0;z<10;z++)if(wv[z])begin
  key=e*20480+(z/2)*4096+wa[12*z+:12];seen++;
  if(!ex.exists(key)||taken.exists(key)||wd[32*z+:32]!==ex[key])begin errors++;$display("CW_BAD n=%0d key=%0d data=%h expected=%h",n,key,wd[32*z+:32],ex[key]);end
  taken[key]=1;
 end
 if(n==11899)begin
  if(mode==0 && (errors||seen!=512||fault))$fatal(1,"PHASE_FAIL errors=%0d seen=%0d fault=%b",errors,seen,fault);
  if(mode==1 && !fault)$fatal(1,"NEGATIVE_BLIND");
  $display("PHASE_RESULT mode=%0d errors=%0d writes=%0d fault=%b",mode,errors,seen,fault);$finish;
 end
end
endmodule
