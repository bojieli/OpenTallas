`timescale 1ns/1ps
// Real head/IS/program write path/calendar/GO stations; explicit engine status
// stimuli. PSRAM0 exercises the source FF program-store profile; SRAM physical
// mode and actual endpoint/VM composition require separate admitted gates.
module tb_qfd_static_head_face;
 parameter MUT_CONTEXT=0,CP_BUSY=0,ACTIVE_WRITE=0;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,start=0,pv=0;reg[9:0]pa=0;reg[63:0]pd=0;
 reg[17:0]token=1,pos=7;
 reg[94:0]ret=95'd3;
 wire[379:0]cmd;wire[55:0]cp;wire[15:0]obs;wire ctx,ce,cf;
 wire[17:0]nt,np;reg[1023:0]rom[0:7];string path;
 integer j,k,c,me_seen=0,cp_seen=0,ctx_seen=0;
 reg before_me,before_cp;reg[11:0]before_pc;
 localparam[55:0]COPY={7'd64,24'd8192,24'd8192,1'b1};
 qfd_tt_ctlm_head_static #(.PSRAM(0))d(
 .clk(clk),.ck_sched(clk),.cp_active(CP_BUSY?1'b1:1'b0),.cp(cp),.layer_context_v(ctx),.native_tok(nt),.native_pos(np),
 .rst_n(rst_n),.h_start(start),.token(token),.pos(pos),.prog_base(12'd0),
 .pw_v(pv),.pw_addr(pa),.pw_data(pd),.x_oacc(24'd3),.x_oidle(1'b1),.x_oprog(16'hffff),.x_orows(16'hffff),
 .kv_ok(1'b1),.kv_write_drained(1'b1),.me_mem_ok(1'b0),.me_clk_en(ce),.c_fault(cf),
 .cmd(cmd),.ret(ret),.me_observe(obs));
 task tick;begin @(posedge clk);#0.1;end endtask
 task pw(input[9:0]a,input[63:0]v);begin @(negedge clk);pv=1;pa=a;pd=v;tick();@(negedge clk);pv=0;end endtask
 initial begin
 if(!$value$plusargs("PROGRAM=%s",path))$fatal(1,"actual sourceprogramrequired");$readmemh(path,rom);
 repeat(5)tick();rst_n=1;repeat(5)tick();
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
 if(cf!==((CP_BUSY||ACTIVE_WRITE)?1'b1:1'b0)||me_seen!=4||cp_seen!=3||ctx_seen!=1||ce!==1'b1)$fatal(1,"head face composition fault");
 $display("PASS real head PW/IS/decoder/GO+CP56 stations, registered unit/PC, accepted context despite raw pin changes");$finish;
 end
endmodule
