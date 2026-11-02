`timescale 1ns/1fs
module tb_mu_native;
reg ck=0;always #0.416500 ck=~ck;
reg rst_n=0;wire[115:0]cmd;
reg wv=0,tv=0;reg[23:0]wa=0,ta=0;reg[511:0]wd=0;reg[1023:0]td=0;
reg[8:0]treq=0;wire lw;wire[1:0]lk;wire[23:0]la;wire[1023:0]ld;wire lf,lb,ldone;
reg[1023:0]pairs[0:3];integer u,j,l,k,active=-1,count=0,checks=0;reg[127:0]seen=0;reg[23:0]out_a;reg[31:0]out_d,expected;
qfd_dv_s8_flat dut (.ck(ck),.rst_n(rst_n),.cmd_i(cmd),.hr_i('0),.rs_s('0),.rs_n('0),.l9_i('0),.st_up_i('0),.st_dn_i('0),.sc_up_i('0),.sc_dn_i('0),.ch_up_i('0),.ch_dn_i('0),.ag_up_i('0),.treq_i('0));

reg pv=0,dv=0,cs=0;reg[9:0]pa=0;reg[2:0]da=0;reg[63:0]pd=0,dd=0;reg[1:0]cu=0;
wire[1:0]issued_user;wire cf,ready;wire[5:0]fc;reg[63:0]pw[0:1023];reg[127:0]entry;reg[115:0]word_cmd;integer x,issued=0; // low16 calendar words, high16 native decoded words
qfd_dv_cmd_cal_mu #(.NU(4),.UVM_STRIDE(4096),.PIDX_STRIDE(128),.TABLE_USER_RELOC(1),.BTAB_COMPACT(1),.UFOLD(1)) cal(
 .ck(ck),.rst_n(rst_n),.pw_v(pv),.pw_addr(pa),.pw_data(pd),.dw_v(dv),.dw_addr(da),.dw_data(dd),
 .start(cs),.stage(6'd1),.start_user(cu),.start_rng(1'b0),.start_first(10'd0),.start_cnt(10'd0),
 .cmd(cmd),.cmd_user(issued_user),.image_ready(ready),.fault(cf),.fault_code(fc));
qfd_dv_slice_tload #(.SLICE(0),.CAPTURE_STAGE(0),.LOCAL_JOIN(0),.NWC(34)) load(
 .ck(ck),.rst_n(rst_n),.treq(treq),.s_we(1'b0),.s_kind(2'd0),.s_addr(24'd0),.s_data(1024'd0),
 .tw_we(lw),.tw_kind(lk),.tw_addr(la),.tw_data(ld),.busy(lb),.done(ldone),.fault(lf));
task load_calendar;
 begin
 for(x=0;x<1024;x=x+1)pw[x]=0;
 // Real ROOT/STN words travel the native control decode. Their arithmetic
 // engines are excluded; the XA command is the actual native data witness.
 word_cmd=(116'd1344<<11)|(116'd1500<<36)|116'd7;entry=(128'd16<<116)|128'(word_cmd);pw[0]=entry[63:0];pw[1]=entry[127:64];
 word_cmd=(116'd4<<15)|(116'd1600<<26)|116'd5;entry=(128'd16<<116)|128'(word_cmd);pw[2]=entry[63:0];pw[3]=entry[127:64];
 word_cmd=(116'd11<<4)|116'd3;if($test$plusargs("MUT_PIDX"))word_cmd=(116'd9<<4)|116'd3;
 entry=(128'd16<<116)|128'(word_cmd);pw[4]=entry[63:0];pw[5]=entry[127:64];
 entry=(128'd16<<116)|128'd15;pw[8]=entry[63:0];pw[9]=entry[127:64];
 for(x=0;x<1024;x=x+1)begin pv=1;pa=10'(x);pd=pw[x];@(negedge ck);end
 pv=0;repeat(8)@(negedge ck);
 for(x=0;x<8;x=x+1)begin dv=1;da=3'(x);dd=(x==0)?64'h43414c4400000005:((x==2)?64'd3:((x==4)?64'h0000000000040001:64'd0));@(negedge ck);end
 dv=0;repeat(16)@(negedge ck);if(!ready||cf)$fatal(1,"CAL_SEAL ready%b fault%b code%h",ready,cf,fc);
 end
endtask
always @(negedge ck)if(rst_n)begin
 if(cf)$fatal(1,"LIVE_CAL_FAULT %h",fc);
 if(dut.sc_cfg[100])begin
 issued=issued+65536;
 if(active<0||dut.sc_cfg[91:68]!==24'(1344+4096*active)||dut.sc_cfg[66:43]!==24'(1500+4096*active))$fatal(1,"NATIVE_ROOT_DECODE");
 end
 if(dut.stn_cfg[28])begin
 issued=issued+65536;
 if(active<0||dut.stn_cfg[16:8]!==9'(4+((active==0)?0:200+72*active)))$fatal(1,"NATIVE_STN_DECODE");
 end
 if(dut.su_cmd[9])begin
 issued=issued+65536;
 if(active<0||dut.su_cmd[8:0]!==9'(11+128*active))$fatal(1,"NATIVE_SU_DECODE");
 end
 if(cmd[0])begin
 if(cmd[3:1]!=7)issued=issued+1;
 case(cmd[3:1])
 3:if(cmd[34:11]!==24'(1344+4096*issued_user)||cmd[59:36]!==24'(1500+4096*issued_user))$fatal(1,"LIVE_ROOT_BANK");
 2:if(cmd[23:15]!==9'(4+((issued_user==0)?0:200+72*issued_user))||cmd[52:51]!==issued_user)$fatal(1,"LIVE_STN_BANK");
 1:if(cmd[12:4]!==9'(11+128*issued_user))$fatal(1,"LIVE_SU_PIDX");
 7:if(cmd!==116'd15)$fatal(1,"LIVE_BOOT_SETID");
 default:$fatal(1,"LIVE_UNEXPECTED_CMD");
 endcase
 end
end

initial begin
 force dut.w16_we=wv;force dut.w16_addr=wa;force dut.w16_data=wd;
 force dut.tw_we=lw;force dut.tw_kind=lk;force dut.tw_addr=la;force dut.tw_data=ld;
 pairs[0]=1024'h0000000000000000000000000000000000000000000000004000201000001000000000000000000000000000000000000000000000400020000150000400000200000000000000000000017f0000000000000000000000004000001000001e030000010000000004400000008000000002600000004000000001100004000002;
 pairs[1]=1024'h0000000000000000000000000000000000000000000000004000201000001000000000000000001000000000000000000800000000400020000550000400000200000000000000000000017f0000000000000000000000004000001000001e03000001000000001440000000800000000a600000004000000005100004000002;
 pairs[2]=1024'h0000000000000000000000000000000000000000000000004000201000001000000000000000002000000000000000001000000000400020000950000400000200000000000000000000017f0000000000000000000000004000001000001e030000010000000024400000008000000012600000004000000009100004000002;
 pairs[3]=1024'h0000000000000000000000000000000000000000000000004000201000001000000000000000003000000000000000001800000000400020000d50000400000200000000000000000000017f0000000000000000000000004000001000001e03000001000000003440000000800000001a60000000400000000d100004000002;
 repeat(64)@(negedge ck);rst_n=1;repeat(64)@(negedge ck);
 repeat(16)@(negedge ck);
 load_calendar;
 for(u=0;u<4;u=u+1)begin
  for(j=0;j<128;j=j+16)begin
   wv=1;wa=24'(1344+4096*u+j);
   for(l=0;l<16;l=l+1)wd[32*l+:32]=32'h3f000000|(32'(u)<<16)|32'(j+l);
   if($test$plusargs("MUT_PAYLOAD")&&u==1&&j==0)wd[3*32+3]=~wd[3*32+3];
   @(negedge ck);
  end
  wv=0;treq={1'b1,6'd1,2'(u)};@(negedge ck);treq=0;
  repeat(128)@(negedge ck);if(lf)$fatal(1,"LIVE_LOADER_FAULT user%0d",u);

 end
 repeat(64)@(negedge ck);
 for(u=0;u<4;u=u+1)begin
  active=u;seen=0;count=0;
  cu=2'(u);cs=1;@(negedge ck);cs=0;
  repeat(300)@(negedge ck);
  if(count!=128||seen!=={128{1'b1}})$fatal(1,"MU_COVERAGE user=%0d count=%0d seen=%h idle=%b sufault=%b vmfault=%b",u,count,seen,dut.su_idle,dut.su_fault,dut.vm_fault);
  if(dut.su_fault||dut.vm_fault||cf||lf||dut.st_c[69]||dut.rp_fault)$fatal(1,"MU_NATIVE_FAULT user=%0d",u);
  $display("MU_USER_PASS user=%0d writes=%0d",u,count);active=-1;
 end
 if(issued!=786444)$fatal(1,"CAL_COMMAND_COUNT %0d decoded%0d",issued&65535,issued>>16);
 $display("MU_CALENDAR_NATIVE_XA_PASS users4 literalwords512 checks=%0d precision1fs period833ps MEMALIGN3 MIF0",checks);$finish;
end
always @(negedge ck)begin
 if(rst_n&&active>=0)begin
  for(k=0;k<8;k=k+1)if(dut.L_vm_we[k])begin
   out_a=dut.L_vm_waddr[24*k+:24];out_d=dut.L_vm_wdata[32*k+:32];
   if(out_a[23:22]!=2'd1||out_a[21:0]>=128)$fatal(1,"MU_DEST_MISMATCH user%0d addr%h",active,out_a);
   j=integer'(out_a[21:0]);expected=32'h3f000000|(32'(active)<<16)|32'(j);
   if(out_d!==expected||seen[j])$fatal(1,"MU_PAYLOAD_MISMATCH user%0d index%0d got%h expected%h duplicate%b",active,j,out_d,expected,seen[j]);
   seen[j]=1;count=count+1;checks=checks+1;
  end
 end
end
endmodule
