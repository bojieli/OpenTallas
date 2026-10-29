`timescale 1ns/1ps
// TOK-HBM-7 2026-10-29: ot_hnx_idxq_qctl ROW_CLEAR_DELAY lockstep on the actual compiled IDX frame (vm_rt 173, vm_period 1,
// tools/hbm_next/idx_row_pitch_price.py). a = D0 (clear at launch), b = D (delayed clear). Every output equal except
// row_start, where b(t) == a(t-D). Drain: each row r>=1 clear must land after row r-1's last head emit and before row r's
// first block can reach the query core (first query slot + VM_RT). +DMUT compares against D-1 (must fail).
module tb_idxq_row_clear;
parameter integer D=171, PITCH=328, NROWS=6, LEN=1568, VM_RT=173;
reg clk=0;always begin #0.416 clk=1;#0.417 clk=0;end
reg rst_n=0,pw=0,start=0;reg[7:0]pa=0;reg[255:0]pd=0;
reg[31:0]prog[0:2047];
reg compare=0;integer t=0,checks=0;
wire a_ws,a_qs,a_qe,a_ks,a_kv,a_pv,a_fs,a_rs,a_f;wire[6:0]a_qi;wire[4:0]a_qh,a_kr;wire[7:0]a_ki,a_pi;wire[11:0]a_nq;
wire b_ws,b_qs,b_qe,b_ks,b_kv,b_pv,b_fs,b_rs,b_f;wire[6:0]b_qi;wire[4:0]b_qh,b_kr;wire[7:0]b_ki,b_pi;wire[11:0]b_nq;
ot_hnx_idxq_qctl #(.DELIVERED_RESET(1),.ROW_CLEAR_DELAY(0)) a(.clk_program(clk),.clk_program_mem(clk),.rst_n(rst_n),.slot(1'b0),.program_we(pw),.program_addr(pa),.program_data(pd),.start(start),.length(12'(LEN)),.n_rows(5'(NROWS)),.row_pitch(12'(PITCH)),.nkeys(14'd4096),.vf(1'b0),.qf(1'b0),.scf(1'b0),.kbf(1'b0),.weight_slot(a_ws),.query_slot(a_qs),.query_index(a_qi),.query_emit(a_qe),.query_emit_head(a_qh),.key_slot(a_ks),.key_v(a_kv),.key_index(a_ki),.key_row(a_kr),.pre_v(a_pv),.pre_index(a_pi),.nq(a_nq),.frame_start(a_fs),.row_start(a_rs),.fault(a_f));
ot_hnx_idxq_qctl #(.DELIVERED_RESET(1),.ROW_CLEAR_DELAY(D)) b(.clk_program(clk),.clk_program_mem(clk),.rst_n(rst_n),.slot(1'b0),.program_we(pw),.program_addr(pa),.program_data(pd),.start(start),.length(12'(LEN)),.n_rows(5'(NROWS)),.row_pitch(12'(PITCH)),.nkeys(14'd4096),.vf(1'b0),.qf(1'b0),.scf(1'b0),.kbf(1'b0),.weight_slot(b_ws),.query_slot(b_qs),.query_index(b_qi),.query_emit(b_qe),.query_emit_head(b_qh),.key_slot(b_ks),.key_v(b_kv),.key_index(b_ki),.key_row(b_kr),.pre_v(b_pv),.pre_index(b_pi),.nq(b_nq),.frame_start(b_fs),.row_start(b_rs),.fault(b_f));
integer dd;initial dd=$test$plusargs("DMUT")?D-1:D;
reg[8191:0]ahist=0;               // a.row_start history, bit k = k edges ago
integer arow[0:31],brow[0:31],emit_e[0:255],qslot0[0:31];integer na=0,nb=0,ne=0,nq0=0,keys=0,emits=0;
always @(posedge clk)begin #0.001;if(compare)begin t++;checks++;
 if({a_ws,a_qs,a_qi,a_qe,a_qh,a_ks,a_kv,a_ki,a_kr,a_pv,a_pi,a_nq,a_fs}!=={b_ws,b_qs,b_qi,b_qe,b_qh,b_ks,b_kv,b_ki,b_kr,b_pv,b_pi,b_nq,b_fs})
  $fatal(1,"ROWCLEAR_FAIL nonclear output differs at edge %0d",t);
 ahist={ahist[8190:0],a_rs};
 if(b_rs!==ahist[dd])$fatal(1,"ROWCLEAR_FAIL row_start not a delayed by %0d at edge %0d (b %0d)",dd,t,b_rs);
 if(a_f||b_f)$fatal(1,"ROWCLEAR_FAIL fault a%0d b%0d edge %0d",a_f,b_f,t);
 if(a_rs)begin arow[na]=t;na++;end
 if(b_rs)begin brow[nb]=t;nb++;end
 if(a_qe)begin emit_e[ne]=t;ne++;end
 if(a_qs&&a_qi==0)begin qslot0[nq0]=t;nq0++;end
 keys+=a_kv;
end end
integer r,bad_a,last_emit;
initial begin
 $readmemh("prog.hex",prog);
 repeat(8)@(negedge clk);rst_n=1;repeat(40)@(negedge clk);
 for(integer row=0;row*8<LEN;row++)begin
  pa=8'(row);for(integer j=0;j<8;j++)pd[j*32+:32]=(row*8+j<LEN)?prog[row*8+j]:32'd0;
  pw=1;@(negedge clk);pw=0;repeat(2)@(negedge clk);
 end
 compare=1;start=1;@(negedge clk);start=0;repeat((NROWS-1)*PITCH+LEN+D+64)@(negedge clk);
 if(na!=NROWS||nb!=NROWS||ne!=32*NROWS||nq0!=NROWS||keys!=171*NROWS)$fatal(1,"ROWCLEAR_FAIL counts rows a%0d b%0d emits%0d qslot0 %0d keys%0d",na,nb,ne,nq0,keys);
 bad_a=0;
 for(r=1;r<NROWS;r++)begin
  last_emit=emit_e[r*32-1];
  if(arow[r]<=last_emit)bad_a++;
  if(brow[r]<=last_emit)$fatal(1,"ROWCLEAR_FAIL drain row%0d clear %0d <= prev last emit %0d",r,brow[r],last_emit);
  if(brow[r]>=qslot0[r]+VM_RT)$fatal(1,"ROWCLEAR_FAIL row%0d clear %0d after first block bound %0d",r,brow[r],qslot0[r]+VM_RT);
  $display("ROW %0d launch_clear %0d delayed_clear %0d prev_last_emit %0d first_qslot %0d",r,arow[r],brow[r],last_emit,qslot0[r]);
 end
 $display("ROWCLEAR_PASS D%0d pitch%0d rows%0d checks%0d emits%0d keys%0d clear_at_launch_drain_violations%0d",dd,PITCH,NROWS,checks,ne,keys,bad_a);
 $finish;
end
endmodule
