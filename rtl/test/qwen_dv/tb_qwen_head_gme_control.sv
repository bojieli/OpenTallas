`timescale 1fs/1fs
// COMPONENT ONLY: real decoder/calendar/storage + explicit availability fixture.
// No matrix execution, numeric results, transport or production dates claimed.
module tb_qwen_head_gme_control #(parameter MODE=2);
reg ck=0;always #416500 ck=~ck;
reg rst_n=0,pw_v=0,h_start=0,stage_start=0;
reg[9:0]pw_addr=0;reg[63:0]pw_data=0;reg[5:0]stage=37;
reg[23:0]x_oacc=0;reg[15:0]x_oprog=64;reg[94:0]avail=95'd3;
wire[379:0]rom_cmd,native_cmd;wire[15:0]me_observe;wire ready,fault;
reg[63:0]image[0:1023];reg[379:0]expected[0:3];
reg su_issue=0;reg[3:0]su_slice=0;reg[8:0]su_pc=0;wire[15:0]su_ob;wire su_fault;
qfd_dv_typed_su_observer #(.ENABLE(1)) su_obs(.ck(ck),.rst_n(rst_n),.su_issue(su_issue),.cmd_user(2'd0),.su_pidx(su_pc),.cmd_slice(su_slice),.observation(su_ob),.fault(su_fault));
always @(posedge ck)if(rst_n&&su_ob[15])x_oacc<=x_oacc+1;
integer old6=0,nochase=0,require_seen=-1;
integer native_fixture=1,busy=0,want_fault=0,seen=0,obs=0,edge_i=0,first=-1;
wire[379:0]cmd=rom_cmd[0]?rom_cmd:native_cmd;
generate if(MODE==0)begin:h
ot_qfd_tt_ctlm_static_hr_safe32_native32_1r #(.STAGE_ME(1),.SEGCAL(1)) dut(.rom_ret_i(avail),.native_ret(avail),.cp_active(1'b0),.me_image_ready(ready),.rom_cmd(rom_cmd),.native_cmd(native_cmd),.me_observe(me_observe),.ck_head(ck),.rst_n(rst_n),.h_start(h_start),.stage_start(stage_start),.stage(stage),.token(18'd0),.pos(18'd0),.prog_base(12'd28),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(pw_data),.x_oacc(x_oacc),.x_oidle(1'b1),.x_oprog(x_oprog),.x_orows(16'd48),.kv_ok(1'b1),.kv_write_drained(1'b1),.me_mem_ok(1'b1),.c_fault(fault));
end else begin:f
ot_qfd_tt_ctlm_static_hr_g5prep #(.STAGE_ME(1),.SEGCAL(1),.NATIVE_STATIC_DEPS(MODE==2)) dut(.rom_ret_i(avail),.native_ret(avail),.cp_active(1'b0),.me_image_ready(ready),.rom_cmd(rom_cmd),.native_cmd(native_cmd),.me_observe(me_observe),.ck_head(ck),.rst_n(rst_n),.h_start(h_start),.stage_start(stage_start),.stage(stage),.token(18'd0),.pos(18'd0),.prog_base(12'd28),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(pw_data),.x_oacc(x_oacc),.x_oidle(1'b1),.x_oprog(x_oprog),.x_orows(16'd48),.kv_ok(1'b1),.kv_write_drained(1'b1),.me_mem_ok(1'b1),.c_fault(fault),.ck_pm0(ck),.ck_pm1(ck));
end endgenerate
always @(negedge ck)if(rst_n)begin
 edge_i++;
 if(fault&&first<0)first=edge_i;
 if(rom_cmd[0]&&native_cmd[0])$fatal(1,"TWO_ENDPOINT_GO");
 if(cmd[0])begin
  $display("GME_CMD index=%0d edge=%0d word=%095h",seen,edge_i,cmd);
  if(seen>=4||cmd!==expected[seen])$fatal(1,"GME_FIELD_ORDER_OR_BOUNDS");
  seen++;
 end
 if(me_observe[15])begin
  if(me_observe[13:12]!=1||me_observe[11:0]!=28+obs)$fatal(1,"GME_OBSERVER_PC");
  obs++;
 end
end
initial begin
 if(!$value$plusargs("NATIVE=%d",native_fixture))native_fixture=1;
 if(!$value$plusargs("BUSY=%d",busy))busy=0;
 if(!$value$plusargs("FAULT=%d",want_fault))want_fault=0;
 if(!$value$plusargs("OLD6=%d",old6))old6=0;
 if(!$value$plusargs("NOCHASE=%d",nochase))nochase=0;
 if(!$value$plusargs("REQUIRE_SEEN=%d",require_seen))require_seen=-1;
 if(nochase)$readmemh("input/program_nochase.memh",image);else if(old6)$readmemh("input/program_old6.memh",image);else $readmemh("input/program.memh",image);$readmemh("input/cmd.memh",expected);
 repeat(8)@(negedge ck);rst_n=1;
 repeat(16)@(negedge ck);
 for(integer i=0;i<1024;i++)begin pw_v=1;pw_addr=i;pw_data=image[i];@(negedge ck);end
 pw_v=0;repeat(80)@(negedge ck);
 if(!ready||fault)$fatal(1,"PROGRAMME_SEAL");
 x_oacc=0;x_oprog=native_fixture?48:64;
 if(busy)avail=0;
 repeat(32)@(negedge ck);stage_start=1;@(negedge ck);stage_start=0;
 repeat(16)@(negedge ck);h_start=1;@(negedge ck);h_start=0;
 for(integer t=0;t<5300;t++)begin
 su_issue=native_fixture&&t>=128&&t<=150&&t%2==0;
 su_slice=(t-128)/2;su_pc=(t==128)?17:16;
 @(negedge ck);
 end
 su_issue=0;
 if(native_fixture&&(x_oacc!=12||su_fault))$fatal(1,"ACTUAL_NATIVE_SU_OBSERVER_COUNT");
 $display("GME_SUMMARY MODE=%0d NATIVE=%0d busy=%0d seen=%0d obs=%0d fault=%0d first=%0d",MODE,native_fixture,busy,seen,obs,fault,first);
 if(require_seen>=0&&seen!=require_seen)$fatal(1,"CAUSAL_GO_COUNT");
 if(fault!=want_fault)$fatal(1,"GME_FAULT_CONTROL");
 if(!want_fault&&(seen!=4||obs!=4))$fatal(1,"GME_FOUR_CHUNKS_REQUIRED");
 $display("PASS_HEAD_GME_CONTROL_COMPONENT");$finish;
end
endmodule
