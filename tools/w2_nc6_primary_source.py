#!/usr/bin/env python3
"""Actual default-off coded primary source generator; runtime admission is separate."""
from pathlib import Path
import json
import w2_nc6_count_utility_closure as m
import w2_nc6_secondary_source as s
ROOT=Path(__file__).resolve().parents[1]
PRIMARY=[i for i in range(219) if i not in s.mapping()]
RTL=ROOT/'rtl/experimental/w2_nc6_primary_20261003/ot_w2_nc6_protected_completion.sv'

def enrollment_model():
    return dict(schema='w2.primary-enrollment.wip.v1',antecedent='10cb7849246f7ca06fe3309e577b10c099fdac29',
        NC=6,MAX_OUT=16,total_words=219,primary_words=182,secondary_words=37,physical_bits=15768,
        persistent_phase_state='only coded scheduler and coded correction contexts',
        table_mutators=9,count_mutators=6,backend_requests_per_edge=1,backend_read_captures_per_edge=1,backend_write_captures_per_edge=1,
        request_record_bits=335,read_query_bits=297,read_delivery_bits=300,write_query_bits=41,
        client_tag_bits=32,generation_bits=4,client_bits=3,scoped_identity_bits=39,address_bits=34,sector_bytes=32,
        prospective_lookup_edges={'CHECK':1,'MATCH':1,'PREP':1,'journal':4,'offer':1},
        prospective_correction_edges={'CAPTURE':4,'REPAIR':4},correction_II_min=9,
        source_count_epoch_calendar_after_request_accept={'table_commit':4,'count_load':5,'count_commit':9,'epoch_reopen':10,'next_same_client_capture':11,'next_backend_accept':19},
        same_client_request_II_min=19,
        prospective_different_client_request_II=10,
        different_client_overlap='capture at accepted+2 when old issue journal phase>=1, CHECK+3 MATCH+4 PREP+5 after old issue commit+4, reservation commit+9 backend accept+10; no same-edge free slot reuse',
        difference_vs_10cb_conditional_II18='actual secondary reopen checks CURRENT idle worker/cache, so reopening is a separate edge after count commit; not fitted to runtime',
        correction_boundary_bits=8*(72+72+10),delta_vs_target_only_boundary=8*72,
        correction_held_original='coded context72; no added72-bit pipeline register',
        query_read_mux={'normal':3,'rows_per_selected_bank':16,'utility':2,'utility_words':219,'address_capture_before_read':True},
        extra_boundary_buffer_min_x4=(8*72+7)//8,
        price='base219 coded FF/write-router/codec/control budget10cb; added original snapshot boundary576bits and minimum72BUFx4 must be composed with actual decode/load/route before physical admission',
        loaded_clock='prospective833.333ps SS setup60ps FF hold25ps; no closure claim',
        readiness={'functional_build':False,'primary_in_progress':False,'physical_build':False,'system_provider':False},
        remaining=['Russell single full NC6 runtime with actual helper and frozen source','exceptional source fault/held/reset gate enrollment','final synthesis/load/cell/route accounting before physical admission'])

