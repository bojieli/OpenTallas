// S81 kv_leaf t2 A|B seam: the COMPILED SUKV programme, played on its own dates (kv_seam_image.py image.txt).
// The bench is the A side.  Nothing here waits for done or busy: input rows commit, commands are captured and outputs are
// read on the compiled sampled edges only, as the program-timed slice does.  A wrong date is a fault or a data mismatch.
// VLAT = VM read loop at the leaf port (4; 5 with OT_S81SL_VP_SRAMREG): the store is read VLAT - 3 edges after the port
// edge and a write commits VLAT - 3 edges after it, read before write.
`timescale 1ns/1ps
module tb_s81sl_kv_prog_timed #(parameter integer VLAT = 4, HARD_RQ = 0, parameter [47:0] KV_XD = 48'd0, parameter [63:0] KV_KST = 64'd0, parameter integer KV_XMRG = 0, KV_YBASE = 0, SEAM_IN = 0, SEAM_OUT = 0, parameter [63:0] KV_XST = 64'd0, parameter integer KV_CPQ = 3);
 localparam integer SA = VLAT - 3;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,c_v=0;reg[159:0]c_d=0;
 wire busy,done,fault,xrv,xwv;wire[9:0]xra,xwa;wire[7:0]xwm;wire[255:0]xwd;
 wire dc_v,dxqv,d_busy,d_done,d_fault,d_xrv,d_xwv;wire[159:0]dc_d;wire[255:0]dxqd,d_xwd;wire[9:0]d_xra,d_xwa;wire[7:0]d_xwm;
 reg xqv;reg[255:0]xqd;
 ot_s81sl_kv_leaf #(.CNIK(1),.CP(1),.HARD_RQ(HARD_RQ),.KV_XD(KV_XD),.KV_KST(KV_KST),.KV_XMRG(KV_XMRG),.KV_YBASE(KV_YBASE),.KV_XST(KV_XST),.KV_CPQ(KV_CPQ)) dut(.clk(clk),.rst_n(rst_n),.c_v(dc_v),.c_d(dc_d),
  .busy(d_busy),.done(d_done),.fault(d_fault),.x_rv(d_xrv),.x_ra(d_xra),.x_qv(dxqv),.x_qd(dxqd),.x_wv(d_xwv),.x_wa(d_xwa),.x_wm(d_xwm),.x_wd(d_xwd));
 ot_hdc_delay #(.W(1+160+1+256),.D(SEAM_IN),.RESET(1)) u_seam_in(.clk(clk),.rst_n(rst_n),.d({c_v,c_d,xqv,xqd}),.q({dc_v,dc_d,dxqv,dxqd}));
 ot_hdc_delay #(.W(5+20+8+256),.D(SEAM_OUT),.RESET(1)) u_seam_out(.clk(clk),.rst_n(rst_n),
  .d({d_busy,d_done,d_fault,d_xrv,d_xwv,d_xra,d_xwa,d_xwm,d_xwd}),.q({busy,done,fault,xrv,xwv,xra,xwa,xwm,xwd}));
 // ---- leaf store
 reg[127:0]mem[0:1023];reg[127:0]img[0:1023];
 reg [SA-1:0] ra_v=0,wa_v=0;reg[9:0]ra_a[0:SA-1],wa_a[0:SA-1];reg[7:0]wa_m[0:SA-1];reg[255:0]wa_d[0:SA-1];
 reg q1_v=0,q2_v=0;reg[255:0]q1,q2;
 // ---- programme
 localparam integer ME=256;
 integer nev=0,ep=0;
 string op[0:ME-1],file[0:ME-1],kd[0:ME-1];integer ev[0:ME-1],a0[0:ME-1],a1[0:ME-1];reg[159:0]cmd[0:ME-1];
 reg[511:0]ecp[0:31];reg[511:0]ecn[0:47];reg[511:0]eik[0:7];reg[511:0]ekv[0:24];
 integer edge_n=-1000,bad=0,late=0,reads_out=0,k,nchk=0,ncmd=0,lastrd=-1,firstwr[0:31],jobn=-1,lastw[0:31];
 integer fd,rc,x0,x1,last_edge=0;string t,s,k0;
 task cmprow(input string tag,input integer base,input integer n,input integer sel,input integer off);
  integer i,j;reg[31:0]got,want;integer miss;
  begin miss=0;
   for(i=0;i<n;i=i+1)for(j=0;j<16;j=j+1)begin
    if(sel==3 && i==8 && j>=8)continue;
    got=mem[base+4*i+j/4][32*(j%4)+:32];
    case(sel)0:want=ecp[i][32*j+:32];1:want=ecn[off+i][32*j+:32];2:want=eik[off+i][32*j+:32];default:want=ekv[i][32*j+:32];endcase
    if(got!==want)miss=miss+1;
   end
   nchk=nchk+1;bad=bad+miss;
   $display("KVPROG READ %s edge=%0d base=%0d words=%0d mismatches=%0d",tag,edge_n,base,16*n,miss);
  end
 endtask
 always @(posedge clk)begin
  edge_n=edge_n+1;
  // store pipeline: the read sees the store before this edge's commit
  ra_v[0]<=xrv;ra_a[0]<=xra;wa_v[0]<=xwv;wa_a[0]<=xwa;wa_m[0]<=xwm;wa_d[0]<=xwd;
  for(k=1;k<SA;k=k+1)begin ra_v[k]<=ra_v[k-1];ra_a[k]<=ra_a[k-1];wa_v[k]<=wa_v[k-1];wa_a[k]<=wa_a[k-1];wa_m[k]<=wa_m[k-1];wa_d[k]<=wa_d[k-1];end
  q1_v<=ra_v[SA-1];q1<={mem[ra_a[SA-1]+1],mem[ra_a[SA-1]]};q2_v<=q1_v;q2<=q1;
  xqv<=q2_v;xqd<=q2;
  if(ra_v[SA-1])lastrd=edge_n;
  if(wa_v[SA-1])begin
   if(jobn>=0 && firstwr[jobn]<0)firstwr[jobn]=edge_n;
   for(integer m=0;m<8;m=m+1)if(wa_m[SA-1][m])mem[wa_a[SA-1]+m/4][32*(m%4)+:32]<=wa_d[SA-1][32*m+:32];
  end
  // compiled events of this edge
  for(k=0;k<nev;k=k+1)if(ev[k]==edge_n)begin
   if(op[k]=="L")begin $readmemh(file[k],img);for(integer r=a0[k];r<=a1[k];r=r+1)mem[r]<=img[r];end
   if(op[k]=="R")begin
    if(kd[k]=="CP")cmprow("CP",692,32,0,0);
    if(kd[k]=="CN")begin cmprow("CNQ",672,16,1,0);cmprow("CNR",736,16,1,16);cmprow("CNN",800,16,1,32);end
    if(kd[k]=="IK")begin cmprow("IKQ",672,4,2,0);cmprow("IKR",688,4,2,4);end
    if(kd[k]=="KV")cmprow("KV",672,25,3,0);
   end
   if(op[k]=="W" && firstwr[a0[k]]!=edge_n)begin late=late+1;$display("KVPROG DATE first write job %0d compiled=%0d measured=%0d",a0[k],edge_n,firstwr[a0[k]]);end
   if(op[k]=="E" && lastrd>edge_n)begin late=late+1;end
   // port free: the slice muxes the leaf port on busy, so the A-side busy must be low on the compiled free edge
   if(op[k]=="F" && busy)begin late=late+1;$display("KVPROG DATE port free job %0d compiled=%0d busy=1",a0[k],edge_n);end
  end
 end
 // a job's last store read must not come after its compiled last-read bound (checked when the next command is captured)
 integer ebound[0:31];
 always @(negedge clk)begin
  c_v=0;
  for(integer q=0;q<nev;q=q+1)if(op[q]=="C" && ev[q]==edge_n+1)begin
   if(jobn>=0 && lastrd>ebound[jobn])begin late=late+1;$display("KVPROG DATE last read job %0d compiled=%0d measured=%0d",jobn,ebound[jobn],lastrd);end
   jobn=jobn+1;ncmd=ncmd+1;c_v=1;c_d=cmd[q];
   $display("KVPROG CMD job=%0d edge=%0d c_d=%h",jobn,ev[q],cmd[q]);
  end
 end
 initial begin
  for(k=0;k<32;k=k+1)begin firstwr[k]=-1;ebound[k]=1<<30;end
  for(k=0;k<1024;k=k+1)mem[k]=0;
  $readmemh("exp_cp.mem",ecp);$readmemh("exp_cn.mem",ecn);$readmemh("exp_ik.mem",eik);$readmemh("exp_kv.mem",ekv);
  if(!$value$plusargs("IMAGE=%s",s))$fatal(1,"KVPROG needs +IMAGE=");
  fd=$fopen(s,"r");if(fd==0)$fatal(1,"KVPROG no image");
  while($fscanf(fd,"%s",t)==1)begin
   op[nev]=t;
   if(t=="L")rc=$fscanf(fd,"%d %s %d %d",ev[nev],file[nev],a0[nev],a1[nev]);
   else if(t=="C")rc=$fscanf(fd,"%d %h",ev[nev],cmd[nev]);
   else if(t=="F")rc=$fscanf(fd,"%d %d",ev[nev],a0[nev]);
   else if(t=="E")begin rc=$fscanf(fd,"%d %d",ev[nev],a0[nev]);ebound[a0[nev]]=ev[nev];end
   else rc=$fscanf(fd,"%d %d %s",ev[nev],a0[nev],kd[nev]);
   if(ev[nev]>last_edge)last_edge=ev[nev];
   nev=nev+1;
  end
  repeat(64)@(negedge clk);rst_n=1;repeat(128)@(negedge clk);
  edge_n=0;
  while(edge_n<last_edge+8)@(negedge clk);
  $display("KVPROG commands=%0d reads=%0d mismatches=%0d dates_off=%0d fault=%0d",ncmd,nchk,bad,late,fault);
  if(bad||late||fault||nchk!=7||ncmd!=7)$fatal(1,"KVPROG FAIL");
  $display("KVPROG PASS");$finish;
 end
endmodule
