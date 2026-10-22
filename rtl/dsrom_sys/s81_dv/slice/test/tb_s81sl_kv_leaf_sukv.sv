`timescale 1ns/1ps
// RTLGAP-SUKV 10-21: ot_s81sl_kv_leaf CNIK=1 / CP=1 bench (G-L2-L20-HW).  Real VM pair port model with a fixed read
// latency VLAT (the VP extension's 4 edges by default).  Phases (files in the run dir, tools/s81_dv/rtlgap_sukv_1021):
//   GK gsel 3 <- img_gk3.mem (CN gain), GK gsel 0 <- img_gk0.mem (IK gain, 384 zero + k_norm 128),
//   img_main.mem: [+CP] CP job slot0 0 / slot1 256 -> out 692 (checked vs exp_cp.mem BF16-widened rows and the lanes'
//   FP32 y vs exp_cp32.mem), then CN job (params 672, operands 692, obase 168, nbase 200) vs exp_cn.mem (16 QDQ,
//   16 raw, 16 norm rows), img_ik.mem: IK job (params 672, operands 692 with 24 zero rows, obase 168) vs exp_ik.mem.
//   [+KV] KV regression on the same build: img_kvg.mem GK gsel 0, img_kv.mem KV job vs exp_kv.mem (25 rows).
// Every job: no output event before its last input read (KV-class), fixed finish ages printed (calendar pricing).
module tb_s81sl_kv_leaf_sukv #(parameter integer VLAT = 4, CNIK_MUT = 0, CP_MUT = 0, HARD_RQ = 0);
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,c_v=0;reg[159:0]c_d=0;
 wire busy,done,fault,xrv,xwv;wire[9:0]xra,xwa;wire[7:0]xwm;wire[255:0]xwd;
 reg xqv;reg[255:0]xqd;
 reg[127:0]mem[0:1023];reg[127:0]img[0:1023];
 reg[511:0]ecp[0:31];reg[31:0]ecp32[0:511];reg[511:0]ecn[0:47];reg[511:0]eik[0:7];reg[511:0]ekv[0:24];
 ot_s81sl_kv_leaf #(.CNIK(1),.CP(1),.HARD_RQ(HARD_RQ),.CP_MUT(CP_MUT),.CNIK_MUT(CNIK_MUT)) dut(.clk(clk),.rst_n(rst_n),.c_v(c_v),.c_d(c_d),
  .busy(busy),.done(done),.fault(fault),.x_rv(xrv),.x_ra(xra),.x_qv(xqv),.x_qd(xqd),.x_wv(xwv),.x_wa(xwa),.x_wm(xwm),.x_wd(xwd));
 // VM: VLAT-edge pair reads, masked pair writes
 reg [VLAT:1] qv_l; reg [255:0] qd_l [1:VLAT];
 integer cycle=0,writes=0,bad=0,reads=0,lastread=-1,firstev=-1,k,fage=-1,lage=-1,nev=0;
 always @(posedge clk)begin
  qv_l[1]<=xrv;qd_l[1]<={mem[xra+1],mem[xra]};
  for(k=2;k<=VLAT;k=k+1)begin qv_l[k]<=qv_l[k-1];qd_l[k]<=qd_l[k-1];end
  if(xrv)begin reads=reads+1;lastread=cycle;end
  if(xwv)begin
   writes=writes+1;
   for(integer m=0;m<8;m=m+1)if(xwm[m])mem[xwa+m/4][32*(m%4)+:32]<=xwd[32*m+:32];
  end
 end
 always @(*)begin xqv=qv_l[VLAT];xqd=qd_l[VLAT];end
 initial qv_l=0;
 // first bank output event (KV-class jobs) must follow the last input read
 reg checking=0;
 always @(negedge clk)if(rst_n)begin
  cycle=cycle+1;
  if(checking && (|dut.ov))begin if(firstev<0)begin firstev=cycle;fage=dut.age;end lage=dut.age;nev=nev+$countones(dut.ov);end
 end
 // pool FP32 probe: the lanes' y as each group is written
 integer np32=0;
 always @(negedge clk)if(rst_n && dut.g_cp.u_pool.lo_v[0])begin
  for(integer m=0;m<8;m=m+1)begin
   if(dut.g_cp.y32[32*m+:32]!==ecp32[8*np32+m])begin
    if(bad<8)$display("SUKV CP32 mismatch feature=%0d got=%h want=%h",8*np32+m,dut.g_cp.y32[32*m+:32],ecp32[8*np32+m]);
    bad=bad+1;
   end
  end
  np32=np32+1;
 end
 task load(input string f);
  integer i;
  begin $readmemh(f,img);for(i=0;i<1024;i=i+1)mem[i]=img[i];end
 endtask
 task job(input[3:0]kind,input[1:0]gs,input[9:0]a0,input[9:0]a1,input[9:0]ob,input string tag);
  reg[127:0]im;integer t0,r0,w0;
  begin
   im=0;im[3:0]=kind;
   if(kind==14)im[13:4]=ob;else begin im[5:4]=gs;im[31:16]=1024;end
   firstev=-1;fage=-1;lage=-1;nev=0;r0=reads;w0=writes;
   @(negedge clk);c_d={im,8'd32,a1,a0,4'd15};c_v=1;t0=cycle;
   @(negedge clk);c_v=0;
   wait(done);@(negedge clk);
   $display("SUKV_JOB %s kind=%0d finish_edges=%0d reads=%0d pair_writes=%0d events=%0d first_event_age=%0d last_event_age=%0d first_event=%0d last_read=%0d fault=%0d",
            tag,kind,cycle-t0,reads-r0,writes-w0,nev,fage,lage,firstev,lastread,fault);
   if(fault)$fatal(1,"SUKV FAIL job fault %s",tag);
   if(kind!=14 && kind!=7 && firstev>=0 && firstev<=lastread)$fatal(1,"SUKV FAIL output before last input read %s",tag);
  end
 endtask
 task check(input string tag,input integer n,input integer unit0,input integer stride_row);
  integer i,j;
  begin
   for(i=0;i<n;i=i+1)for(j=0;j<16;j=j+1)begin
    reg[31:0]got,want;
    got=mem[unit0+4*i+j/4][32*(j%4)+:32];
    case(tag)
     "CP":want=ecp[i][32*j+:32];
     "CNQ":want=ecn[i][32*j+:32];
     "CNR":want=ecn[16+i][32*j+:32];
     "CNN":want=ecn[32+i][32*j+:32];
     "IKQ":want=eik[i][32*j+:32];
     "IKR":want=eik[4+i][32*j+:32];
     default:want=ekv[i][32*j+:32];
    endcase
    if(tag=="KV" && i==8 && j>=8)continue;
    if(got!==want)begin
     if(bad<12)$display("SUKV %s mismatch row=%0d word=%0d got=%h want=%h",tag,i,j,got,want);
     bad=bad+1;
    end
   end
  end
 endtask
 initial begin
  $readmemh("exp_cn.mem",ecn);$readmemh("exp_ik.mem",eik);
  if($test$plusargs("CP"))begin $readmemh("exp_cp.mem",ecp);$readmemh("exp_cp32.mem",ecp32);end
  if($test$plusargs("KV"))$readmemh("exp_kv.mem",ekv);
  repeat(64)@(negedge clk);rst_n=1;repeat(128)@(negedge clk);
  load("img_gk3.mem");job(7,3,528,896,0,"GK3");
  load("img_gk0.mem");job(7,0,528,896,0,"GK0");
  load("img_main.mem");
  if($test$plusargs("CP"))begin
   job(14,0,0,256,692,"CP");
   check("CP",32,692,4);
   if(np32!=64)begin $display("SUKV CP groups=%0d",np32);bad=bad+1;end
  end
  checking=1;job(12,3,672,692,0,"CN");checking=0;
  check("CNQ",16,672,4);check("CNR",16,736,4);check("CNN",16,800,4);
  load("img_ik.mem");
  checking=1;job(13,0,672,692,0,"IK");checking=0;
  check("IKQ",4,672,4);check("IKR",4,688,4);
  if($test$plusargs("KV"))begin
   load("img_kvg.mem");job(7,0,528,896,0,"GKKV");
   load("img_kv.mem");checking=1;job(1,0,672,692,0,"KV");checking=0;
   check("KV",25,672,4);
  end
  $display("SUKV bad=%0d fault=%0d cycles=%0d",bad,fault,cycle);
  if(bad||fault)$fatal(1,"SUKV FAIL");
  $display("SUKV PASS CN/IK on the production KV bank + CP pool through native VM pairs (VLAT %0d)",VLAT);$finish;
 end
 initial begin repeat(20000)@(negedge clk);$fatal(1,"SUKV FAIL finite calendar");end
endmodule
