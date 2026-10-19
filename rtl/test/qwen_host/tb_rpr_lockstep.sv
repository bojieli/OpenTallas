`timescale 1ns/1ps
// KVJ-A9 lock-step: qkd_host_qm_ingress16_service_debt RP_REPL=1 (9 replicated
// read-pointer select copies) vs RP_REPL=0, same stimulus, every output
// compared every cycle (4-state !==). Epochs between random async resets
// alternate legal credited traffic (source honours the 16 storage credits from
// in_crn, sink honours the 4 downstream credits; queue fills to 16 and drains
// under random allow) and fully random (illegal) inputs. Build with
// -DQKD_RPR_MUTANT for the mutant (one replica advances by 2): it must FAIL.
module tb_rpr_lockstep;
 parameter integer NCYC=50000, SEED=1, ES=1;
 reg ck=0,rst_n=0,in_v=0,allow=0,out_cr=0;reg[1:0]in_cls=0;reg[511:0]in_d=0;
 wire[4:0]a_crn,b_crn;wire a_ov,b_ov,a_f,b_f,a_qq,b_qq;wire[545:0]a_od,b_od;
 qkd_host_qm_ingress16_service_debt #(.MUT(0),.ENABLE_SERVICE(ES),.RP_REPL(0))ua(.ck(ck),.rst_n(rst_n),
  .in_v(in_v),.allow(allow),.in_cls(in_cls),.in_d(in_d),.in_crn(a_crn),.out_v(a_ov),.out_d(a_od),
  .out_cr(out_cr),.fault(a_f),.queue_quiet(a_qq));
 qkd_host_qm_ingress16_service_debt #(.MUT(0),.ENABLE_SERVICE(ES),.RP_REPL(1))ub(.ck(ck),.rst_n(rst_n),
  .in_v(in_v),.allow(allow),.in_cls(in_cls),.in_d(in_d),.in_crn(b_crn),.out_v(b_ov),.out_d(b_od),
  .out_cr(out_cr),.fault(b_f),.queue_quiet(b_qq));
 wire[553:0]va={a_crn,a_ov,a_od,a_f,a_qq},vb={b_crn,b_ov,b_od,b_f,b_qq};
 integer seed,cyc,mism=0,first_mism=-1,resets=0,pops=0,full=0,faults=0,legal=1,epoch_len=0,k;
 integer s_cr,o_out; // source storage credits / sink outstanding outputs
 task new_epoch;begin legal=($random(seed)&3)!=0;epoch_len=300+($random(seed)&16'h3ff);
  s_cr=16;o_out=0;end endtask
 always #0.5 ck=~ck;
 initial begin
  seed=SEED;new_epoch;
  repeat(3)@(negedge ck);rst_n=1;
  for(cyc=0;cyc<NCYC;cyc=cyc+1)begin
   @(negedge ck);
   if(va!==vb)begin mism=mism+1;if(first_mism<0)first_mism=cyc;end
   if(a_ov)pops=pops+1;if(ua.count==16)full=full+1;if(a_f)faults=faults+1;
   epoch_len=epoch_len-1;
   if(epoch_len<=0)begin rst_n=0;resets=resets+1;#0.2;rst_n=1;new_epoch;end
   for(k=0;k<16;k=k+1)in_d[k*32+:32]=$random(seed);
   in_cls=$random(seed);
   if(legal)begin
    s_cr=s_cr+a_crn;if(a_ov)o_out=o_out+1;
    // long allow-off phases fill the queue to 16, allow-on phases drain it
    allow=(($random(seed)&15)==0)?~allow:allow;
    in_v=(s_cr>0)&&(($random(seed)&3)!=0);if(in_v)s_cr=s_cr-1;
    out_cr=(o_out>0)&&($random(seed)&1);if(out_cr)o_out=o_out-1;
   end else begin
    in_v=$random(seed);allow=$random(seed);out_cr=$random(seed);
   end
  end
  $display("A9_LOCKSTEP seed=%0d es=%0d cycles=%0d resets=%0d pops=%0d full_cycles=%0d fault_cycles=%0d mismatches=%0d first_mismatch=%0d %s",
   SEED,ES,NCYC,resets,pops,full,faults,mism,first_mism,(mism==0)?"PASS":"FAIL");
  $finish;
 end
endmodule
