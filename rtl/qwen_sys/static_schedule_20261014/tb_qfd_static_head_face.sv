`timescale 1ns/1ps
// Real head/IS/program write path/calendar/GO stations; explicit engine status
// stimuli. PSRAM0 tests the source FF store; PSRAM1 uses the source-pinned
// production SRAM functional model. Physical clocks and actual endpoint/VM
// composition require separate admitted gates.
module tb_qfd_static_head_face;
 parameter MUT_CONTEXT=0,CP_BUSY=0,ACTIVE_WRITE=0,PSRAM=0,DENSE_IMAGE=0;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,start=0,pv=0;reg[9:0]pa=0;reg[63:0]pd=0;
 reg[17:0]token=1,pos=7;
 reg[94:0]ret=95'd3;
 wire[379:0]cmd;wire[55:0]cp;wire[15:0]obs;wire ctx,ce,cf,me_ready;wire[75:0]program_obs;
 wire[17:0]nt,np;reg[1023:0]rom[0:7];reg[63:0]image[0:1023];string path,image_path;
 integer j,k,c,me_seen=0,cp_seen=0,ctx_seen=0,sent=0,observed=0;
 reg before_me,before_cp;reg[11:0]before_pc;
 localparam[55:0]COPY={7'd64,24'd8192,24'd8192,1'b1};
 qfd_tt_ctlm_head_static #(.DENSE_IMAGE(DENSE_IMAGE),.PSRAM(PSRAM))d(
 .clk(clk),.ck_sched(clk),.cp_active(CP_BUSY?1'b1:1'b0),.cp(cp),.layer_context_v(ctx),.native_tok(nt),.native_pos(np),
 .rst_n(rst_n),.h_start(start),.token(token),.pos(pos),.prog_base(12'd0),
 .pw_v(pv),.pw_addr(pa),.pw_data(pd),.x_oacc(24'd3),.x_oidle(1'b1),.x_oprog(16'hffff),.x_orows(16'hffff),
 .kv_ok(1'b1),.kv_write_drained(1'b1),.me_mem_ok(1'b0),.me_clk_en(ce),.c_fault(cf),
 .cmd(cmd),.ret(ret),.me_observe(obs),.me_image_ready(me_ready),.program_obs(program_obs));
 generate if(PSRAM!=0)begin:g_readback
  always @(negedge clk)if(program_obs[75])begin
   if(!program_obs[74])$fatal(1,"actual program write was not full64");
   if(program_obs[67])begin
    if(d.g_psram.g_m[1].u_pm.arr[program_obs[73:68]][64*program_obs[66:64]+:64]!==program_obs[63:0])$fatal(1,"receipt preceded actual SRAM1 write");
   end else if(d.g_psram.g_m[0].u_pm.arr[program_obs[73:68]][64*program_obs[66:64]+:64]!==program_obs[63:0])$fatal(1,"receipt preceded actual SRAM0 write");
   observed=observed+1;
  end
 end endgenerate
 generate if(DENSE_IMAGE!=0)begin:g_dense_control
  wire su_ready,su_fault,xready,mready,xfault;
  wire xc,xv,xs;wire[2:0]xi;wire[187:0]xd;wire[3:0]xn;wire[5:0]xstage;wire[31:0]xstop;
  ot_qwen_fixed_issue_pw #(.DENSE_IMAGE(1),.OWN(2))su_cfg(.clk(clk),.rst_n(rst_n),.pw_v(d.q_pw_v),.pw_addr(d.q_pw_addr),.pw_data(d.q_pw_data),.start(1'b0),.stage(6'd37),.candidate_v(1'b0),.candidate_pc(12'd0),.candidate_unit(2'd0),.available(1'b0),.end_ok(1'b0),.cp_available(1'b0),.image_ready(su_ready),.fault(su_fault));
  ot_qfd_xpf_dense_pw_loader xl(.clk(clk),.rst_n(rst_n),.stage_active(1'b0),.pw_v(d.q_pw_v),.pw_addr(d.q_pw_addr),.pw_data(d.q_pw_data),.cfg_clear(xc),.cfg_v(xv),.cfg_seal(xs),.cfg_index(xi),.cfg_data(xd),.cfg_count(xn),.stage(xstage),.stop_cycle(xstop),.image_ready(xready),.fault(xfault));
  ot_qfd_xpf_static_schedule #(.N(4),.ARM_TRANSPORT_EDGES(13))xm(.clk(clk),.rst_n(rst_n),.cfg_clear(xc),.cfg_v(xv),.cfg_seal(xs),.cfg_index(xi[1:0]),.cfg_data(xd),.cfg_count(xn[2:0]),.start(1'b0),.stop(1'b0),.stage(xstage),.me_issue(1'b0),.me_pc(12'd0),.su_issue(1'b0),.su_pc(12'd0),.cp_issue(1'b0),.cp_pc(12'd0),.image_ready(mready),.fault());
  always @(negedge clk)if(start&&(!me_ready||!su_ready||!xready||!mready||su_fault||xfault))$fatal(1,"dense footer did not seal all actual control stores");
 end endgenerate
 task tick;begin @(posedge clk);#0.1;end endtask
 task pw(input[9:0]a,input[63:0]v);begin @(negedge clk);pv=1;pa=a;pd=v;sent=sent+1;tick();@(negedge clk);pv=0;end endtask
 initial begin
 if(!$value$plusargs("PROGRAM=%s",path))$fatal(1,"actual sourceprogramrequired");$readmemh(path,rom);
 repeat(5)tick();rst_n=1;repeat(5)tick();
 if(DENSE_IMAGE)begin
 if(!$value$plusargs("IMAGE=%s",image_path))$fatal(1,"actual denseimage required");$readmemh(image_path,image);
 for(j=0;j<1024;j=j+1)pw(j,image[j]);
 end else begin
 for(j=0;j<8;j=j+1)for(k=0;k<16;k=k+1)pw(j*16+k,rom[j][64*k+:64]);
 pw(1016,{32'h43414c31,32'd600});
 pw(976,{17'd0,1'b0,2'd1,12'd3,32'd40});
 pw(977,{17'd0,1'b0,2'd3,12'd4,32'd60});
 pw(978,{17'd0,1'b0,2'd1,12'd4,32'd180});
 pw(979,{17'd0,1'b0,2'd3,12'd5,32'd200});
 pw(980,{17'd0,1'b0,2'd1,12'd5,32'd320});
 pw(981,{17'd0,1'b0,2'd3,12'd6,32'd340});
 pw(982,{17'd0,1'b0,2'd1,12'd6,32'd460});
 pw(983,{17'd0,1'b1,2'd0,12'd7,32'd600});
 pw(1019,{8'd0,COPY});pw(1020,{8'd0,COPY});pw(1021,{8'd0,COPY});
 pw(1017,{32'h43414c53,4'd0,10'd8,6'd37,6'd1,6'd8});
 end
 repeat(5)tick();@(negedge clk);start=1;tick();@(negedge clk);start=0;
 for(c=0;c<615;c=c+1)begin
 before_me=d.fixed_issue;before_cp=d.cp_v;before_pc=d.q_prog_base+d.candidate_pc;
 tick();
 if(ctx)ctx_seen=ctx_seen+1;
 if(c>5)begin
   if(nt!==(MUT_CONTEXT?18'd999:18'd1)||np!==18'd7)$fatal(1,"accepted context changed with future raw start pins");
 end
 if(cmd[0]!==before_me||cp[0]!==before_cp)$fatal(1,"actual head GO/CP boundary changed fixed timeline");
 if(before_me||before_cp)begin
   if(!obs[15]||obs[11:0]!==before_pc||obs[13:12]!=(before_cp?3:1))$fatal(1,"actual registered producer identity drift");
 end
 if(cmd[0])begin
   if(cmd[54:37]!=8||cmd[254:251]!=9||cmd[175:152]!=8192)$fatal(1,"actual head descriptor corrupted");
   me_seen=me_seen+1;
 end
 if(cp[0])begin if(cp!==COPY)$fatal(1,"actual CP56 payload corrupted");cp_seen=cp_seen+1;end
 @(negedge clk);if(c>4)begin token=999;pos=555;end
 if(ACTIVE_WRITE&&c==100)begin pv=1;pa=0;pd=rom[0][63:0];end else pv=0;
 end
 if((PSRAM!=0&&observed!=sent)||cf!==((CP_BUSY||ACTIVE_WRITE)?1'b1:1'b0)||me_seen!=4||cp_seen!=3||ctx_seen!=1||ce!==1'b1)$fatal(1,"head face composition fault");
 $display("PASS real head PW/IS/decoder/GO+CP56 stations, registered unit/PC, accepted context despite raw pin changes");$finish;
 end
endmodule
