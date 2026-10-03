`timescale 1ps/1ps
// Default-off PRIVATE NC6 secondary controller. Owns exactly37/219 coded words.
// Table states/status come from the SAME CURRENT outer sealed-codec instances.
// No native caller/R14/backend, fullNC6, or loadedSSFF qualification implied.
module ot_w2_nc6_coded_secondary_reset_quarantine #(
 parameter integer OPT_PROTECTION=0, OPT_RESET_QUARANTINE=0,
 parameter logic [6:0] PC_ID=7'd0
)(
 input wire clk,rst_n,admission_stop,
 input wire [191:0] table_state,
 input wire [95:0] table_clean,table_bad,
 input wire [5:0] table_pending,offer_copies_drained,
 input wire other_clean,other_bad,logic_fault,
 input wire [17:0] reserve_roles,accept_intent,
 input wire [5:0] cancel_request,reopen_epoch,
 output logic [17:0] commit_roles,
 output logic [5:0] request_bank_open,completion_bank_open,
 output logic normal_permit,repair_busy,fault,
 input wire rearm_v,provider_fenced,reverse_fenced,reset_fenced,local_other_idle,
 output logic rearm_ready,local_idle,
 input wire [1:0] scrub_v,
 input wire [19:0] scrub_index,
 input wire [143:0] scrub_original,scrub_repaired,
 output logic [1:0] scrub_ready,
 // Private CURRENT inspection, combinational wires, not another state copy.
 output wire [2663:0] inspect_original,inspect_corrected,
 output wire [1627:0] inspect_payload,
 output wire [36:0] inspect_clean,inspect_ce,inspect_bad
);
 localparam integer NW=37;
 // Full72-bit words including static seal/padding must survive physical mapping.
 // Netlist census is required; keep attributes are not a physical proof.
 (* keep = "true" *) logic [71:0] cw[0:NW-1];
 wire [43:0] payload[0:NW-1];
 wire [71:0] encoded[0:NW-1],corrected[0:NW-1];
 wire [NW-1:0] clean,ce,badword;
 logic [43:0] next_payload[0:NW-1];
 logic [NW-1:0] write_enable;
 logic semantic_bad,local_all_clean,integrity_bad;
 integer client,wordno,slot,lane,index,a,d,newn,version,delta,phase;
 integer census[0:5];
 integer local_scrub[0:1];
 logic [131:0] worker[0:5],next_worker[0:5];
 logic [7:0] epoch[0:5];
 logic [4:0] pending[0:5];
 logic [8:0] cache[0:5];
 logic [2:0] roles,reserves,taken;
 logic [71:0] target;
 logic [63:0] target_data;

 function automatic integer global_index(input integer i);
  begin global_index=0;
  case(i)
   0: global_index=125;
   1: global_index=126;
   2: global_index=127;
   3: global_index=128;
   4: global_index=129;
   5: global_index=130;
   6: global_index=189;
   7: global_index=190;
   8: global_index=191;
   9: global_index=192;
   10: global_index=193;
   11: global_index=194;
   12: global_index=195;
   13: global_index=196;
   14: global_index=197;
   15: global_index=198;
   16: global_index=199;
   17: global_index=200;
   18: global_index=201;
   19: global_index=202;
   20: global_index=203;
   21: global_index=204;
   22: global_index=205;
   23: global_index=206;
   24: global_index=207;
   25: global_index=208;
   26: global_index=209;
   27: global_index=210;
   28: global_index=211;
   29: global_index=212;
   30: global_index=213;
   31: global_index=214;
   32: global_index=215;
   33: global_index=216;
   34: global_index=217;
   35: global_index=218;
   36: global_index=132;
   default:global_index=0;
  endcase
  end
 endfunction
 function automatic integer kind_of(input integer i);
  begin
   if(i<6||i>=24)kind_of=4;else kind_of=7;
  end
 endfunction
 function automatic integer bits_of(input integer i);
  begin
   if(i<6)bits_of=9;
   else if(i<24)bits_of=((i-6)%3==2)?10:44;
   else if(i<30)bits_of=5;
   else if(i<36)bits_of=8;
   else bits_of=1;
  end
 endfunction
 function automatic [71:0] encode_payload(input [43:0] p,input [9:0] wi,input [2:0] kind);
  reg [63:0] data64;reg [71:0] code;
  integer pos,j,k;reg par;
  begin
   data64={3'(kind),10'(wi),PC_ID,p};code='0;j=0;
   for(pos=1;pos<=71;pos=pos+1)if((pos&(pos-1))!=0)begin code[pos-1]=data64[j];j=j+1;end
   for(k=0;k<7;k=k+1)begin
    par=0;for(pos=1;pos<=71;pos=pos+1)if((pos&(1<<k))!=0)par=par^code[pos-1];
    code[(1<<k)-1]=par;
   end
   code[71]=^code[70:0];encode_payload=code;
  end
 endfunction
 function automatic [63:0] data_from_word(input [71:0] code);
  integer pos,j;reg [63:0] value;
  begin value=0;j=0;
   for(pos=1;pos<=71;pos=pos+1)if((pos&(pos-1))!=0)begin value[j]=code[pos-1];j=j+1;end
   data_from_word=value;
  end
 endfunction
 function automatic integer s3(input [2:0] v);
  s3=v[2]?(integer'(v)-8):integer'(v);
 endfunction
 function automatic integer ones6(input [5:0] v);
  integer q;begin ones6=0;for(q=0;q<6;q=q+1)ones6=ones6+integer'(v[q]);end
 endfunction
 generate for(genvar w=0;w<NW;w=w+1)begin:word_codec
  localparam integer PB=bits_of(w);
  wire uncorrectable,seal_ok,padding_ok;
  wire [43:0] bounded_next_payload={{(44-PB){1'b0}},next_payload[w][PB-1:0]};
  ot_w2_sealed_secded72 #(.PC_ID(PC_ID),.WORD_INDEX(10'(global_index(w))),
    .WORD_KIND(3'(kind_of(w))),.PAYLOAD_BITS(bits_of(w))) codec(
    .payload(44'b0),.current_word(cw[w]),.encoded_word(),
    .syndrome(),.overall_odd(),.clean(),.correctable(ce[w]),.uncorrectable(uncorrectable),
    .seal_ok(seal_ok),.padding_ok(padding_ok),.release_clean(clean[w]),
    .repaired_payload(payload[w]),.repaired_word(corrected[w]));
  // Separate frozen codec instances avoid a false scheduling SCC caused by
  // the leaf's bundled always_comb. Unused encoder/decoder cones must map out.
  ot_w2_sealed_secded72 #(.PC_ID(PC_ID),.WORD_INDEX(10'(global_index(w))),
    .WORD_KIND(3'(kind_of(w))),.PAYLOAD_BITS(PB)) encoder(
    .payload(bounded_next_payload),.current_word(72'b0),.encoded_word(encoded[w]),
    .syndrome(),.overall_odd(),.clean(),.correctable(),.uncorrectable(),
    .seal_ok(),.padding_ok(),.release_clean(),.repaired_payload(),.repaired_word());
  assign badword[w]=uncorrectable||!seal_ok||!padding_ok;
  assign inspect_original[72*w+:72]=cw[w];
  assign inspect_corrected[72*w+:72]=corrected[w];
  assign inspect_payload[44*w+:44]=payload[w];
 end endgenerate
 assign inspect_clean=clean;
 assign inspect_ce=ce;
 assign inspect_bad=badword;

 integer view_client,view_slot,bank_client;
 always_comb begin
  local_all_clean=&clean;integrity_bad=(|badword)||(|table_bad)||other_bad;local_idle=1;
  for(view_client=0;view_client<6;view_client=view_client+1)begin
  cache[view_client]=payload[view_client][8:0];pending[view_client]=payload[24+view_client][4:0];epoch[view_client]=payload[30+view_client][7:0];
  worker[view_client]={payload[6+3*view_client+2],payload[6+3*view_client+1],payload[6+3*view_client]};census[view_client]=0;
  for(view_slot=0;view_slot<16;view_slot=view_slot+1)if(table_state[2*(16*view_client+view_slot)+:2]!=0)census[view_client]=census[view_client]+1;
  if(cache[view_client][4:0]!=0||pending[view_client][3]||worker[view_client][92]||epoch[view_client][7]||table_pending[view_client])local_idle=0;
  end end
  // Bank eligibility is CURRENT pre-qualification, never the final semantic permit.
  // Actual state writes and public handshakes still require final normal_permit.
  always_comb begin
  request_bank_open=0;completion_bank_open=0;
  for(bank_client=0;bank_client<6;bank_client=bank_client+1)
  if(OPT_PROTECTION!=0&&rst_n&&!integrity_bad&&!payload[36][0]&&!logic_fault&&local_all_clean&&(&table_clean)&&other_clean&&
  !table_pending[bank_client]&&!worker[bank_client][92]&&!pending[bank_client][3]&&!epoch[bank_client][6])begin
  completion_bank_open[bank_client]=1;
  if(cache[bank_client][4:0]<16&&integer'(cache[bank_client][4:0])==census[bank_client]&&!admission_stop)request_bank_open[bank_client]=1;
  end end
  always_comb begin
  write_enable='0;semantic_bad=0;
  commit_roles='0;scrub_ready='0;
  normal_permit=0;repair_busy=0;fault=0;rearm_ready=0;
  client=0;wordno=0;slot=0;lane=0;index=0;a=0;d=0;newn=0;version=0;delta=0;phase=0;
  roles=0;reserves=0;taken=0;target=0;target_data=0;
  local_scrub[0]=-1;local_scrub[1]=-1;
  for(wordno=0;wordno<NW;wordno=wordno+1)next_payload[wordno]=payload[wordno];
  for(client=0;client<6;client=client+1)begin
   next_worker[client]=worker[client];
   if(cache[client][4:0]>16||pending[client][4])semantic_bad=1;
   if(!pending[client][3]&&pending[client][2:0]!=0)semantic_bad=1;
   if(pending[client][3]&&(s3(pending[client][2:0]) < -2||s3(pending[client][2:0])>1))semantic_bad=1;
   if((epoch[client][5:3]&~epoch[client][2:0])!=0)semantic_bad=1;
   if(!worker[client][92]&&!pending[client][3]&&!table_pending[client]&&integer'(cache[client][4:0])!=census[client])semantic_bad=1;
  end
  // Explicit intent BEFORE permit, avoiding permit -> take -> bad -> permit loop.
  if(ones6({accept_intent[15],accept_intent[12],accept_intent[9],accept_intent[6],accept_intent[3],accept_intent[0]})>1)semantic_bad=1;
  if(ones6({accept_intent[16],accept_intent[13],accept_intent[10],accept_intent[7],accept_intent[4],accept_intent[1]})>1)semantic_bad=1;
  if(OPT_PROTECTION!=0&&rst_n)begin
   fault=integrity_bad||payload[36][0]||logic_fault;
   repair_busy=!local_all_clean||!(&table_clean)||!other_clean;
   normal_permit=!fault&&!repair_busy;
   rearm_ready=admission_stop&&provider_fenced&&reverse_fenced&&reset_fenced&&local_other_idle&&local_idle&&local_all_clean&&(&table_clean)&&other_clean&&!integrity_bad;
   if(rearm_v&&!rearm_ready)semantic_bad=1;
   for(client=0;client<6;client=client+1)begin
    roles=accept_intent[3*client+:3];reserves=reserve_roles[3*client+:3];taken=epoch[client][5:3];
    if((roles&~epoch[client][2:0])!=0||(roles&taken)!=0)semantic_bad=1;
    if(reserves!=0)begin
     if(epoch[client][6]||(reserves&epoch[client][2:0])!=0||!completion_bank_open[client])semantic_bad=1;
     if(reserves[0]&&!request_bank_open[client])semantic_bad=1;
     if(reserves[2:1]!=0&&census[client]==0)semantic_bad=1;
    end
    if(cancel_request[client]&&(!admission_stop||!epoch[client][0]||epoch[client][3]||roles[0]))semantic_bad=1;
    if(reopen_epoch[client]&&(epoch[client][2:0]!=epoch[client][5:3]||table_pending[client]||!offer_copies_drained[client]||worker[client][92]||pending[client][3]))semantic_bad=1;
    delta=s3(pending[client][2:0])+integer'(roles[0])-integer'(roles[1])-integer'(roles[2]);
    if(roles!=0&&(delta < -2||delta>1))semantic_bad=1;
    if(worker[client][92])begin
     target=worker[client][71:0];target_data=data_from_word(target);
     phase=integer'(worker[client][91:89]);version=integer'(worker[client][85:82]);d=s3(worker[client][88:86]);
     if(phase>3||worker[client][81:72]!=10'(global_index(client))||version!=integer'(cache[client][8:5])||d < -2||d>1)semantic_bad=1;
     // Stored target is itself a SECDED word, not unprotected72-bit metadata.
     if(target!=encode_payload({35'b0,target_data[8:0]},10'(global_index(client)),3'd4)||target_data[43:9]!=0||
       target_data[4:0]!=worker[client][97:93]||target_data[4:0]>16||
       integer'(target_data[4:0])!=integer'(cache[client][4:0])+d||target_data[8:5]!=4'(version+1))semantic_bad=1;
    end
   end
   // Normal state updates only after complete semantic qualification of batch.
   if(normal_permit&&!semantic_bad&&!rearm_v)begin
    commit_roles=accept_intent;
    for(client=0;client<6;client=client+1)begin
     roles=accept_intent[3*client+:3];reserves=reserve_roles[3*client+:3];
     if(reserves!=0)begin
      next_payload[30+client][2:0]=epoch[client][2:0]|reserves;next_payload[30+client][7]=1;write_enable[30+client]=1;
     end
     if(roles!=0)begin
      delta=s3(pending[client][2:0])+integer'(roles[0])-integer'(roles[1])-integer'(roles[2]);
      next_payload[24+client][4:0]={1'b0,1'b1,3'(delta)};write_enable[24+client]=1;
      next_payload[30+client][5:3]=epoch[client][5:3]|roles;
      next_payload[30+client][6]=1;write_enable[30+client]=1;
     end
     if(cancel_request[client])begin next_payload[30+client][0]=0;write_enable[30+client]=1;end
     if(reopen_epoch[client])begin next_payload[30+client]=0;write_enable[30+client]=1;end
     if(worker[client][92])begin
      phase=integer'(worker[client][91:89]);
      if(phase==3)begin
       target_data=data_from_word(worker[client][71:0]);next_payload[client]=target_data[43:0];write_enable[client]=1;
       next_worker[client]=0;
      end else next_worker[client][91:89]=3'(phase+1);
      for(a=0;a<3;a=a+1)begin next_payload[6+3*client+a]=next_worker[client][44*a+:44];write_enable[6+3*client+a]=1;end
     end else if(pending[client][3]&&!table_pending[client]&&roles==0)begin
      newn=integer'(cache[client][4:0])+s3(pending[client][2:0]);
      if(newn<0||newn>16||newn!=census[client])semantic_bad=1;
      else begin
       version=(integer'(cache[client][8:5])+1)&15;
       target=encode_payload({35'b0,4'(version),5'(newn)},10'(global_index(client)),3'd4);
       next_worker[client]=0;next_worker[client][71:0]=target;
       next_worker[client][81:72]=10'(global_index(client));next_worker[client][85:82]=cache[client][8:5];
       next_worker[client][88:86]=pending[client][2:0];next_worker[client][92]=1;
       next_worker[client][97:93]=5'(census[client]);
       for(a=0;a<3;a=a+1)begin next_payload[6+3*client+a]=next_worker[client][44*a+:44];write_enable[6+3*client+a]=1;end
       next_payload[24+client]=0;write_enable[24+client]=1;
      end
     end
    end
   end
   // Two utility scrub lanes own private local destinations. Context/header
   // and ORIGINAL current sample must match; foreign owners are not ACKed.
   for(lane=0;lane<2;lane=lane+1)begin
    index=integer'(scrub_index[10*lane+:10]);
    for(wordno=0;wordno<NW;wordno=wordno+1)if(index==global_index(wordno))local_scrub[lane]=wordno;
    if(scrub_v[lane]&&index>=219)semantic_bad=1;
    if(scrub_v[lane]&&local_scrub[lane]>=0)begin
     wordno=local_scrub[lane];
     if(!ce[wordno]||badword[wordno]||scrub_original[72*lane+:72]!=cw[wordno]||scrub_repaired[72*lane+:72]!=corrected[wordno])semantic_bad=1;
     else begin
      scrub_ready[lane]=1;next_payload[wordno]=payload[wordno];write_enable[wordno]=1;
      if(wordno<6||wordno>=6&&wordno<24)begin
       client=(wordno<6)?wordno:(wordno-6)/3;
       // Remaining worker words must be CURRENT clean; do not use multiple
       // independent corrections as an unpriced atomic-context repair.
       for(a=0;a<3;a=a+1)if(6+3*client+a!=wordno&&!clean[6+3*client+a])semantic_bad=1;
       next_worker[client]=worker[client];next_worker[client][91:89]=0;
       for(a=0;a<3;a=a+1)begin next_payload[6+3*client+a]=next_worker[client][44*a+:44];write_enable[6+3*client+a]=1;end
      end
     end
    end
   end
   if(scrub_v==2'b11&&local_scrub[0]>=0&&local_scrub[0]==local_scrub[1])semantic_bad=1;
   if(semantic_bad||integrity_bad||logic_fault)begin
    write_enable='0;next_payload[36]=44'd1;write_enable[36]=1;
    commit_roles=0;normal_permit=0;scrub_ready=0;fault=1;
   end else if(rearm_v&&rearm_ready)begin
    write_enable='0;next_payload[36]=0;write_enable[36]=1;
   end
  end
 end
 always_ff @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   for(integer w=0;w<NW;w=w+1)cw[w]<=encode_payload((OPT_RESET_QUARANTINE!=0&&global_index(w)==132)?44'd1:44'd0,10'(global_index(w)),3'(kind_of(w)));
  end else if(OPT_PROTECTION!=0)begin
   for(integer w=0;w<NW;w=w+1)if(write_enable[w])cw[w]<=encoded[w];
  end
 end
endmodule