def source():
    old=(ROOT/'rtl/experimental/w2_nc6_completion_20261003/ot_hdc_qwen_pc_exact_completion.sv').read_text()
    ports=old[old.index(' input wire clk'):old.index('\n);')]
    ports=ports.replace('output reg fault','output wire fault,repair_busy,\n input wire reverse_fenced')
    text='''`timescale 1ps/1ps
// WIP actual primary enrollment. No runtime/build/bridge admission.
// All current-word status is wired from the actual frozen sealed decoders.
module ot_w2_nc6_protected_completion #(
 parameter integer OPT_EXACT=0, NC=6, MAX_OUT=16, AW=34,
 parameter integer CTAGW=32, GENW=4, SIDW=3, PTAGW=35,
 parameter logic [6:0] PC_ID=0
)(
@@PORTS@@
);
 localparam integer NW=182;
 (* keep="true" *) logic [71:0] cw[0:NW-1];
 wire [43:0] P[0:218]; wire [71:0] raw[0:218],fixed_word[0:218];
 wire [218:0] clean,ce,invalid;
 logic [43:0] D[0:NW-1]; logic [NW-1:0] WE;
 wire [71:0] encoded[0:NW-1];
 wire [2663:0] secondary_raw,secondary_fixed;
 wire [1627:0] secondary_payload;
 wire [36:0] secondary_clean,secondary_ce,secondary_bad;
 wire [191:0] table_state;
 wire [95:0] table_clean,table_bad;
 logic [5:0] count_pending,offer_drained,cancel_request,reopen_epoch;
 logic [17:0] reserve_roles,intents;
 wire [17:0] committed;
 wire [5:0] request_open,completion_open;
 wire permit,secondary_idle,secondary_rearm;
 logic all_core_clean,any_core_bad,core_bad,plan_bad,core_idle,context_live;
 integer fault_i,fault_j,fault_k,fault_c,fault_a,fault_n,fault_slot;
 logic [43:0] fault_row,fault_target;logic [38:0] fault_key;logic [15:0] fault_mask;logic fault_busy;
 logic [351:0] H,Hn,RQ,RQn,RD,RDn;
 logic [40:0] WQ,WQn;
 logic [4:0] S[0:5],Sn[0:5];
 logic [78:0] C,Cn;
 logic [86:0] J[0:8],Jn[0:8];
 logic [64:0] Q[0:5],Qn[0:5];
 logic [95:0] X[0:7],Xn[0:7];
 logic [7:0] context_clean,context_changed,peer_repaired;
 logic [1:0] scrub_v;
 logic [19:0] scrub_index;
 logic [143:0] scrub_original,scrub_repaired;
 wire [1:0] scrub_ready;
 wire [15767:0] controller_raw,controller_fixed;
 wire [9635:0] controller_payload;
 wire [767:0] context_current,context_next;
 wire [7:0] repair_context_we,repair_scrub_v;
 wire [79:0] repair_index;
 wire [575:0] repair_original,repair_candidate;
 wire [7:0] repair_retire_ready;
 logic [7:0] primary_retire_offer,secondary_retire_offer;
 wire correction_busy,correction_error;
 logic [2:0] rr,rrn;
 logic [2:0] phase[0:2];
 logic [43:0] row,target;
 logic [38:0] key;
 logic [15:0] mask;
 logic req_offer,read_offer;
 logic [5:0] wr_offer;
 logic [17:0] candidate_intents;
 integer i,j,k,c,a,n,slot,hits,choice,rc,wc,bank,offset,eng,owner;
 integer view_i,view_j,retire_e,retire_a;
 integer offer_i,offer_k,offer_c,offer_a;logic [43:0] offer_target;logic offer_found;
 integer count_i,count_k,count_c,count_a;logic [43:0] count_target;logic count_found;
 logic found,busy;

 function automatic integer global_index(input integer x);
 begin case(x)
@@GMAP@@
 default:global_index=-1;endcase end
 endfunction
 function automatic integer local_index(input integer x);
 begin case(x)
@@LMAP@@
 default:local_index=-1;endcase end
 endfunction
 function automatic integer payload_bits(input integer x);
 begin case(x)
@@PB@@
 default:payload_bits=0;endcase end
 endfunction
 function automatic integer kind(input integer x);
 begin case(x)
@@KIND@@
 default:kind=0;endcase end
 endfunction
 function automatic [71:0] seal(input [43:0] p,input integer wi);
 reg [63:0] data64;reg [71:0] code;reg parity;integer pos,b,t;
 begin
 data64={3'(kind(wi)),10'(wi),PC_ID,p};code=0;t=0;
 for(pos=1;pos<=71;pos=pos+1)if((pos&(pos-1))!=0)begin code[pos-1]=data64[t];t=t+1;end
 for(b=0;b<7;b=b+1)begin parity=0;
 for(pos=1;pos<=71;pos=pos+1)if((pos&(1<<b))!=0)parity=parity^code[pos-1];
 code[(1<<b)-1]=parity;end
 code[71]=^code[70:0];seal=code;
 end endfunction
 function automatic [351:0] get_record(input integer base,input integer chunks);
 integer t;begin get_record=0;for(t=0;t<chunks;t=t+1)get_record[44*t+:44]=P[base+t];end
 endfunction
 task automatic put_record(input integer base,input integer chunks,input [351:0] value);
 integer t,l;begin for(t=0;t<chunks;t=t+1)begin l=local_index(base+t);if(l>=0)begin D[l]=value[44*t+:44];WE[l]=1;end end end
 endtask
 task automatic prepare(input integer role,input integer address,input [43:0] value);
 begin
 if(J[role][86])plan_bad=1;
 else begin
 Jn[role]=0;Jn[role][71:0]=seal(value,address);
 Jn[role][81:72]=10'(address);Jn[role][85:82]=P[address][42:39];Jn[role][86]=1;
 Cn[9+2*role+:2]=0;
 end
 end
 endtask
 function automatic [63:0] decode_data(input [71:0] value);
 integer pos,t;begin decode_data=0;t=0;
 for(pos=1;pos<=71;pos=pos+1)if((pos&(pos-1))!=0)begin decode_data[t]=value[pos-1];t=t+1;end
 end endfunction
 function automatic [6:0] syndrome(input [71:0] value);
 integer pos,b;begin syndrome=0;
 for(b=0;b<7;b=b+1)for(pos=1;pos<=71;pos=pos+1)if((pos&(1<<b))!=0)syndrome[b]=syndrome[b]^value[pos-1];
 end endfunction
 function automatic integer popcount16(input [15:0] value);
 integer t;begin popcount16=0;for(t=0;t<16;t=t+1)popcount16=popcount16+integer'(value[t]);end
 endfunction
 function automatic qualified(input [43:0] oldrow,newrow,input [3:0] version,input integer role);
 begin
 qualified=oldrow[42:39]==version;
 if(role==0)begin
 if(newrow[1:0]==0&&newrow[43])qualified=qualified&&oldrow[1:0]==0&&!oldrow[43]&&newrow[42:39]==version;
 else if(newrow[1:0]==1)qualified=qualified&&oldrow[1:0]==0&&oldrow[43]&&!newrow[43]&&newrow[38:2]==oldrow[38:2]&&newrow[42:39]==version;
 else qualified=qualified&&newrow[1:0]==0&&oldrow[1:0]==0&&oldrow[43]&&!newrow[43]&&newrow[38:2]==oldrow[38:2]&&newrow[42:39]==4'(version+1);
 end else begin
 qualified=qualified&&!oldrow[43]&&!newrow[43]&&oldrow[38:2]==newrow[38:2];
 if(role==1&&newrow[1:0]==2)qualified=qualified&&oldrow[1:0]==1&&!oldrow[38]&&newrow[42:39]==version;
 else if(role==2)qualified=qualified&&oldrow[1:0]==1&&newrow[1:0]==3&&oldrow[38]&&newrow[42:39]==version;
 else qualified=qualified&&oldrow[1:0]==(role==1?2:3)&&newrow[1:0]==0&&oldrow[38]==(role!=1)&&newrow[42:39]==4'(version+1);
 end
 end endfunction
 generate for(genvar l=0;l<NW;l=l+1)begin:primary_word
 localparam integer G=global_index(l),PB=payload_bits(G);
 wire uncorrectable,seal_ok,padding_ok;
 wire [43:0] bounded={{(44-PB){1'b0}},D[l][PB-1:0]};
 ot_w2_sealed_secded72 #(.PC_ID(PC_ID),.WORD_INDEX(10'(G)),.WORD_KIND(3'(kind(G))),.PAYLOAD_BITS(PB)) decoder(
 .payload(44'b0),.current_word(cw[l]),.encoded_word(),.syndrome(),.overall_odd(),.clean(),
 .correctable(ce[G]),.uncorrectable(uncorrectable),.seal_ok(seal_ok),.padding_ok(padding_ok),
 .release_clean(clean[G]),.repaired_payload(P[G]),.repaired_word(fixed_word[G]));
 ot_w2_sealed_secded72 #(.PC_ID(PC_ID),.WORD_INDEX(10'(G)),.WORD_KIND(3'(kind(G))),.PAYLOAD_BITS(PB)) encoder(
 .payload(bounded),.current_word(72'b0),.encoded_word(encoded[l]),.syndrome(),.overall_odd(),.clean(),
 .correctable(),.uncorrectable(),.seal_ok(),.padding_ok(),.release_clean(),.repaired_payload(),.repaired_word());
 assign raw[G]=cw[l];assign invalid[G]=uncorrectable||!seal_ok||!padding_ok;
 end
@@SECONDARY_ASSIGN@@
 for(genvar r=0;r<96;r=r+1)begin:table_view
 assign table_state[2*r+:2]=P[r][1:0];assign table_clean[r]=clean[r];assign table_bad[r]=invalid[r];
 end endgenerate
 generate for(genvar g=0;g<219;g=g+1)begin:repair_view
 assign controller_raw[72*g+:72]=raw[g];assign controller_fixed[72*g+:72]=fixed_word[g];
 assign controller_payload[44*g+:44]=P[g];
 end
 for(genvar e=0;e<8;e=e+1)begin:context_view
 assign context_current[96*e+:96]={P[147+3*e][7:0],P[146+3*e],P[145+3*e]};
 end endgenerate
 ot_w2_nc6_correction_control correction(
 .enable(OPT_EXACT!=0&&rst_n),.context_current(context_current),.context_clean(context_clean),
 .current_raw(controller_raw),.current_fixed(controller_fixed),.current_payload(controller_payload),
 .current_clean(clean),.current_ce(ce),.current_bad(invalid),
 .context_next(context_next),.context_we(repair_context_we),
 .scrub_v(repair_scrub_v),.scrub_index(repair_index),.scrub_original(repair_original),.scrub_candidate(repair_candidate),
 .retire_ready(repair_retire_ready),.busy(correction_busy),.error(correction_error));
 ot_w2_nc6_coded_secondary_acyclic #(.OPT_PROTECTION(OPT_EXACT),.PC_ID(PC_ID)) secondary(
 .clk(clk),.rst_n(rst_n),.admission_stop(admission_stop),.table_state(table_state),
 .table_clean(table_clean),.table_bad(table_bad),.table_pending(count_pending),.offer_copies_drained(offer_drained),
 .other_clean(all_core_clean&&!context_live),.other_bad(any_core_bad),.logic_fault(core_bad),
 .reserve_roles(reserve_roles),.accept_intent(intents),.cancel_request(cancel_request),.reopen_epoch(reopen_epoch),
 .commit_roles(committed),.request_bank_open(request_open),.completion_bank_open(completion_open),
 .normal_permit(permit),.repair_busy(repair_busy),.fault(fault),
 .rearm_v(rearm_v),.provider_fenced(provider_fenced),.reverse_fenced(reverse_fenced),.reset_fenced(reset_fenced),
 .local_other_idle(core_idle),.rearm_ready(secondary_rearm),.local_idle(secondary_idle),
 .scrub_v(scrub_v),.scrub_index(scrub_index),.scrub_original(scrub_original),.scrub_repaired(scrub_repaired),.scrub_ready(scrub_ready),
 .inspect_original(secondary_raw),.inspect_corrected(secondary_fixed),.inspect_payload(secondary_payload),
 .inspect_clean(secondary_clean),.inspect_ce(secondary_ce),.inspect_bad(secondary_bad));
 assign idle=core_idle&&secondary_idle;
 assign rearm_rdy=secondary_rearm;
 initial if(NC!=6||MAX_OUT!=16||AW!=34||CTAGW!=32||GENW!=4||SIDW!=3||PTAGW!=35)
 $fatal(1,"full protected NC6/MAX16/AW34/customer32/gen4 required");

 // CURRENT-only views: never depend on permit, retirement or next-context.
 always_comb begin
 all_core_clean=1;any_core_bad=0;context_live=0;core_idle=1;
 for(view_i=0;view_i<NW;view_i=view_i+1)begin
 all_core_clean=all_core_clean&&clean[global_index(view_i)];
 any_core_bad=any_core_bad||invalid[global_index(view_i)];end
 for(view_i=0;view_i<8;view_i=view_i+1)begin
 X[view_i]=96'(get_record(145+3*view_i,3));
 context_clean[view_i]=clean[145+3*view_i]&&clean[146+3*view_i]&&clean[147+3*view_i];
 if(X[view_i][95]||!context_clean[view_i])context_live=1;
 end
 H=get_record(96,8);RQ=get_record(104,7);RD=get_record(112,7);WQ=41'(get_record(111,1));
 C=79'(get_record(187,2));rr=P[131][2:0];
 for(view_i=0;view_i<3;view_i=view_i+1)phase[view_i]=C[3*view_i+:3];
 for(view_i=0;view_i<9;view_i=view_i+1)J[view_i]=87'(get_record(169+2*view_i,2));
 for(view_i=0;view_i<6;view_i=view_i+1)begin Q[view_i]=65'(get_record(133+2*view_i,2));S[view_i]=P[119+view_i][4:0];end
 for(view_i=0;view_i<96;view_i=view_i+1)if(P[view_i][1:0]!=0||P[view_i][43])core_idle=0;
 if(H[0]||RQ[0]||RD[0]||WQ[0]||context_live)core_idle=0;
 for(view_i=0;view_i<9;view_i=view_i+1)if(J[view_i][86])core_idle=0;
 for(view_i=0;view_i<6;view_i=view_i+1)if(S[view_i][0]||Q[view_i][63])core_idle=0;
 end
 generate for(genvar re=0;re<8;re=re+1)begin:retirement_feedback
 if(re<6)assign repair_retire_ready[re]=primary_retire_offer[re];
 else assign repair_retire_ready[re]=primary_retire_offer[re]||(secondary_retire_offer[re]&&scrub_ready[re-6]);
 end endgenerate
 // Retirement eligibility does not consume next-context writeback.
 always_comb begin
 scrub_v=0;scrub_index=0;scrub_original=0;scrub_repaired=0;primary_retire_offer=0;secondary_retire_offer=0;
 retire_a=0;
 if(OPT_EXACT&&rst_n&&!any_core_bad&&!correction_error&&!core_bad)begin
 for(retire_e=0;retire_e<8;retire_e=retire_e+1)if(repair_scrub_v[retire_e])begin
 retire_a=integer'(repair_index[10*retire_e+:10]);
 if(retire_a<219&&ce[retire_a]&&!invalid[retire_a]&&raw[retire_a]==repair_original[72*retire_e+:72]&&fixed_word[retire_a]==repair_candidate[72*retire_e+:72])begin
 if(local_index(retire_a)>=0)primary_retire_offer[retire_e]=1;
 else if(retire_e>=6)begin
 scrub_v[retire_e-6]=1;scrub_index[10*(retire_e-6)+:10]=10'(retire_a);
 scrub_original[72*(retire_e-6)+:72]=repair_original[72*retire_e+:72];
 scrub_repaired[72*(retire_e-6)+:72]=repair_candidate[72*retire_e+:72];
 secondary_retire_offer[retire_e]=1;end
 end end end
 end
 // Semantic fault is independent of permit, bank eligibility and next state.
 always_comb begin
 core_bad=0;fault_i=0;fault_j=0;fault_k=0;fault_c=0;fault_a=0;fault_n=0;fault_slot=0;
 fault_row=0;fault_target=0;fault_key=0;fault_mask=0;fault_busy=0;
 if(rr>=6||phase[0]>5||phase[1]>4||phase[2]>4)core_bad=1;
 if(H[0]&&H[4:2]>=6||RQ[0]&&RQ[4:2]>=6||RD[0]&&RD[3:1]>=6||WQ[0]&&WQ[4:2]>=6)core_bad=1;
 if(H[0]&&!admission_stop&&H[4:2]<6)begin fault_c=integer'(H[4:2]);
 if(!c_req_v[fault_c]||c_req_we[fault_c]!=H[1]||c_req_addr[fault_c*34+:34]!=H[42:9]||
 c_req_tag[fault_c*32+:32]!=H[74:43]||c_req_gen[fault_c*4+:4]!=H[78:75]||c_req_data[fault_c*256+:256]!=H[334:79])core_bad=1;end
 if(all_core_clean)begin
 if((phase[0]!=0)!=H[0]||(phase[1]!=0)!=RQ[0]||(phase[2]!=0)!=WQ[0])core_bad=1;
 for(fault_n=0;fault_n<3;fault_n=fault_n+1)begin
 if(Q[2*fault_n][63]!=(phase[fault_n]>=2)||Q[2*fault_n+1][63]!=(phase[fault_n]>=3))core_bad=1;
 end
 end
 for(fault_i=0;fault_i<9;fault_i=fault_i+1)if(J[fault_i][86])begin
 fault_a=integer'(J[fault_i][81:72]);if(fault_a>=96)core_bad=1;
 else begin
 fault_target=44'(decode_data(J[fault_i][71:0]));
 if(J[fault_i][71:0]!=seal(fault_target,fault_a)||!qualified(P[fault_a],fault_target,J[fault_i][85:82],fault_i))core_bad=1;
 if(fault_i>=3&&fault_a/16!=fault_i-3)core_bad=1;
 if(fault_i==0&&fault_target[43]&&(!H[0]||fault_a!=16*integer'(H[4:2])+integer'(H[8:5])||fault_target[33:2]!=H[74:43]||fault_target[37:34]!=H[78:75]||fault_target[38]!=H[1]))core_bad=1;
 if(fault_i==1&&fault_target[1:0]==2&&(!RQ[0]||fault_a!=16*integer'(RQ[4:2])+integer'(Q[3][58:55])||fault_target[33:2]!=RQ[36:5]||fault_target[37:34]!=RQ[40:37]))core_bad=1;
 if(fault_i==1&&fault_target[1:0]==0&&(fault_a!=16*integer'(RD[3:1])+integer'(RD[7:4])||fault_target[33:2]!=RD[39:8]||fault_target[37:34]!=RD[43:40]))core_bad=1;
 if(fault_i==2&&(!WQ[0]||fault_a!=16*integer'(WQ[4:2])+integer'(Q[5][58:55])||fault_target[33:2]!=WQ[36:5]||fault_target[37:34]!=WQ[40:37]))core_bad=1;
 if(fault_i>=3&&fault_a!=16*(fault_i-3)+integer'(S[fault_i-3][4:1]))core_bad=1;
 end end
 if(all_core_clean)begin
 if(H[0]&&phase[0]==5&&H[4:2]<6)begin fault_a=16*integer'(H[4:2])+integer'(H[8:5]);fault_row=P[fault_a];
 if(fault_row[1:0]!=0||!fault_row[43]||fault_row[38]!=H[1]||fault_row[33:2]!=H[74:43]||fault_row[37:34]!=H[78:75])core_bad=1;end
 if(RD[0]&&RD[3:1]<6)begin fault_a=16*integer'(RD[3:1])+integer'(RD[7:4]);fault_row=P[fault_a];
 if(fault_row[1:0]!=2||fault_row[43]||fault_row[38]||fault_row[33:2]!=RD[39:8]||fault_row[37:34]!=RD[43:40])core_bad=1;end
 for(fault_i=0;fault_i<6;fault_i=fault_i+1)if(S[fault_i][0])begin fault_a=16*fault_i+integer'(S[fault_i][4:1]);
 if(P[fault_a][1:0]!=3||P[fault_a][43]||!P[fault_a][38])core_bad=1;end
 end
 if(all_core_clean&&!context_live&&OPT_EXACT&&rst_n)begin
 if(RQ[0]&&RQ[1]||WQ[0]&&WQ[1])core_bad=1;
 for(fault_n=0;fault_n<3;fault_n=fault_n+1)begin
 fault_c=(fault_n==0)?integer'(H[4:2]):(fault_n==1)?integer'(RQ[4:2]):integer'(WQ[4:2]);
 fault_key=(fault_n==0)?{H[4:2],H[74:43],H[78:75]}:(fault_n==1)?{RQ[4:2],RQ[36:5],RQ[40:37]}:{WQ[4:2],WQ[36:5],WQ[40:37]};
 if(phase[fault_n]!=0&&fault_c>=6)core_bad=1;
 if(fault_c<6&&!(fault_n==0&&admission_stop))begin
 if(phase[fault_n]==1&&fault_n==0)begin
 fault_busy=0;for(fault_j=0;fault_j<9;fault_j=fault_j+1)if(J[fault_j][86]&&integer'(J[fault_j][81:72])/16==fault_c)fault_busy=1;
 if(!fault_busy)for(fault_k=0;fault_k<16;fault_k=fault_k+1)begin fault_row=P[16*fault_c+fault_k];
 if((fault_row[1:0]!=0||fault_row[43])&&fault_row[33:2]==H[74:43]&&fault_row[37:34]==H[78:75]&&fault_row[38]==H[1])core_bad=1;
 end end
 if(phase[fault_n]==2)begin
 fault_mask=0;fault_slot=0;
 for(fault_k=15;fault_k>=0;fault_k=fault_k-1)begin fault_row=P[16*fault_c+fault_k];
 if(fault_n==0&&fault_row[1:0]==0&&!fault_row[43]||fault_n!=0&&fault_row[1:0]==1&&!fault_row[43]&&fault_row[38]==(fault_n==2)&&fault_row[33:2]==fault_key[35:4]&&fault_row[37:34]==fault_key[3:0])begin fault_mask[fault_k]=1;fault_slot=fault_k;end
 end
 if(!Q[2*fault_n][63]||Q[2*fault_n][64]||Q[2*fault_n][54:16]!=fault_key||Q[2*fault_n][15:0]!=fault_mask||Q[2*fault_n][58:55]!=4'(fault_slot)||
 (fault_n!=0&&popcount16(fault_mask)!=1)||fault_n==0&&fault_mask==0)core_bad=1;
 end
 if(phase[fault_n]==3)begin
 if(!Q[2*fault_n+1][63]||Q[2*fault_n+1][64]||Q[2*fault_n+1][54:16]!=fault_key)core_bad=1;
 else begin
 fault_a=16*fault_c+integer'(Q[2*fault_n+1][58:55]);fault_row=P[fault_a];
 if(fault_row[42:39]!=Q[2*fault_n+1][62:59])core_bad=1;
 if(fault_n==0)begin if(fault_row[1:0]!=0||fault_row[43])core_bad=1;end
 else if(fault_row[1:0]!=1||fault_row[43]||fault_row[38]!=(fault_n==2)||fault_row[33:2]!=fault_key[35:4]||fault_row[37:34]!=fault_key[3:0])core_bad=1;
 if(J[fault_n][86])core_bad=1;
 end end
 end end
 // Journal availability is checked from OLD state, before any handshake.
 if((H[0]&&phase[0]==5&&!admission_stop&&H[4:2]<6)&&p_req_rdy&&J[0][86])core_bad=1;
 if((RD[0]&&RD[3:1]<6)&&c_rsp_rdy[integer'(RD[3:1])]&&J[1][86])core_bad=1;
 for(fault_c=0;fault_c<6;fault_c=fault_c+1)if(S[fault_c][0]&&c_wr_done_rdy[fault_c]&&J[fault_c+3][86])core_bad=1;
 if(admission_stop&&H[0]&&H[4:2]<6&&(phase[0]==5||phase[0]==4&&!J[0][86])&&J[0][86])core_bad=1;
 end
 if(correction_error)core_bad=1;
 end
 // Pre-permit intents/status, isolated from state writeback and retire ready.
 always_comb begin
 count_pending=0;offer_drained=0;reopen_epoch=0;
 count_i=0;count_k=0;count_c=0;count_a=0;count_target=0;count_found=0;
 // Pending role0 contributes only when its count_target is ISSUED; role1 retirement
 // is identified by old RD_HELD, and local WR retire roles3..8 always count.
 count_target=44'(decode_data(J[0][71:0]));
 if(J[0][86]&&J[0][81:72]<96&&count_target[1:0]==1)count_pending[integer'(J[0][81:72])/16]=1;
 if(J[1][86]&&J[1][81:72]<96&&P[integer'(J[1][81:72])][1:0]==2)count_pending[integer'(J[1][81:72])/16]=1;
 for(count_i=3;count_i<9;count_i=count_i+1)if(J[count_i][86])count_pending[count_i-3]=1;
 for(count_i=0;count_i<6;count_i=count_i+1)begin
 offer_drained[count_i]=(!P[213+count_i][3]||((!H[0]||H[4:2]!=3'(count_i))&&(!Q[0][63]||Q[0][54:52]!=3'(count_i))&&
 (!Q[1][63]||Q[1][54:52]!=3'(count_i))&&(!J[0][86]||integer'(J[0][81:72])/16!=count_i)))&&
 (!P[213+count_i][4]||((!RD[0]||RD[3:1]!=3'(count_i))&&(!J[1][86]||integer'(J[1][81:72])/16!=count_i)))&&
 (!P[213+count_i][5]||(!S[count_i][0]&&!J[count_i+3][86]));
 if(P[213+count_i][7]&&P[213+count_i][2:0]==P[213+count_i][5:3]&&offer_drained[count_i]&&!count_pending[count_i]&&
 !P[207+count_i][3]&&!P[191+3*count_i][4])reopen_epoch[count_i]=1;
 end
 end
 // CURRENT pre-permit request and completion intents.
 always_comb begin
 cancel_request=0;reserve_roles=0;intents=0;req_offer=0;read_offer=0;wr_offer=0;candidate_intents=0;
 offer_i=0;offer_k=0;offer_c=0;offer_a=0;offer_target=0;offer_found=0;
 req_offer=H[0]&&phase[0]==5&&!admission_stop&&H[4:2]<6;
 read_offer=RD[0]&&RD[3:1]<6;
 for(offer_i=0;offer_i<6;offer_i=offer_i+1)wr_offer[offer_i]=S[offer_i][0];
 if(req_offer&&p_req_rdy)candidate_intents[3*integer'(H[4:2])]=1;
 if(read_offer&&c_rsp_rdy[integer'(RD[3:1])])candidate_intents[3*integer'(RD[3:1])+1]=1;
 for(offer_i=0;offer_i<6;offer_i=offer_i+1)if(wr_offer[offer_i]&&c_wr_done_rdy[offer_i])candidate_intents[3*offer_i+2]=1;
 intents=candidate_intents;
 // Reserve intent is offer_a CURRENT offer; only common permit commits it.
 offer_target=44'(decode_data(J[0][71:0]));
 if(all_core_clean&&!context_live&&OPT_EXACT&&rst_n)begin
 if(!H[0]&&phase[0]==0&&!admission_stop&&(!J[0][86]||(offer_target[1:0]==1&&C[9+:2]>=1)))begin
 offer_found=0;for(offer_k=0;offer_k<6;offer_k=offer_k+1)begin offer_c=integer'(rr)+offer_k;if(offer_c>=6)offer_c=offer_c-6;
 if(!offer_found&&c_req_v[offer_c]&&request_open[offer_c])begin offer_found=1;reserve_roles[3*offer_c]=1;end end end
 if(phase[1]==4&&RQ[0]&&!RD[0]&&RQ[4:2]<6)begin
 offer_c=integer'(RQ[4:2]);offer_a=16*offer_c+integer'(Q[3][58:55]);
 if((!J[1][86]&&P[offer_a][1:0]==2||J[1][86]&&C[11+:2]==3)&&completion_open[offer_c])reserve_roles[3*offer_c+1]=1;
 end
 for(offer_c=0;offer_c<6;offer_c=offer_c+1)if(!S[offer_c][0]&&completion_open[offer_c])begin
 offer_found=0;for(offer_k=0;offer_k<16;offer_k=offer_k+1)if(P[16*offer_c+offer_k][1:0]==3&&!P[16*offer_c+offer_k][43])offer_found=1;
 if(offer_found)reserve_roles[3*offer_c+2]=1;end
 if(admission_stop&&H[0]&&H[4:2]<6)begin offer_c=integer'(H[4:2]);
 if(P[213+offer_c][0]&&!P[213+offer_c][3])cancel_request[offer_c]=1;end
 end
 end
 always_comb begin
 WE=0;plan_bad=0;
 for(i=0;i<NW;i=i+1)D[i]=P[global_index(i)];
 context_changed=0;peer_repaired=0;
 for(i=0;i<8;i=i+1)Xn[i]=X[i];
 Hn=H;RQn=RQ;RDn=RD;WQn=WQ;Cn=C;rrn=rr;
 for(i=0;i<9;i=i+1)Jn[i]=J[i];
 for(i=0;i<6;i=i+1)begin Qn[i]=Q[i];Sn[i]=S[i];end
 row=0;target=0;key=0;mask=0;found=0;busy=0;
 j=0;k=0;c=0;a=0;n=0;slot=0;hits=0;choice=0;rc=0;wc=0;bank=0;offset=0;eng=0;owner=0;
 if(rr>=6||phase[0]>5||phase[1]>4||phase[2]>4)plan_bad=1;
 if(H[0]&&H[4:2]>=6||RQ[0]&&RQ[4:2]>=6||RD[0]&&RD[3:1]>=6||WQ[0]&&WQ[4:2]>=6)plan_bad=1;
 if(H[0]&&!admission_stop&&H[4:2]<6)begin c=integer'(H[4:2]);
 if(!c_req_v[c]||c_req_we[c]!=H[1]||c_req_addr[c*34+:34]!=H[42:9]||
 c_req_tag[c*32+:32]!=H[74:43]||c_req_gen[c*4+:4]!=H[78:75]||c_req_data[c*256+:256]!=H[334:79])plan_bad=1;end
 if(all_core_clean)begin
 if((phase[0]!=0)!=H[0]||(phase[1]!=0)!=RQ[0]||(phase[2]!=0)!=WQ[0])plan_bad=1;
 for(n=0;n<3;n=n+1)begin
 if(Q[2*n][63]!=(phase[n]>=2)||Q[2*n+1][63]!=(phase[n]>=3))plan_bad=1;
 end
 end
 for(i=0;i<9;i=i+1)if(J[i][86])begin
 a=integer'(J[i][81:72]);if(a>=96)plan_bad=1;
 else begin
 target=44'(decode_data(J[i][71:0]));
 if(J[i][71:0]!=seal(target,a)||!qualified(P[a],target,J[i][85:82],i))plan_bad=1;
 if(i>=3&&a/16!=i-3)plan_bad=1;
 if(i==0&&target[43]&&(!H[0]||a!=16*integer'(H[4:2])+integer'(H[8:5])||target[33:2]!=H[74:43]||target[37:34]!=H[78:75]||target[38]!=H[1]))plan_bad=1;
 if(i==1&&target[1:0]==2&&(!RQ[0]||a!=16*integer'(RQ[4:2])+integer'(Q[3][58:55])||target[33:2]!=RQ[36:5]||target[37:34]!=RQ[40:37]))plan_bad=1;
 if(i==1&&target[1:0]==0&&(a!=16*integer'(RD[3:1])+integer'(RD[7:4])||target[33:2]!=RD[39:8]||target[37:34]!=RD[43:40]))plan_bad=1;
 if(i==2&&(!WQ[0]||a!=16*integer'(WQ[4:2])+integer'(Q[5][58:55])||target[33:2]!=WQ[36:5]||target[37:34]!=WQ[40:37]))plan_bad=1;
 if(i>=3&&a!=16*(i-3)+integer'(S[i-3][4:1]))plan_bad=1;
 end end
 // Outputs are frozen tuples from coded records, never the live input bus.
 c_req_rdy=0;c_rsp_v=0;c_wr_done_v=0;c_rsp_tag=0;c_rsp_gen=0;c_rsp_data=0;c_wr_done_tag=0;c_wr_done_gen=0;
 p_req_v=0;p_req_we=H[1];p_req_addr=H[42:9];p_req_tag={H[4:2],H[74:43]};p_req_gen=H[78:75];p_req_data=H[334:79];
 p_rsp_rdy=0;p_wr_done_ready=0;
 if(all_core_clean)begin
 if(H[0]&&phase[0]==5&&H[4:2]<6)begin a=16*integer'(H[4:2])+integer'(H[8:5]);row=P[a];
 if(row[1:0]!=0||!row[43]||row[38]!=H[1]||row[33:2]!=H[74:43]||row[37:34]!=H[78:75])plan_bad=1;end
 if(RD[0]&&RD[3:1]<6)begin a=16*integer'(RD[3:1])+integer'(RD[7:4]);row=P[a];
 if(row[1:0]!=2||row[43]||row[38]||row[33:2]!=RD[39:8]||row[37:34]!=RD[43:40])plan_bad=1;end
 for(i=0;i<6;i=i+1)if(S[i][0])begin a=16*i+integer'(S[i][4:1]);
 if(P[a][1:0]!=3||P[a][43]||!P[a][38])plan_bad=1;end
 end
 if(permit&&!core_bad&&OPT_EXACT&&rst_n)begin
 p_req_v=req_offer;if(req_offer)c_req_rdy[integer'(H[4:2])]=p_req_rdy;
 p_rsp_rdy=!RQ[0]&&phase[1]==0&&!RD[0]&&!J[1][86];
 p_wr_done_ready=!WQ[0]&&phase[2]==0&&!J[2][86];
 if(read_offer)begin c=integer'(RD[3:1]);c_rsp_v[c]=1;c_rsp_tag[c*32+:32]=RD[39:8];c_rsp_gen[c*4+:4]=RD[43:40];c_rsp_data[c*256+:256]=RD[299:44];end
 for(i=0;i<6;i=i+1)if(wr_offer[i])begin a=16*i+integer'(S[i][4:1]);
 c_wr_done_v[i]=1;c_wr_done_tag[i*32+:32]=P[a][33:2];c_wr_done_gen[i*4+:4]=P[a][37:34];end
 end
 if(all_core_clean&&!context_live&&OPT_EXACT&&rst_n)begin
 // Plan from OLD records/intents; the common permit gates every write below.
 // Matching faults are independent of permit, avoiding a ready/fault loop.
 if(RQ[0]&&RQ[1]||WQ[0]&&WQ[1])plan_bad=1;
 target=44'(decode_data(J[0][71:0]));
 if(!H[0]&&phase[0]==0&&!admission_stop&&(!J[0][86]||(target[1:0]==1&&C[9+:2]>=1)))begin
 found=0;
 for(k=0;k<6;k=k+1)begin c=integer'(rr)+k;if(c>=6)c=c-6;
 if(!found&&c_req_v[c]&&request_open[c])begin
 found=1;Hn=0;Hn[0]=1;Hn[1]=c_req_we[c];Hn[4:2]=3'(c);
 Hn[42:9]=c_req_addr[34*c+:34];Hn[74:43]=c_req_tag[32*c+:32];
 Hn[78:75]=c_req_gen[4*c+:4];Hn[334:79]=c_req_data[256*c+:256];
 Cn[2:0]=1;
 end end end
 if(p_rsp_v&&p_rsp_rdy)begin
 RQn=0;RQn[0]=1;RQn[4:2]=p_rsp_tag[34:32];RQn[36:5]=p_rsp_tag[31:0];RQn[40:37]=p_rsp_gen;RQn[296:41]=p_rsp_data;
 RQn[1]=req_offer&&p_req_rdy&&!H[1]&&p_rsp_tag=={H[4:2],H[74:43]}&&p_rsp_gen==H[78:75];Cn[5:3]=1;
 end
 if(p_wr_done_v&&p_wr_done_ready)begin
 WQn=0;WQn[0]=1;WQn[4:2]=p_wr_done_tag[34:32];WQn[36:5]=p_wr_done_tag[31:0];WQn[40:37]=p_wr_done_gen;
 WQn[1]=req_offer&&p_req_rdy&&H[1]&&p_wr_done_tag=={H[4:2],H[74:43]}&&p_wr_done_gen==H[78:75];Cn[8:6]=1;
 end
 for(n=0;n<3;n=n+1)begin
 c=(n==0)?integer'(H[4:2]):(n==1)?integer'(RQ[4:2]):integer'(WQ[4:2]);
 key=(n==0)?{H[4:2],H[74:43],H[78:75]}:(n==1)?{RQ[4:2],RQ[36:5],RQ[40:37]}:{WQ[4:2],WQ[36:5],WQ[40:37]};
 if(phase[n]!=0&&c>=6)plan_bad=1;
 if(c<6&&phase[n]==1&&!(n==0&&admission_stop))begin
 busy=0;for(j=0;j<9;j=j+1)if(J[j][86]&&integer'(J[j][81:72])/16==c)busy=1;
 if(!busy)begin
 mask=0;hits=0;slot=0;
 for(k=15;k>=0;k=k-1)begin a=16*c+k;row=P[a];
 if(n==0)begin
 if((row[1:0]!=0||row[43])&&row[33:2]==H[74:43]&&row[37:34]==H[78:75]&&row[38]==H[1])plan_bad=1;
 if(row[1:0]==0&&!row[43])begin mask[k]=1;slot=k;hits=hits+1;end
 end else if(row[1:0]==1&&!row[43]&&row[38]==(n==2)&&row[33:2]==key[35:4]&&row[37:34]==key[3:0])begin mask[k]=1;slot=k;hits=hits+1;end
 end
 Qn[2*n]=0;Qn[2*n][15:0]=mask;Qn[2*n][54:16]=key;Qn[2*n][58:55]=4'(slot);
 Qn[2*n][62:59]=P[16*c+slot][42:39];Qn[2*n][63]=1;Qn[2*n][64]=(n==0)?hits==0:hits!=1;
 Cn[3*n+:3]=2;
 end end
 if(c<6&&phase[n]==2&&!(n==0&&admission_stop))begin
 mask=0;slot=0;
 for(k=15;k>=0;k=k-1)begin row=P[16*c+k];
 if(n==0&&row[1:0]==0&&!row[43]||n!=0&&row[1:0]==1&&!row[43]&&row[38]==(n==2)&&row[33:2]==key[35:4]&&row[37:34]==key[3:0])begin mask[k]=1;slot=k;end
 end
 if(!Q[2*n][63]||Q[2*n][64]||Q[2*n][54:16]!=key||Q[2*n][15:0]!=mask||Q[2*n][58:55]!=4'(slot)||
 (n!=0&&popcount16(mask)!=1)||n==0&&mask==0)plan_bad=1;
 else begin Qn[2*n+1]=Q[2*n];Cn[3*n+:3]=3;end
 end
 if(c<6&&phase[n]==3&&!(n==0&&admission_stop))begin
 if(!Q[2*n+1][63]||Q[2*n+1][64]||Q[2*n+1][54:16]!=key)plan_bad=1;
 else begin
 a=16*c+integer'(Q[2*n+1][58:55]);row=P[a];target=row;
 if(row[42:39]!=Q[2*n+1][62:59])plan_bad=1;
 if(n==0)begin
 if(row[1:0]!=0||row[43])plan_bad=1;
 target[43]=1;target[38]=H[1];target[37:34]=H[78:75];target[33:2]=H[74:43];Hn[8:5]=Q[1][58:55];
 end else begin
 if(row[1:0]!=1||row[43]||row[38]!=(n==2)||row[33:2]!=key[35:4]||row[37:34]!=key[3:0])plan_bad=1;
 target[1:0]=(n==1)?2:3;
 end
 prepare(n,a,target);Cn[3*n+:3]=4;
 end end
 end
 // Prepared journal holds the sealed target/address/version for FOUR edges.
 for(j=0;j<9;j=j+1)if(J[j][86]&&J[j][81:72]<96)begin
 a=integer'(J[j][81:72]);target=44'(decode_data(J[j][71:0]));
 if(C[9+2*j+:2]==3)begin
 D[local_index(a)]=target;WE[local_index(a)]=1;Jn[j]=0;Cn[9+2*j+:2]=0;
 if(j==0&&phase[0]==4)begin
 if(target[43])Cn[2:0]=5;
 else begin Hn[0]=0;Qn[0]=0;Qn[1]=0;Cn[2:0]=0;end
 end
 if(j==2)begin WQn[0]=0;Qn[4]=0;Qn[5]=0;Cn[8:6]=0;end
 end else Cn[9+2*j+:2]=C[9+2*j+:2]+1'b1;
 end
 // Read delivery is reserved before asserting valid. The journal-commit edge
 // may publish from its qualified target, without an extra unpriced bubble.
 if(phase[1]==4&&RQ[0]&&!RD[0]&&RQ[4:2]<6)begin
 c=integer'(RQ[4:2]);a=16*c+integer'(Q[3][58:55]);
 if((!J[1][86]&&P[a][1:0]==2||J[1][86]&&C[11+:2]==3)&&completion_open[c])begin
 RDn=0;RDn[0]=1;RDn[3:1]=3'(c);RDn[7:4]=Q[3][58:55];RDn[39:8]=RQ[36:5];RDn[43:40]=RQ[40:37];RDn[299:44]=RQ[296:41];
 RQn[0]=0;Qn[2]=0;Qn[3]=0;Cn[5:3]=0;
 end end
 for(c=0;c<6;c=c+1)if(!S[c][0]&&completion_open[c])begin
 found=0;for(k=15;k>=0;k=k-1)if(P[16*c+k][1:0]==3&&!P[16*c+k][43])begin found=1;slot=k;end
 if(found)begin Sn[c]={4'(slot),1'b1};end
 end
 if(candidate_intents!=0)begin
 if(H[4:2]<6&&candidate_intents[3*integer'(H[4:2])])begin
 a=16*integer'(H[4:2])+integer'(H[8:5]);target=P[a];target[1:0]=1;target[43]=0;
 prepare(0,a,target);Hn[0]=0;Qn[0]=0;Qn[1]=0;Cn[2:0]=0;rrn=(H[4:2]==5)?0:H[4:2]+1'b1;
 end
 if(RD[3:1]<6&&candidate_intents[3*integer'(RD[3:1])+1])begin
 a=16*integer'(RD[3:1])+integer'(RD[7:4]);target=P[a];target[1:0]=0;target[42:39]=target[42:39]+1'b1;
 prepare(1,a,target);RDn[0]=0;
 end
 for(c=0;c<6;c=c+1)if(candidate_intents[3*c+2])begin
 a=16*c+integer'(S[c][4:1]);target=P[a];target[1:0]=0;target[42:39]=target[42:39]+1'b1;
 prepare(3+c,a,target);Sn[c][0]=0;
 end end
 // Stop cancels only the unaccepted source reservation, never an issued row.
 if(admission_stop&&H[0]&&H[4:2]<6)begin
 c=integer'(H[4:2]);
 if(phase[0]>0&&phase[0]<4)begin Hn[0]=0;Qn[0]=0;Qn[1]=0;Cn[2:0]=0;end
 else if(phase[0]==5||phase[0]==4&&!J[0][86])begin
 a=16*c+integer'(H[8:5]);target=P[a];target[43]=0;target[42:39]=target[42:39]+1'b1;
 prepare(0,a,target);Cn[2:0]=4;
 end end
 if(Hn!=H)put_record(96,8,Hn);
 if(RQn!=RQ)put_record(104,7,RQn);
 if(WQn!=WQ)put_record(111,1,352'(WQn));
 if(RDn!=RD)put_record(112,7,RDn);
 if(rrn!=rr)put_record(131,1,352'(rrn));
 for(i=0;i<6;i=i+1)begin
 if(Sn[i]!=S[i])put_record(119+i,1,352'(Sn[i]));
 if(Qn[i]!=Q[i])put_record(133+2*i,2,352'(Qn[i]));
 end
 for(i=0;i<9;i=i+1)if(Jn[i]!=J[i])put_record(169+2*i,2,352'(Jn[i]));
 if(Cn!=C)put_record(187,2,352'(Cn));
 end
 // No late semantic error or quarantined edge may modify primary debt.
 if(!permit||core_bad||!OPT_EXACT||!rst_n)begin
 WE=0;p_req_v=0;c_req_rdy=0;p_rsp_rdy=0;p_wr_done_ready=0;c_rsp_v=0;c_wr_done_v=0;
 end
 // Actual correction commit and context writeback, after eligibility.
 if(OPT_EXACT&&rst_n&&!any_core_bad&&!correction_error)begin
 for(eng=0;eng<8;eng=eng+1)if(repair_scrub_v[eng]&&repair_retire_ready[eng])begin
 a=integer'(repair_index[10*eng+:10]);
 if(a<219&&local_index(a)>=0)begin D[local_index(a)]=P[a];WE[local_index(a)]=1;end
 end
 for(eng=0;eng<8;eng=eng+1)if(repair_context_we[eng])put_record(145+3*eng,3,352'(context_next[96*eng+:96]));
 end
 if(correction_error)plan_bad=1;
 if(plan_bad||core_bad)WE=0;
 end
 always_ff @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin for(integer x=0;x<NW;x=x+1)cw[x]<=seal(0,global_index(x));end
 else if(OPT_EXACT)begin for(integer x=0;x<NW;x=x+1)if(WE[x])cw[x]<=encoded[x];end
 end
endmodule
'''
    maps='\n'.join(f'{l}:global_index={g};' for l,g in enumerate(PRIMARY))
    inverse='\n'.join(f'{g}:local_index={l};' for l,g in enumerate(PRIMARY))
    pb='\n'.join(f"{x['index']}:payload_bits={x['payload_bits']};" for x in m.ROWS)
    kinds='\n'.join(f"{x['index']}:kind={x['kind']};" for x in m.ROWS)
    sec=[]
    for l,g in enumerate(s.mapping()):
        sec.append(f'assign raw[{g}]=secondary_raw[{72*l}+:72];assign fixed_word[{g}]=secondary_fixed[{72*l}+:72];assign P[{g}]=secondary_payload[{44*l}+:44];assign clean[{g}]=secondary_clean[{l}];assign ce[{g}]=secondary_ce[{l}];assign invalid[{g}]=secondary_bad[{l}];')
    return text.replace('@@PORTS@@',ports).replace('@@GMAP@@',maps).replace('@@LMAP@@',inverse).replace('@@PB@@',pb).replace('@@KIND@@',kinds).replace('@@SECONDARY_ASSIGN@@','\n'.join(sec))

if __name__=='__main__':
    # Record prospective resources/edges before writing the actual source.
    (RTL.parent/'enrollment_model.json').write_text(json.dumps(enrollment_model(),sort_keys=True,indent=2)+'\n')
    RTL.write_text(source())
