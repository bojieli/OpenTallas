`default_nettype none
// ---------------------------------------------------------------------------
// HBM-HARD-1-IDX 2026-11-07: n12 operand reader core, redesign of ot_hbm_idx_vm_query_static_core +
// ot_hbm_idx_vm_static (g_nrst) for the measured DEPTH class: all 655 TT fails of the vK form were one cone,
// res_v/result_tag -> decode -> 256-bit select fanout -> 8:1 AND-OR -> block_data/weights/head_weight.
// Same ports, same cycle at every output (PIN CYCLES 0). Two changes, nothing else:
//  (1) SELECT ONE CYCLE EARLY. The selects, enables, qid and weight flags are computed from the D inputs of the old
//      res_v/result_tag and registered, in per-32-bit replicas, beside the data they steer. res_v and result_tag are gone.
//  (2) COMPRESSED TAG DELAY LINE. A read tag is either 0, a weight tag (bit 15, s in bit 0) or a query tag
//      ({0,6'd0,s,query_index}). query_index is common to all banks of a cycle, so each stage holds 7 shared bits +
//      3 bits per bank instead of the 80 live bits of the old tags[]. The old check "tag query id != qid" compared
//      copies of the same query_index, so it could never fire; it has no compare left to do.
//  (3) OT_N12R_LEGAL only (form vM, plan-free, 80% fewer crossbar wires): a legal query has query_sector[1:0]==0 and a
//      legal weight read weight_sector[2:0]==0, else `bad` is set at the request. So part p comes only from bank p or
//      p+4, and weight w only from bank w. Other banks are not wired to the word; block_data/weights differ from the
//      old core only after fault=1. block_v, fault, vm_rq stay cycle exact in all cases.
// Reset-free select flops: due[] resets async, so the D of every select is 0 after one clock in reset (reset is held
// >=64 clk by the die boot), as for the other reset-free data flops here.
(* keep_hierarchy, keep *)
module ot_hbm_idx_n12r_rep #(parameter integer W = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk) q <= d;
endmodule

module ot_hbm_idx_vm_query_n12r_core #(parameter integer VM_RT_EXTRA=0)(
 input wire clk,rst_n,input wire[1:0]sid,
 input wire weight_slot,query_slot,input wire[6:0]query_index,
 input wire[15:0]weight_sector,query_sector,
 output wire[135:0]vm_rq,input wire[2055:0]vm_rr,
 output reg block_v,output reg[4:0]block_head,output reg[1:0]block_number,
 output reg[1023:0]block_data,output reg[15:0]head_weight,
 output wire fault
);
 localparam integer D=8+VM_RT_EXTRA;
 localparam integer REP=8; // select replicas per 256-bit word (32 bits each)
 wire[1:0]rst_r;
 ot_rst_relay #(.REGIONS(2),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rst_r));
 // ---- slot decode: last writer wins in the original loop order, query after weight
 reg[135:0]slots;
 reg[23:0]code_d; // per bank {q,s[1:0]}: q=1 query part s; q=0 s[1]=weight hit, s[0]=weight index
 reg[15:0]wsec[0:1];reg[15:0]qsec[0:3];
 always @*begin
  slots=0;code_d=0;
  for(integer s=0;s<2;s=s+1)wsec[s]=weight_sector+16'(s);
  for(integer s=0;s<4;s=s+1)qsec[s]=query_sector+16'(int'(query_index)*4+s);
  for(integer l=0;l<8;l=l+1)begin
   if(weight_slot)for(integer s=0;s<2;s=s+1)if(wsec[s][2:0]==3'(l))begin
    slots[l*17+:17]={1'b1,wsec[s]};code_d[l*3+:3]={1'b0,1'b1,1'(s)};
   end
   if(query_slot)for(integer s=0;s<4;s=s+1)if(qsec[s][2:0]==3'(l))begin
    slots[l*17+:17]={1'b1,qsec[s]};code_d[l*3+:3]={1'b1,2'(s)};
   end
  end
 end
 // ---- VM face
 reg[7:0]due[0:D-1];
 reg[23:0]code[0:D-1];
 reg[6:0]qi_dl[0:D-1];
 reg[7:0]rq_v;reg[127:0]rq_s;reg[2047:0]res_d;reg face_fault;
 wire[7:0]expected=due[D-1];
 for(genvar b=0;b<8;b=b+1)begin:g_pack
  assign vm_rq[17*b+:17]={rq_v[b],rq_s[16*b+:16]};
 end
 always @(posedge clk or negedge rst_r[1])begin
  if(!rst_r[1])begin
   rq_v<=0;face_fault<=0;
   for(integer d=0;d<D;d=d+1)due[d]<=0;
  end else begin
   for(integer d=1;d<D;d=d+1)due[d]<=due[d-1];
   for(integer b=0;b<8;b=b+1)begin
    due[0][b]<=slots[17*b+16];
    rq_v[b]<=slots[17*b+16];
    if(slots[17*b+16]&&(slots[17*b+:3]!=3'(b)||(!slots[17*b+15]&&slots[17*b+13+:2]!=sid)))begin
     face_fault<=1;rq_v[b]<=0;due[0][b]<=0;
    end
    if(vm_rr[257*b+256]!=expected[b])face_fault<=1;
   end
  end
 end
 always @(posedge clk)begin
  for(integer d=1;d<D;d=d+1)begin code[d]<=code[d-1];qi_dl[d]<=qi_dl[d-1];end
  code[0]<=code_d;qi_dl[0]<=query_index;
  for(integer b=0;b<8;b=b+1)begin
   rq_s[16*b+:16]<=slots[17*b+:16];
   res_d[256*b+:256]<=vm_rr[257*b+:256];
  end
 end
 // ---- early decode from the D side of the old res_v / result_tag; the highest bank wins as in the old loops
 reg[31:0]sel_d;reg[3:0]parts_d;
 reg[15:0]wsel_d;reg[1:0]wv_d;
 reg[6:0]qid_d;
 wire[23:0]code_e=code[D-1];
 wire[6:0]qi_e=qi_dl[D-1];
 always @*begin
  sel_d=0;wsel_d=0;parts_d=0;wv_d=0;qid_d=0;
  for(integer b=0;b<8;b=b+1)if(expected[b]&&vm_rr[257*b+256])begin
   if(code_e[b*3+2])begin
    parts_d[code_e[b*3+:2]]=1;
    sel_d[32'(code_e[b*3+:2])*8+:8]=8'd1<<b;
    qid_d=qi_e;
   end else if(code_e[b*3+1])begin
    wv_d[code_e[b*3]]=1;
    wsel_d[32'(code_e[b*3])*8+:8]=8'd1<<b;
   end
  end
 end
 wire en_d=|parts_d;
 // ---- registered selects, one replica per 32 data bits; each word is 8 x {enable, one-hot bank}
 wire[9*REP*4-1:0]selq;
 wire[9*REP*2-1:0]wselq;
 reg[511:0]weights;
 for(genvar g=0;g<REP;g=g+1)begin:g_rep
  for(genvar p=0;p<4;p=p+1)begin:g_p
   ot_hbm_idx_n12r_rep #(.W(9)) u_r(.clk(clk),.d({en_d,sel_d[p*8+:8]}),.q(selq[(p*REP+g)*9+:9]));
   wire[8:0]c=selq[(p*REP+g)*9+:9];
`ifdef OT_N12R_LEGAL
   wire[31:0]m0=({32{c[p]}}&res_d[p*256+g*32+:32])|({32{c[p+4]}}&res_d[(p+4)*256+g*32+:32]);
   wire[31:0]m1=32'd0;
