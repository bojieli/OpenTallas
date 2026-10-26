`timescale 1ns/1ps
module tb_eq;
 parameter integer MUT=0, RELAY=0;
 reg ck=0,rst_n=0; always #1 ck=~ck;
 reg v,slot; reg[10:0]tag; reg[511:0]data; reg[58:0]id,cid; reg[1:0]gen,cgen,ix;
 `define PORTS(p) .ck(ck),.rst_n(rst_n),.word_valid(v),.word_tag(tag),.word_data(data),.word_identity(id),.word_generation(gen),.compiled_word_slot(slot),.compiled_word_index(ix),.compiled_identity(cid),.compiled_generation(cgen),.es(p``es),.dest_pc(p``pc),.dest_stack(p``st),.identity(p``oi),.generation(p``og),.write_mask(p``m),.native_kv(p``nk),.expected_valid(p``ev),.expected_pc(p``epc),.expected_stack(p``est),.expected_identity(p``ei),.expected_generation(p``eg),.expected_address(p``ea),.es_context(p``cx),.es_expected_identity(p``ec),.fault(p``f),.fault_code(p``fc)
 wire[1151:0]aes,bes; wire[19:0]apc,bpc,aepc,bepc; wire[1:0]ast,bst,aog,bog,aest,best,aeg,beg; wire[58:0]aoi,boi,aei,bei;
 wire[1023:0]am,bm; wire[3:0]ank,bnk,aev,bev; wire[28:0]aea,bea; wire[317:0]acx,bcx; wire[60:0]aec,bec; wire af,bf; wire[7:0]afc,bfc;
 qkd_kv_static_writer_ref #(.MUT(MUT)) A(`PORTS(a));
 qkd_kv_static_writer #(.MUT(MUT),.RST_RELAY(RELAY)) B(`PORTS(b));
 wire [3000:0] va={aes,apc,aepc,ast,aog,aest,aeg,aoi,aei,am,ank,aev,aea,acx,aec,af,afc};
 wire [3000:0] vb={bes,bpc,bepc,bst,bog,best,beg,boi,bei,bm,bnk,bev,bea,bcx,bec,bf,bfc};
 integer n=0,cyc,k,seed=1,mode;
 always @(negedge ck) if(va!==vb) begin $display("MISMATCH t=%0t es %0d pc %0d m %0d f %0d %0d late %b",$time, aes!==bes, apc!==bpc, am!==bm, af, bf, A.late_live);for(k=0;k<1152;k=k+1) if(aes[k]!==bes[k]) $display("bit %0d a%b b%b",k,aes[k],bes[k]); $fatal(1,"FAIL"); end
 task rnd; begin
   // mostly well-formed 4-slot cohorts, sometimes random corruption
   mode=$urandom%8;
   for(k=0;k<4;k=k+1) begin
     @(posedge ck); #0.2;
     cid={16'($urandom),6'(1+$urandom%36),18'($urandom),13'($urandom),6'd0}; cgen=$urandom;
     if(k>0 && mode!=7) begin cid=B.ci; cgen=B.cg; end
     ix=k; slot=(mode==6)?$urandom:1; v=(mode==5)?$urandom:slot; id=cid^((mode==4)?59'($urandom%2):59'd0); gen=cgen;
     tag={3'b010,5'd0,1'(k/2),1'b0,1'(k%2)}; if(mode==3) tag=$urandom;
     data={16{$urandom}};
     if(mode==2) ix=$urandom;
   end
   @(posedge ck); #0.2; slot=0; v=0; data={16{$urandom}};
   repeat($urandom%3) @(posedge ck);
 end endtask
 initial begin
   v=0;slot=0;tag=0;data=0;id=0;cid=0;gen=0;cgen=0;ix=0;
   repeat(3)@(posedge ck); #0.2 rst_n=1; repeat(3)@(posedge ck);
   for(cyc=0;cyc<20000;cyc=cyc+1) begin
     rnd();
     if(cyc%5000==4999) begin #0.3 rst_n=0; repeat(2)@(posedge ck); #0.2 rst_n=1; repeat(3)@(posedge ck); end
   end
   $display("PASS eq MUT%0d RELAY%0d",MUT,RELAY); $finish;
 end
endmodule
