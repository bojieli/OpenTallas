`timescale 1ns/1ps
// ELEM-GAPS/HBMB 10-18: die-master bench of ot_hbm_idx_qctl_static (d4g idx_qctl_<Q>, port-identical, no parameters).
// Lockstep against the benched reference calendar ot_hbm_idx_calendar_static fed by the UNREGISTERED pins: every qctl
// output must equal the reference field 2 edges later (pin flop + output flop), on every edge of the frame:
// weight/query/emit/key slots, query_index/query_emit_head/key_index (on issue edges), nq(slot) for both straps and
// several nkeys values, frame_start = start + 2, and the sticky fault (vf / qf / scf pulses and a calendar programme-
// while-active fault) at +2 edges. Three programmes, slot 0 and 1, real mapped SRAM behavioural model.
// Mutants (MUT, stimulus side; each must FAIL): 1 one programme bit differs at the DUT only (field path);
// 2 the DUT gets the other slot strap than the model (nq path); 3 the model expects latency 1 (timing).
module tb_idx_qctl_static;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,pwe=0,start=0,slot=0,vf=0,qf=0,scf=0;reg[7:0]pa=0;reg[255:0]pd=0,pd_dut;reg[11:0]len=0;reg[13:0]nk=0;
 wire ws,qs,qe,ks,fs,flt;wire[6:0]qi;wire[4:0]qh;wire[7:0]ki;wire[11:0]nq;
 ot_hbm_idx_qctl_static dut(.clk_program(clk),.clk_program_mem(clk),.rst_n(rst_n),.slot(MUT==2?~slot:slot),
  .program_we(pwe),.program_addr(pa),.program_data(pd_dut),.start(start),.length(len),.nkeys(nk),
  .weight_slot(ws),.query_slot(qs),.query_index(qi),.query_emit(qe),.query_emit_head(qh),.key_slot(ks),.key_index(ki),
  .nq(nq),.frame_start(fs),.vf(vf),.qf(qf),.scf(scf),.fault(flt));
 // reference: the calendar on the raw pins (its own bench: run_calendar.sh)
 wire riv,rdone,rfault;wire[31:0]rins;
 reg rrst=0;
 ot_hbm_idx_calendar_static ref_cal(.clk(clk),.clk_mem(clk),.rst_n(rrst),.program_we(pwe),.program_addr(pa),
  .program_data(pd),.start(start),.length(len),.issue_v(riv),.instruction(rins),.done(rdone),.fault(rfault));
 localparam integer LAT=(MUT==3)?1:2;
 localparam integer H=8;
 reg[31:0]h_ins[0:H-1];reg h_iv[0:H-1];reg h_st[0:H-1];reg[13:0]h_nk[0:H-1];reg h_sl[0:H-1];reg h_ef[0:H-1];
 reg sticky=0;integer cyc=0,checked=0,issues=0,errors=0,nqchk=0,fchk=0;
 function automatic [11:0] nq_of(input [13:0]k,input s);
  reg[13:0]b;begin b=s?14'd2736:14'd0;nq_of=(k<=b)?12'd0:((k-b>=14'd2736)?12'd2736:12'(k-b));end
 endfunction
 // history shift on every posedge (values present before the edge)
 always @(posedge clk)begin
  for(integer i=H-1;i>0;i=i-1)begin h_ins[i]<=h_ins[i-1];h_iv[i]<=h_iv[i-1];h_st[i]<=h_st[i-1];h_nk[i]<=h_nk[i-1];h_sl[i]<=h_sl[i-1];h_ef[i]<=h_ef[i-1];end
  h_ins[0]<=rins;h_iv[0]<=riv;h_st[0]<=start;h_nk[0]<=nk;h_sl[0]<=slot;h_ef[0]<=vf|qf|scf;
  cyc<=cyc+1;
 end
 // the fault model: sticky after (event at the pins LAT edges ago) or the reference calendar fault (1 edge earlier
 // edge at the reference = 2 edges at the DUT: its calendar sees the pins 1 edge later, the fault flop 1 more)
 reg chk_on=0;reg rf_d=0,rf_d2=0;
 always @(posedge clk)begin rf_d<=rfault;rf_d2<=rf_d;end
 always @(negedge clk)if(chk_on)begin
  // fields: ins/iv sampled at the reference output after edge t, DUT output after edge t+LAT -> history index LAT-1
  reg[31:0]ei;reg ev;ei=h_ins[LAT-1];ev=h_iv[LAT-1];
  checked++;
  if(ws!==(ev&&ei[31])||qs!==(ev&&ei[30])||qe!==(ev&&ei[29])||ks!==(ev&&ei[28]))begin errors++;if(errors<6)$display("slot mismatch cyc%0d",cyc);end
  if(ev)begin issues++;if(qi!==ei[26:20]||qh!==ei[24:20]||ki!==ei[27:20])begin errors++;if(errors<6)$display("field mismatch cyc%0d",cyc);end end
  if(fs!==h_st[LAT-1])begin errors++;if(errors<6)$display("frame_start mismatch cyc%0d",cyc);end
  if(nq!==nq_of(h_nk[LAT-1],h_sl[LAT-1]))begin errors++;if(errors<6)$display("nq mismatch cyc%0d got%0d",cyc,nq);end else nqchk++;
  if(h_ef[LAT-1]||rf_d2)sticky=1;
  if(flt!==sticky)begin errors++;if(errors<6)$display("fault mismatch cyc%0d got%0d exp%0d",cyc,flt,sticky);end else fchk++;
 end
 reg[255:0]prog[0:255];
 task automatic frame(input integer n,input integer seed);
  integer rows;integer s;begin
  s=seed;rows=(n+7)/8;
  for(integer r=0;r<rows;r=r+1)for(integer w=0;w<8;w=w+1)prog[r][w*32+:32]=$random(s);
  for(integer r=0;r<rows;r=r+1)begin
   pwe=1;pa=8'(r);pd=prog[r];pd_dut=prog[r];
   if(MUT==1&&r==rows/2)pd_dut[20+32*3]=~pd_dut[20+32*3];
   @(negedge clk);
  end
  pwe=0;pd=0;pd_dut=0;repeat(4)@(negedge clk);
  len=12'(n);start=1;@(negedge clk);start=0;
  for(integer c=0;c<n+10;c=c+1)begin
   if(c%37==5)nk=14'($random(s)%6000);
   @(negedge clk);
  end
 end endtask
 initial begin
  pd_dut=0;
  repeat(3)@(negedge clk);rst_n=1;rrst=1;
  repeat(6)@(negedge clk);chk_on=1;    // DUT reset release +3 (ot_rst_relay): reference released at the same pin edge
  slot=0;nk=14'd1000;frame(300,11);
  slot=1;nk=14'd3000;frame(77,22);
  nk=14'd5600;frame(2048,33);
  slot=0;nk=14'd2736;frame(8,44);
  // sticky fault: a vf pulse, then the model and the DUT must both hold fault
  vf=1;@(negedge clk);vf=0;repeat(5)@(negedge clk);
  $display("IDX_QCTL_STATIC MUT%0d checked%0d issues%0d nq%0d faultchk%0d errors%0d fault%0d",MUT,checked,issues,nqchk,fchk,errors,flt);
  if(errors||issues!=300+77+2048+8||!flt)$fatal(1,"idx qctl static lockstep mismatch");
  $display("IDX_QCTL_STATIC_PASS");$finish;
 end
endmodule
