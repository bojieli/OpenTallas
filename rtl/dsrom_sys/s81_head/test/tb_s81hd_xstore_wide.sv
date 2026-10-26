`timescale 1ns/1ps
module tb_s81hd_xstore_wide;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,load_begin=0,load_v=0,wide_v=0,issue=0;
 reg[511:0]load_d;reg[1023:0]wide_d;
 wire go,xv,busy,done,fault,wgo,wxv,wbusy,wdone,wfault,mgo,mxv,mbusy,mdone,mfault;
 wire[255:0]xa,xb,wxa,wxb,mxa,mxb;
 ot_s81hd_xstore_replay gold(.*);
 ot_s81hd_xstore_replay #(.LOAD_W(1024))wide(.ck(ck),.rst_n(rst_n),.load_begin(load_begin),.load_v(wide_v),.load_d(wide_d),.issue(issue),.go(wgo),.xv(wxv),.busy(wbusy),.done(wdone),.fault(wfault),.xa(wxa),.xb(wxb));
 ot_s81hd_xstore_replay #(.LOAD_W(1024),.MUT_B_ADDR(1))mut(.ck(ck),.rst_n(rst_n),.load_begin(load_begin),.load_v(wide_v),.load_d(wide_d),.issue(issue),.go(mgo),.xv(mxv),.busy(mbusy),.done(mdone),.fault(mfault),.xa(mxa),.xb(mxb));
 reg[255:0]native_x[0:319];string xa_path,xb_path;
 integer seen=0,cyc=0,g=-1,poses=0,mutants=0;
 always @(posedge ck)begin
  #1;cyc=cyc+1;
  if(rst_n&&({wgo,wxv,wbusy,wdone,wfault}!=={go,xv,busy,done,fault}))$fatal(1,"control lockstep mismatch");
  if(go)begin g=cyc;seen=0;end
  if(xv)begin
   if(cyc!=g+5+seen)$fatal(1,"source edge mismatch");
   if(xa!==native_x[seen%256]||xb!==native_x[256+seen%64]||wxa!==xa||wxb!==xb)$fatal(1,"wide/source stream mismatch m%0d",seen);
   if(mxa!==wxa||mxb!==wxb)mutants=mutants+1;
   seen=seen+1;
  end
  if(done)begin if(seen!=8269)$fatal(1,"length");poses=poses+1;end
 end
 task tick;@(negedge ck);endtask
 initial begin
  if(!$value$plusargs("XA=%s",xa_path)||!$value$plusargs("XB=%s",xb_path))$fatal(1,"native vectors required");
  $readmemh(xa_path,native_x,0,255);$readmemh(xb_path,native_x,256,319);
  repeat(3)tick();rst_n=1;load_begin=1;tick();load_begin=0;
  for(integer i=0;i<160;i++)begin
   load_v=1;load_d={native_x[2*i+1],native_x[2*i]};
   wide_v=i<80;
   if(i<80)wide_d={native_x[4*i+3],native_x[4*i+2],native_x[4*i+1],native_x[4*i]};
   tick();
  end
  load_v=0;wide_v=0;
  repeat(2)begin tick();issue=1;tick();issue=0;wait(done);tick();end
  if(poses!=2||mutants==0)$fatal(1,"positions/mutant count");
  $display("XSTORE_WIDE PASS native_pairs=16538 wide_load=80x1024 reference_load=160x512 public_stream=G+5 mutant_differences=%0d",mutants);$finish;
 end
endmodule
