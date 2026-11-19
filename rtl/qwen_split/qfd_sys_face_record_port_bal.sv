`timescale 1ns/1ps
// qfd_sys_face_record_port_bal (FABLE-FIX-S81-GLUE 2026-11-19): depth-balanced, register-identical rewrite of
// qfd_sys_face_record_port (and of its children qfd_program_auth_rx, qkd_program_commit, qkd_program_commit_join,
// qfd_host_native_context_rx, qfd_program_witness_tx).  Same ports, same registers (same hierarchical names, same
// reset values), same next-state function for EVERY state and input (0 added cycles, no reachability assumption):
// each next-state function of the originals' nested if / priority-mux form is written here as a flat sum of products
// over shared, explicitly named terms, so that the generic 2-input netlist (yosys synth -noabc) plus
// tools/qwen_split/record32/depth_opt.py is at most 13 gate levels per register, 11 or fewer on all but 12 registers (the originals: up to 25).
// Why: QC glue u_record (qfd_sys_face_record_port_n32, every gate a retained cell) failed TT setup at -130 ps on 648
// ends, all behind 20..25 retained levels (wide record zero checks and 64/80-bit digest compares in front of the
// fault / accept priority chains).
// What the logic is (unchanged):
//   u_auth      kind-13 BEGIN / AUTH record decode (opaque548: zero checks, expected 1024 PW + 8 DW, epoch, digest)
//   u_receipt*2 per-sink write ledger: digest <= rotl(digest,7) ^ data ^ {desc,addr} per observed full-word write, in
//               address order (1024 PW then 8 DW); at write 1032 the digest must equal the authorized digest
//   u_join      joins the two sink receipts against the authorized epoch/digest, raises commit / program_ready
//   u_context   kind-12 HOST context record decode against the installed image, head context check
//   u_witness   kind-14 witness record transmit
// Proof: tools/qwen_split/record32/prove_rewrite.py (one-edge transition + output SAT against the original source for
// arbitrary state and inputs) and tools/qwen_split/record32/run_bench.sh (cycle-exact lockstep, unchanged bench).
module qfd_program_auth_rx_bal(
 input wire ck,rst_n,receive_slot,rx_v,input wire[547:0]rx_record,
 output reg begin_v,output reg[15:0]begin_epoch,output reg[10:0]expected_pw,output reg[3:0]expected_dw,
 output reg auth_v,output reg[15:0]auth_epoch,output reg[63:0]auth_digest,output reg fault
);
 // rx_v is the raw link valid here (the original takes rx_v && receive_slot).
 wire nz_hi=|rx_record[511:66];
 wire nz_mid=|rx_record[65:17];
 // common_ok: [547:543]==0, [542:539]==13, [538:533]==63, [516:512]==0
 wire com=&{~rx_record[547:543],rx_record[542],rx_record[541],~rx_record[540],rx_record[539],rx_record[538:533],~rx_record[516:512]};
 // begin: [1:0]==1, [12:2]==1024, [16:13]==8 (and [511:17]==0)
 wire bsel=&{rx_record[0],~rx_record[1],rx_record[12],~rx_record[11:2],rx_record[16],~rx_record[15:13]};
 wire asel=rx_record[1]&~rx_record[0];
 wire okb=rx_v&com&bsel&~nz_mid;
 wire oka=rx_v&com&asel;
 wire bgo=receive_slot&okb&~nz_hi;
 wire ago=receive_slot&oka&~nz_hi;
 wire fault_n=fault|(receive_slot&~(okb|oka))|(receive_slot&nz_hi);
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin begin_v<=0;begin_epoch<=0;expected_pw<=0;expected_dw<=0;auth_v<=0;auth_epoch<=0;auth_digest<=0;fault<=0;end
  else begin
   begin_v<=bgo;auth_v<=ago;fault<=fault_n;
   if(bgo)begin begin_epoch<=rx_record[532:517];expected_pw<=rx_record[12:2];expected_dw<=rx_record[16:13];end
   if(ago)begin auth_epoch<=rx_record[532:517];auth_digest<=rx_record[65:2];end
  end
 end
endmodule

module qkd_program_commit_bal(
 input wire ck,rst_n,execution_active,control_stores_ready,
 input wire begin_v,input wire[15:0]begin_epoch,
 input wire[10:0]expected_pw,input wire[3:0]expected_dw,
 input wire auth_v,input wire[15:0]auth_epoch,input wire[63:0]auth_digest,
 input wire pw_v,input wire[9:0]pw_addr,input wire[63:0]pw_data,input wire pw_full_word,
 input wire dw_v,input wire[2:0]dw_addr,input wire[63:0]dw_data,input wire dw_full_word,
 output reg commit_v,ready,fault,installed_fusedcap,output reg[15:0]commit_epoch,
 output reg[63:0]commit_digest);
 reg[2:0]state;reg footer_cap;reg[10:0]count;reg[15:0]epoch;
 reg[63:0]digest,authorized_digest;
 // states: IDLE 0, WAIT_AUTH 1, WRITES 2, VERIFIED 3, READY 4
 wire nf=~fault;
 wire wr=pw_v|dw_v;
 wire eb=nf&begin_v;
 wire ea=nf&~begin_v&auth_v;
 wire ew=nf&~begin_v&~auth_v&wr;
 wire st1=~state[2]&~state[1]&state[0];
 wire st3=~state[2]&state[1]&state[0];
 wire busy=~state[2]&(state[1]|state[0]);
 wire exp_bad=|{~expected_pw[10],expected_pw[9:0],~expected_dw[3],expected_dw[2:0]};
 wire b_bad=|{execution_active,busy,auth_v,pw_v,dw_v,exp_bad};
 wire a_bad=|{execution_active,~st1,auth_epoch^epoch,pw_v,dw_v};
 // PW: {1'b0,pw_addr}!=count || count>=1024.  DW: count<1024 || count>=1032 || {8'd0,dw_addr}!=count-1024.
 wire pne=|{count[10],pw_addr^count[9:0]};
 wire dne=|{~count[10],count[9:3],dw_addr^count[2:0]};
 // w_ok = !(execution_active || state!=WRITES || bad_write), as a literal list that each user folds into its own
 // AND tree (a shared w_ok net would add its own level in front of every user)
`define QFD_RP_W_OK ~execution_active,~state[2],state[1],~state[0],~(pw_v&dw_v),~(pw_v&~pw_full_word),~(pw_v&pne),~(dw_v&~dw_full_word),~(dw_v&dne)
 wire nw=auth_v|~wr;                               // not a write edge (given no fault and no begin)
 wire[63:0]rot={digest[56:0],digest[63:57]};
 wire[63:0]evd=dw_v?dw_data:pw_data;
 wire[10:0]pad={dw_v,dw_v?{7'd0,dw_addr}:pw_addr};
 wire[63:0]ep=evd^{53'd0,pad};
 wire[63:0]nd=rot^ep;                       // next_digest
 wire[63:0]ra=rot^authorized_digest;
 // The final compare only matters on an accepted write at count==1031, and an accepted write there is a DW
 // (an accepted PW has count[10]==0): next_digest != authorized_digest is read on the DW operand alone.
 wire[63:0]dpx=dw_data^{53'd0,1'b1,7'd0,dw_addr};
 wire mm_d=|(ra^dpx);
 wire last=&{count[10],~count[9:3],count[2:0]};   // count==1031
 wire bok=eb&~b_bad;
 wire aok=ea&~a_bad;
 wire wok=&{ew,`QFD_RP_W_OK};
 wire xlm=&{ew,last,mm_d};
 wire lok=&{ew,`QFD_RP_W_OK,last,~mm_d};
 wire fin=&{nf,st3,~begin_v,~auth_v,~pw_v,~dw_v,control_stores_ready};
 wire fault_n=|{fault,eb&b_bad,ea&a_bad,ew&~(&{`QFD_RP_W_OK}),xlm};
 // fin implies every other factor below (no fault, no begin / auth / write this edge)
 wire ready_n=&{fin|ready,nf,~begin_v,~(auth_v&a_bad),nw|(&{`QFD_RP_W_OK}),nw|~last|~mm_d};
 wire ifc_n=&{fin?footer_cap:installed_fusedcap,nf,~begin_v,~(auth_v&a_bad),nw|(&{`QFD_RP_W_OK}),nw|~last|~mm_d};
 wire foot=&{pw_data[63:32]==32'h58504631,pw_data[1],~pw_data[0],~pw_data[31:13],pw_data[12],
             ~pw_data[5],pw_data[4]?~(pw_data[3]|pw_data[2]):(pw_data[3]|pw_data[2])};
 wire fs=&{ew,`QFD_RP_W_OK,pw_v,pw_addr};
 wire sth=&{~eb,~ea,~fin,~ew|~last,~ew|(&{`QFD_RP_W_OK})};      // state holds
 wire[2:0]state_n={fin|(state[2]&sth),aok|lok|(state[1]&sth),bok|lok|(state[0]&sth)};
 wire[10:0]inc={count[10]^(&count[9:0]),count[9]^(&count[8:0]),count[8]^(&count[7:0]),count[7]^(&count[6:0]),
                count[6]^(&count[5:0]),count[5]^(&count[4:0]),count[4]^(&count[3:0]),count[3]^(&count[2:0]),
                count[2]^(&count[1:0]),count[1]^count[0],~count[0]};
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin state<=0;count<=0;epoch<=0;digest<=0;authorized_digest<=0;
   commit_v<=0;ready<=0;fault<=0;installed_fusedcap<=0;footer_cap<=0;commit_epoch<=0;commit_digest<=0;end
  else begin
   commit_v<=fin;ready<=ready_n;fault<=fault_n;installed_fusedcap<=ifc_n;state<=state_n;
   footer_cap<=~eb&(fs?foot:footer_cap);
   if(bok)begin epoch<=begin_epoch;count<=0;digest<=64'h51484f5354505247;end
   if(wok)begin count<=inc;digest<=nd;end
   if(aok)authorized_digest<=auth_digest;
   if(lok)begin commit_epoch<=epoch;commit_digest<=nd;end
  end
 end
`undef QFD_RP_W_OK
endmodule

module qkd_program_commit_join_bal(
 input wire ck,rst_n,begin_v,auth_v,execution_active,control_stores_ready,
 input wire[15:0]auth_epoch,input wire[63:0]auth_digest,
 input wire[1:0]sink_ready,sink_fault,sink_fusedcap,
 input wire[31:0]sink_epoch,input wire[127:0]sink_digest,
 output reg commit_v,ready,fault,installed_fusedcap,
 output reg[15:0]commit_epoch,output reg[63:0]commit_digest);
 reg armed,complete,begin_pending;reg[15:0]epoch;reg[63:0]digest;
 reg[1:0]seen_empty;
 wire nf=~fault;
 wire n=nf&~begin_v;
 wire ac=armed|complete;
 wire ne0=|{sink_epoch[15:0]^epoch,sink_digest[63:0]^digest};
 wire ne1=|{sink_epoch[31:16]^epoch,sink_digest[127:64]^digest};
 // u<i> = no fault and sink i mismatches while armed / complete
 wire u0=&{nf,sink_ready[0],seen_empty[0],ac,ne0};
 wire u1=&{nf,sink_ready[1],seen_empty[1],ac,ne1};
 wire abad_c=|{execution_active,armed,complete,~begin_pending};
 wire abad=auth_v&abad_c;
 wire aok=auth_v&~abad_c;
 wire asr=&sink_ready;
 wire asc=&sink_fusedcap;
 wire rev=complete&(~asr|~control_stores_ready|(installed_fusedcap^asc));
 wire cm0=&{armed,seen_empty,asr,control_stores_ready,~auth_v};
 wire cm=&{n,cm0,~sink_fault,~u0,~u1};
 wire fault_n=|{fault,nf&begin_v&(execution_active|auth_v|armed|begin_pending),n&abad,n&rev&execution_active,
                n&sink_fault[0],n&sink_fault[1],~begin_v&u0,~begin_v&u1};
 wire ready_n=&{(fault&ready)|(&{n,~sink_fault,cm0|(ready&~abad&~rev)}),~u0,~u1};
 wire ifc_n=&{(fault&installed_fusedcap)|(&{n,~sink_fault,cm0?asc:(installed_fusedcap&~abad&~rev)}),~u0,~u1};
 wire armed_n=&{(fault&armed)|(&{n,~sink_fault,~cm0,aok|armed}),~u0,~u1};
 wire complete_n=(complete&(fault|~begin_v))|cm;
 wire bp_n=(fault&begin_pending)|(nf&begin_v)|(n&begin_pending&~aok);
 wire[1:0]se_n=({2{fault}}&seen_empty)|({2{n}}&(seen_empty|~sink_ready));
 wire ld=n&aok;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin commit_v<=0;ready<=0;fault<=0;installed_fusedcap<=0;
   commit_epoch<=0;commit_digest<=0;armed<=0;complete<=0;begin_pending<=0;seen_empty<=0;epoch<=0;digest<=0;end
  else begin
   commit_v<=cm;ready<=ready_n;fault<=fault_n;installed_fusedcap<=ifc_n;
   armed<=armed_n;complete<=complete_n;begin_pending<=bp_n;seen_empty<=se_n;
   if(ld)begin epoch<=auth_epoch;digest<=auth_digest;end
   if(cm)begin commit_epoch<=epoch;commit_digest<=digest;end
  end
 end
endmodule

module qfd_host_native_context_rx_bal #(parameter integer MU_HEAD = 0)(
 input wire ck,rst_n,receive_slot,rx_v,input wire[547:0]rx_record,
 input wire program_begin_v,program_ready,installed_fusedcap,
 input wire[15:0]program_epoch,input wire[63:0]program_digest,
 input wire head_context_v,input wire[5:0]head_stage,
 input wire[17:0]head_token,head_position,input wire native_active,
 output reg host_epoch_valid,output wire[15:0]host_epoch,
 output reg[58:0]host_tag,output reg[1:0]host_gen,
 output reg host_fusedcap,output reg[15:0]host_image_epoch,output reg[63:0]host_image_digest,
 output reg fault
);
 // rx_v is the raw link valid here (the original takes rx_v && receive_slot).
 wire[58:0]tag=rx_record[58:0];
 wire nz_hi=|rx_record[511:142];
 // tag[36:19] < 151936 (18'b100101000110000000)
 wire[17:0]t=tag[36:19];
 wire tok_lt=|{~t[17],&{~t[16:14]},&{~t[16:15],~t[13:12]},&{~t[16:15],t[14],~t[13],~t[11:8]},&{~t[16:15],t[14],~t[13],t[12],~t[11:9],~t[7]}};
 // [547:543]==0, [542:539]==12, [538:533]==63, [516:512]==0, tag[42:37]==0, tag[5:0]==0, [532:517]==tag[58:43]
 wire acc=&{receive_slot,~nz_hi,~fault,
            rx_v,~rx_record[547:543],rx_record[542],rx_record[541],~rx_record[540],~rx_record[539],rx_record[538:533],
            ~rx_record[516:512],~tag[42:37],~tag[5:0],tok_lt,~(rx_record[532:517]^tag[58:43]),
            program_ready,~(rx_record[77:62]^program_epoch),~(rx_record[141:78]^program_digest),~(rx_record[61]^installed_fusedcap),
            ~native_active,~program_begin_v};
 // cbad = the complement of the accept condition without the slot and the fault bit, as its own OR tree
 wire cbad=|{nz_hi,~rx_v,rx_record[547:543],~rx_record[542],~rx_record[541],rx_record[540],rx_record[539],~rx_record[538:533],
             rx_record[516:512],tag[42:37],tag[5:0],~tok_lt,rx_record[532:517]^tag[58:43],
             ~program_ready,rx_record[77:62]^program_epoch,rx_record[141:78]^program_digest,rx_record[61]^installed_fusedcap,
             native_active,program_begin_v};
 wire stale=host_epoch_valid&(|{~program_ready,program_epoch^host_image_epoch,program_digest^host_image_digest,installed_fusedcap^host_fusedcap});
 wire stage_ok=(|head_stage)&(|{~head_stage[5],&{~head_stage[4:2]},&{~head_stage[4:3],~head_stage[1:0]}});   // 1..36
 wire user_ok=(MU_HEAD==0)|~(head_position[17]|head_position[16]);
 wire hbad=&{head_context_v,stage_ok,user_ok,
             |{~host_epoch_valid,~host_fusedcap,head_token^host_tag[36:19],head_position[17:13],head_position[12:0]^host_tag[18:6]}};
 wire hev_n=(acc&~stale)|(&{~receive_slot,host_epoch_valid,~program_begin_v,~stale});
 wire fault_n=|{fault,program_begin_v&native_active,receive_slot&cbad,stale&native_active,hbad};
 assign host_epoch=host_tag[58:43];
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin host_epoch_valid<=0;host_tag<=0;host_gen<=0;host_fusedcap<=0;host_image_epoch<=0;host_image_digest<=0;fault<=0;end
  else begin
   host_epoch_valid<=hev_n;fault<=fault_n;
   if(acc)begin host_tag<=tag;host_gen<=rx_record[60:59];host_fusedcap<=rx_record[61];host_image_epoch<=rx_record[77:62];host_image_digest<=rx_record[141:78];end
  end
 end
endmodule

module qfd_program_witness_tx_bal(
 input wire ck,rst_n,send_slot,commit_v,program_ready,installed_fusedcap,program_fault,
 input wire[15:0]program_epoch,input wire[63:0]program_digest,
 output reg tx_v,tx_observed_v,output reg[547:0]tx_record,output reg fault
);
 reg held,cap;reg[15:0]epoch;reg[63:0]digest;
 wire diff=|{epoch^program_epoch,digest^program_digest,cap^installed_fusedcap};
 wire allok=&{~fault,held,~program_fault,~diff};
 wire source_ok=~program_ready|allok;
 wire fault_n=|{fault,commit_v&(~program_ready|program_fault),send_slot&program_ready&~allok};
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin held<=0;cap<=0;epoch<=0;digest<=0;tx_v<=0;tx_observed_v<=0;tx_record<=0;fault<=0;end
  else begin
   tx_v<=send_slot;tx_observed_v<=(send_slot&~program_ready)|(send_slot&allok);fault<=fault_n;
   if(commit_v)begin held<=1;cap<=installed_fusedcap;epoch<=program_epoch;digest<=program_digest;end
   if(send_slot)
    tx_record<={5'd0,4'd14,6'd63,(program_ready?epoch:program_epoch),5'd0,445'd0,program_fault,program_ready,(program_ready?cap:1'b0),(program_ready?digest:program_digest)};
  end
 end
endmodule

module qfd_sys_face_record_port_bal #(parameter integer MU_HEAD = 0)(
 input wire ck,input wire[5:0]rst_rn,input wire auth_slot,context_slot,witness_slot,
 input wire rx_v,input wire[547:0]rx_record,
 input wire execution_active,
 input wire[151:0]program_obs2,input wire[68:0]descriptor_obs,
 input wire[1:0]cfg_image_ready,
 input wire head_context_v,input wire[5:0]head_stage,
 input wire[17:0]head_token,head_position,
 output wire begin_v,auth_v,output wire[15:0]begin_epoch,auth_epoch,
 output wire[10:0]expected_pw,output wire[3:0]expected_dw,output wire[63:0]auth_digest,
 output wire program_ready,installed_fusedcap,commit_v,
 output wire[15:0]program_epoch,output wire[63:0]program_digest,
 output wire host_epoch_valid,output wire[15:0]host_epoch,
 output wire[58:0]host_tag,output wire[1:0]host_gen,
 output wire tx_v,tx_observed_v,output wire[547:0]tx_record,
 output wire fault
);
 wire af,jf,cf,wf;reg slot_fault;
 wire[1:0]sink_ready,sink_fault,sink_fusedcap;
 wire[31:0]sink_epoch;wire[127:0]sink_digest;
 reg[68:0]tt_descriptor_obs;
 always @(posedge ck or negedge rst_rn[0])
 if(!rst_rn[0])tt_descriptor_obs<=0;else tt_descriptor_obs<=descriptor_obs;
 for(genvar sink=0;sink<2;sink=sink+1)begin:g_actual_sink
 wire[75:0]pw=program_obs2[76*sink+:76];
 wire[68:0]dw=(sink==0)?tt_descriptor_obs:descriptor_obs;
 qkd_program_commit_bal u_receipt(.ck(ck),.rst_n(rst_rn[1+sink]),.execution_active(execution_active),.control_stores_ready(cfg_image_ready[sink]),
 .begin_v(begin_v),.begin_epoch(begin_epoch),.expected_pw(expected_pw),.expected_dw(expected_dw),
 .auth_v(auth_v),.auth_epoch(auth_epoch),.auth_digest(auth_digest),
 .pw_v(pw[75]),.pw_full_word(pw[74]),.pw_addr(pw[73:64]),.pw_data(pw[63:0]),
 .dw_v(dw[68]),.dw_full_word(dw[67]),.dw_addr(dw[66:64]),.dw_data(dw[63:0]),
 .commit_v(),.ready(sink_ready[sink]),.fault(sink_fault[sink]),.installed_fusedcap(sink_fusedcap[sink]),
 .commit_epoch(sink_epoch[16*sink+:16]),.commit_digest(sink_digest[64*sink+:64]));
 end
 wire context_cap;wire[15:0]context_image_epoch;wire[63:0]context_image_digest;
 always @(posedge ck or negedge rst_rn[0])
 if(!rst_rn[0])slot_fault<=0;
 else slot_fault<=|{slot_fault,auth_slot&context_slot,rx_v^(auth_slot|context_slot)};
 qfd_program_auth_rx_bal u_auth(.ck(ck),.rst_n(rst_rn[0]),.receive_slot(auth_slot),.rx_v(rx_v),.rx_record(rx_record),
 .begin_v(begin_v),.begin_epoch(begin_epoch),.expected_pw(expected_pw),.expected_dw(expected_dw),
 .auth_v(auth_v),.auth_epoch(auth_epoch),.auth_digest(auth_digest),.fault(af));
 qkd_program_commit_join_bal u_join(.ck(ck),.rst_n(rst_rn[3]),.begin_v(begin_v),.auth_v(auth_v),
 .execution_active(execution_active),.control_stores_ready(&cfg_image_ready),
 .auth_epoch(auth_epoch),.auth_digest(auth_digest),.sink_ready(sink_ready),.sink_fault(sink_fault),
 .sink_fusedcap(sink_fusedcap),.sink_epoch(sink_epoch),.sink_digest(sink_digest),
 .commit_v(commit_v),.ready(program_ready),.fault(jf),.installed_fusedcap(installed_fusedcap),
 .commit_epoch(program_epoch),.commit_digest(program_digest));
 qfd_host_native_context_rx_bal #(.MU_HEAD(MU_HEAD)) u_context(.ck(ck),.rst_n(rst_rn[4]),.receive_slot(context_slot),.rx_v(rx_v),.rx_record(rx_record),
 .program_begin_v(begin_v),.program_ready(program_ready),.installed_fusedcap(installed_fusedcap),.program_epoch(program_epoch),.program_digest(program_digest),
 .head_context_v(head_context_v),.head_stage(head_stage),.head_token(head_token),.head_position(head_position),.native_active(execution_active),
 .host_epoch_valid(host_epoch_valid),.host_epoch(host_epoch),.host_tag(host_tag),.host_gen(host_gen),
 .host_fusedcap(context_cap),.host_image_epoch(context_image_epoch),.host_image_digest(context_image_digest),.fault(cf));
 qfd_program_witness_tx_bal u_witness(.ck(ck),.rst_n(rst_rn[5]),.send_slot(witness_slot),.commit_v(commit_v),
 .program_ready(program_ready),.installed_fusedcap(installed_fusedcap),.program_fault(jf|af|slot_fault),
 .program_epoch(program_epoch),.program_digest(program_digest),.tx_v(tx_v),.tx_observed_v(tx_observed_v),.tx_record(tx_record),.fault(wf));
 assign fault=af|jf|cf|wf|slot_fault;
endmodule
