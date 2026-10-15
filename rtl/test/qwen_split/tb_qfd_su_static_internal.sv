`timescale 1ns/1ps
// Actual25word TP8 layer decoder plus real PW20x47 fixed consumer.
// Engine endpoint status is declared stimuli: mechanism proof, not native layer.
module tb_qfd_su_static_internal;
 parameter integer BAD_AVAILABLE=0,BAD_PC=0;
 reg clk=0;always #1 clk=~clk;reg rst_n=0,start=0,calstart=0,pv=0;
 reg[9:0]pa=0;reg[63:0]pd=0;reg[11:0]base=0;reg[23:0]otheracc=0;
 wire re,cv,av,eo,iv,ev,cf,go,ce,done,corefault;wire[11:0]ra,cp,ip;wire[1:0]cu,iu;
 wire[31:0]cycle;reg[1023:0]rom[0:24],rq=0;integer seen=0,ends=0,i,j;string path;
 always @(posedge clk)if(re)rq<=rom[base+ra];
 ot_qwen_fixed_issue_pw #(.OWN(2))cal(.clk(clk),.rst_n(rst_n),.pw_v(pv),.pw_addr(pa),.pw_data(pd),
 .start(calstart),.stage(6'd1),.candidate_v(cv),.candidate_pc(base+cp),.candidate_unit(cu),
 .available(av),.end_ok(eo),.issue_v(iv),.end_v(ev),.issue_pc(ip),.issue_unit(iu),.active(),.done(),.cycle(cycle),.fault(cf));
 ot_qwen_rom_core_ctrl_su_static #(.OWN(2),.G(3072),.NW(18),.AW(24),.PAW(12),.PRL(1),
 .SU_VEC(1),.SW(64),.SMIN(7),.QWEN_FULLSHAPE(1),.HID(4096),.HD(128),.HALF(64),.INT8_EMBED(1))core(
 .clk(clk),.rst_n(rst_n),.start(start),.token(18'd50994),.pos(18'd255),
 .fixed_issue(iv),.fixed_end(ev),.fixed_unit(iu),.fixed_fault(cf),
 .candidate_v(cv),.candidate_pc(cp),.candidate_unit(cu),.candidate_available(av),.candidate_end_ok(eo),
 .prog_re(re),.prog_addr(ra),.prog_q(rq),.done(done),.fault(corefault),
 .pi_me_ready(1'b1),.pi_me_idle(1'b1),.pi_me_am_idx(18'd0),.pi_me_am_val(32'd0),.pi_me_am_any(1'b0),
 .pi_me_fault(1'b0),.pi_su_fault(1'b0),.pi_su_ready(BAD_AVAILABLE?1'b0:1'b1),.pi_su_idle(1'b1),
 .x_oacc(otheracc),.x_oidle(1'b1),.x_oprog(16'hffff),.x_orows(16'hffff),.x_ofin(1'b1),
 .kv_write_drained(1'b1),.kv_ok(1'b1),.w_ok(1'b1),.emb_ok(1'b1),.me_mem_ok(1'b0),
 .po_su_go(go),.me_clk_en(ce),.embed_code_q(512'd0),.embed_scale_q(16'h3f80));
 task step;begin @(negedge clk);end endtask
 task pw(input[9:0]a,input[63:0]d);begin pa=a;pd=d;pv=1;step();pv=0;end endtask
 always @(posedge clk)if(rst_n)begin
  if(iv)begin
   if(!go||!cv||base+cp!=ip||cu!=iu)$fatal(1,"fixed slot missed actual SU internal issue go%0d cv%0d pc%0d+%0d ip%0d cu%0d iu%0d cyc%0d",go,cv,base,cp,ip,cu,iu,cycle);
   seen=seen+1;
  end
  if(ev)ends=ends+1;
 end
 initial begin
 if(!$value$plusargs("PROGRAM=%s",path))$fatal(1,"actual program required");$readmemh(path,rom);
 repeat(4)step();rst_n=1;step();
 pw(1018,{32'h43414c32,32'd610});
 pw(984,{17'd0,1'b0,2'd2,12'(BAD_PC),32'd40});
 pw(985,{17'd0,1'b0,2'd2,12'd2,32'd70});
 pw(986,{17'd0,1'b0,2'd2,12'd3,32'd100});
 pw(987,{17'd0,1'b0,2'd2,12'd4,32'd130});
 pw(988,{17'd0,1'b0,2'd2,12'd5,32'd160});
 pw(989,{17'd0,1'b0,2'd2,12'd6,32'd190});
 pw(990,{17'd0,1'b0,2'd2,12'd7,32'd220});
 pw(991,{17'd0,1'b0,2'd2,12'd8,32'd250});
 pw(992,{17'd0,1'b0,2'd2,12'd9,32'd280});
 pw(993,{17'd0,1'b0,2'd2,12'd10,32'd310});
 pw(994,{17'd0,1'b0,2'd0,12'd13,32'd340});
 pw(995,{17'd0,1'b0,2'd2,12'd14,32'd370});
 pw(996,{17'd0,1'b0,2'd2,12'd15,32'd400});
 pw(997,{17'd0,1'b0,2'd2,12'd17,32'd430});
 pw(998,{17'd0,1'b0,2'd2,12'd18,32'd460});
 pw(999,{17'd0,1'b0,2'd2,12'd19,32'd490});
 pw(1000,{17'd0,1'b0,2'd0,12'd21,32'd520});
 pw(1001,{17'd0,1'b0,2'd2,12'd22,32'd550});
 pw(1002,{17'd0,1'b0,2'd2,12'd23,32'd580});
 pw(1003,{17'd0,1'b1,2'd0,12'd24,32'd610});
 pw(1017,{32'h43414c53,4'd0,10'd25,6'd1,6'd20,6'd1});
 repeat(3)step();start=1;calstart=1;step();start=0;calstart=0;
 for(j=0;j<620;j=j+1)begin
  case(cycle)
   60:otheracc=1;
   315:otheracc=3;
   350:begin base=14;start=1;end
   351:start=0;
   410:otheracc=4;
   500:otheracc=5;
   530:begin base=22;start=1;end
   531:start=0;
  endcase
  step();
 end
 if(cf!==(BAD_AVAILABLE!=0||BAD_PC!=0)||seen!=17||ends!=3||!done||!ce)$fatal(1,"SU static25word decoder fault cf%0d seen%0d ends%0d done%0d",cf,seen,ends,done);
 $display("PASS actual25word SUdecoder17internalSU+3END fixedtimeline unavailable%0d badPC%0d",BAD_AVAILABLE,BAD_PC);$finish;
 end
endmodule
