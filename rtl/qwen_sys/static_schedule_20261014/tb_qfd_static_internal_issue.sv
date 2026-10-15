`timescale 1ns/1ps
// Mechanism composition: real source decoder, actual rank7 head program,
// real PW FF calendar, INTERNAL issue/fin and numeric argmax fold. Engine
// responses below are explicit endpoint stimuli, not a native end-to-end claim.
module tb_qfd_static_internal_issue;
 parameter MUT_NUMERIC=0, ROW_HIGH=0, MUT_DROP_ROW_HIGH=0, AVAIL_FALSE=0;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,start=0,pv=0;reg[9:0]pa=0;reg[63:0]pd=0;
 wire re;wire[11:0]ra;reg[1023:0]rq=0,rom[0:7];
 wire cv,av,eo,iv,ev,cf,done,go,ce;wire[11:0]cp,ip;wire[1:0]cu,iu;
 wire[17:0]fidx;wire[31:0]fval;
 reg[17:0]amidx=0;reg[31:0]amval=0;reg amany=0;
 integer c,seen=0;reg[1023:0]w;reg[17:0]expected_idx;string path;
 always @(posedge clk)if(re)rq<=rom[ra[2:0]];
 ot_qwen_fixed_issue_pw #(.OWN(1))cal(.clk(clk),.rst_n(rst_n),.pw_v(pv),.pw_addr(pa),.pw_data(pd),
 .start(start),.stage(6'd37),.candidate_v(cv),.candidate_pc(cp),.candidate_unit(cu),
 .available(av),.end_ok(eo),.issue_v(iv),.end_v(ev),.issue_pc(ip),.issue_unit(iu),
 .active(),.done(),.cycle(),.fault(cf));
 ot_qwen_rom_core_ctrl_static #(.OWN(1),.G(3072),.DG(3072),.NW(18),.AW(24),.PAW(12),.PRL(1),
 .SU_VEC(1),.SW(64),.SMIN(7),.QWEN_FULLSHAPE(MUT_DROP_ROW_HIGH?0:1),.HID(4096),.HD(128),.HALF(64))core(
 .clk(clk),.rst_n(rst_n),.start(start),.token(18'd1),.pos(18'd0),
 .fixed_issue(iv),.fixed_end(ev),.fixed_unit(iu),.fixed_fault(cf),
 .candidate_v(cv),.candidate_pc(cp),.candidate_unit(cu),.candidate_available(av),.candidate_end_ok(eo),
 .prog_re(re),.prog_addr(ra),.prog_q(rq),.done(done),.next_token(fidx),.next_val(fval),
 .pi_me_ready(AVAIL_FALSE?1'b0:1'b1),.pi_me_idle(1'b1),.pi_me_am_idx(amidx),.pi_me_am_val(amval),.pi_me_am_any(amany),
 .pi_me_fault(1'b0),.pi_su_fault(1'b0),.pi_su_ready(1'b1),.pi_su_idle(1'b1),
 .x_oacc(24'd3),.x_oidle(1'b1),.x_oprog(16'hffff),.x_orows(16'hffff),.x_ofin(1'b1),
 .kv_write_drained(1'b1),.kv_ok(1'b1),.w_ok(1'b1),.emb_ok(1'b1),.me_mem_ok(1'b0),
 .po_me_go(go),.me_clk_en(ce));
 task tick;begin @(posedge clk);#0.1;end endtask
 task pw(input[9:0]a,input[63:0]d);begin @(negedge clk);pv=1;pa=a;pd=d;tick();@(negedge clk);pv=0;end endtask
 initial begin
 if(!$value$plusargs("PROGRAM=%s",path))$fatal(1,"actual program required");
 $readmemh(path,rom);
 // Explicit ISA boundary variant exercises the actual fullshape high row bit.
 if(ROW_HIGH)for(c=3;c<=6;c=c+1)rom[c][898]=1;
 w=rom[5];expected_idx={w[899:898],w[896:881]}+18'd9;
 repeat(3)tick();rst_n=1;
 pw(1016,{32'h43414c31,32'd120});
 pw(976,{17'd0,1'b0,2'd1,12'd3,32'd40});
 pw(977,{17'd0,1'b0,2'd1,12'd4,32'd60});
 pw(978,{17'd0,1'b0,2'd1,12'd5,32'd80});
 pw(979,{17'd0,1'b0,2'd1,12'd6,32'd100});
 pw(980,{17'd0,1'b1,2'd0,12'd7,32'd120});
 pw(1017,{32'h43414c53,4'd0,10'd8,6'd37,6'd1,6'd5});
 repeat(3)tick();@(negedge clk);start=1;tick();@(negedge clk);start=0;
 for(c=0;c<125;c=c+1)begin
   if(iv)begin
     if(!go||!cv||cp!=ip||cu!=iu)$fatal(1,"fixed pulse missed INTERNAL issue");
     seen=seen+1;
   end
   tick();
   if(seen==1)begin amany=1;amidx=3;amval=32'hc0400000;end
   if(seen==2)begin amidx=7;amval=32'hbf800000;end
   if(seen==3)begin amidx=9;amval=32'h40000000;end
   if(seen==4)begin amidx=11;amval=32'h3f800000;end
   @(negedge clk);
 end
 if(cf!== (AVAIL_FALSE!=0)||seen!=4||!done||!ce)$fatal(1,"fixed internal source composition fault");
 if(fidx!==expected_idx+(MUT_NUMERIC?1:0)||fval!==32'h40000000)$fatal(1,"real signed argmax/full18bit row fold mismatch got%0d expected%0d",fidx,expected_idx);
 $display("PASS actual rank7 head decoder, PW47 fixed INTERNAL issue/fin, clock independent of memok0, signed argmax row18=%0d",fidx);$finish;
 end
endmodule