`else
   wire[31:0]m0=({32{c[0]}}&res_d[0*256+g*32+:32])|({32{c[1]}}&res_d[1*256+g*32+:32])|({32{c[2]}}&res_d[2*256+g*32+:32])|({32{c[3]}}&res_d[3*256+g*32+:32]);
   wire[31:0]m1=({32{c[4]}}&res_d[4*256+g*32+:32])|({32{c[5]}}&res_d[5*256+g*32+:32])|({32{c[6]}}&res_d[6*256+g*32+:32])|({32{c[7]}}&res_d[7*256+g*32+:32]);
`endif
   always @(posedge clk)if(c[8])block_data[p*256+g*32+:32]<=m0|m1;
  end
  for(genvar w=0;w<2;w=w+1)begin:g_w
   ot_hbm_idx_n12r_rep #(.W(9)) u_r(.clk(clk),.d({wv_d[w],wsel_d[w*8+:8]}),.q(wselq[(w*REP+g)*9+:9]));
   wire[8:0]c=wselq[(w*REP+g)*9+:9];
`ifdef OT_N12R_LEGAL
   wire[31:0]m0={32{c[w]}}&res_d[w*256+g*32+:32];
   wire[31:0]m1=32'd0;
`else
   wire[31:0]m0=({32{c[0]}}&res_d[0*256+g*32+:32])|({32{c[1]}}&res_d[1*256+g*32+:32])|({32{c[2]}}&res_d[2*256+g*32+:32])|({32{c[3]}}&res_d[3*256+g*32+:32]);
   wire[31:0]m1=({32{c[4]}}&res_d[4*256+g*32+:32])|({32{c[5]}}&res_d[5*256+g*32+:32])|({32{c[6]}}&res_d[6*256+g*32+:32])|({32{c[7]}}&res_d[7*256+g*32+:32]);
`endif
   always @(posedge clk)if(c[8])weights[w*256+g*32+:32]<=m0|m1;
  end
 end
 reg[3:0]parts;reg[1:0]wv;reg[6:0]qid;reg en;
 always @(posedge clk)begin parts<=parts_d;wv<=wv_d;qid<=qid_d;en<=en_d;end
 reg[15:0]hw_sel;
 always @*begin
  hw_sel=0;
  for(integer h=0;h<32;h=h+1)if(qid[6:2]==5'(h))hw_sel=weights[h*16+:16];
 end
 // ---- control, reset as before
 reg[1:0]weight_seen;reg bad;
 assign fault=bad||face_fault;
 always @(posedge clk or negedge rst_r[0])begin
  if(!rst_r[0])begin weight_seen<=0;bad<=0;block_v<=0;end
  else begin
   block_v<=en;
   if(weight_slot&&query_slot)bad<=1;
   if(weight_slot&&weight_sector[2:0]!=0)bad<=1;
   if(query_slot&&query_sector[1:0]!=0)bad<=1;
   if(wv[0])weight_seen[0]<=1;
   if(wv[1])weight_seen[1]<=1;
   if(en)begin
    if(parts!=4'hf||weight_seen!=2'b11)bad<=1;
   end
  end
 end
 always @(posedge clk)if(en)begin
  block_head<=qid[6:2];block_number<=qid[1:0];head_weight<=hw_sel;
 end
endmodule
`default_nettype wire
