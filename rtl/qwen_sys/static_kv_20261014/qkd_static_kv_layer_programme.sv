`timescale 1ns/1ps
// Actual all36-layer control-root producer. Tables hold compiler times, never
// payload/results. All events advance on fixed cycles, without ready/credit
// inputs. The actual authorized HOST programme identity and authoritative token
// context are captured once at start. A mismatch faults; no delayed fallback.
//
// Boot 9 words/layer, stages1..36 in order (addresses0..323): ctrl_go,kgo,vgo,
// attention_issue,attention_run,writer_start,link_start,expected_quiet,stage_end.
// Each root is low32 of data64; upper32 must be0. All roots>=3 and<stage_end;
// attention_run>=attention_issue+4. Address324 binds authorized programme digest64,
//325 binds programme epoch16 (upper48=0),326 seals 514b564c59523336 (QKVLYR36).
// Roots are OUTPUT pin edges from each stage's internal start; external start
// capture precedes internal accepted start by1 edge. Stage tables are fetched
// on the first stage edge, before any allowed root. Metadata is already stable.
// expected_upstream_quiet is a compiled expectation, NOT actual drain evidence.
//
// Real boot/source/phase/relay/metadata paths and native programme coverage are
// mandatory. This leaf neither manufactures a native-attention calendar176 nor
// bypasses actual controller/landing/front images or HOST queues.
module qkd_static_kv_layer_programme #(parameter integer MUT=0)(
 input wire ck,rst_n,
 input wire cfg_we,input wire[8:0]cfg_addr,input wire[63:0]cfg_data,
 input wire start,authority_valid,programme_authorized,
 input wire[15:0]programme_epoch,input wire[63:0]programme_digest,
 input wire[15:0]authority_epoch,input wire[17:0]authority_token,authority_position,
 input wire[1:0]authority_generation,
 output reg ctrl_go,kgo,vgo,attention_issue,attention_run,writer_start,link_start,
 output reg stage_start,stage_done,expected_upstream_quiet,output reg[5:0]completed_stage,
 output wire[5:0]stage,output wire[5:0]layer,
 output reg[15:0]epoch,output reg[17:0]token,position,output reg[13:0]ctx_t,
 output reg[1:0]generation,
 output reg configured,active,done,fault,output reg[7:0]fault_code,
 output reg[31:0]age,token_cycles
);
 (* keep *)reg rn;always @(posedge ck)rn<=rst_n;
 reg we_q,start_q,av_q,authorized_q;reg[8:0]addr_q;reg[63:0]data_q,pdigest_q;
 reg[15:0]pepoch_q,epoch_q;reg[17:0]token_q,pos_q;reg[1:0]gen_q;
 always @(posedge ck)begin
  addr_q<=cfg_addr;data_q<=cfg_data;pdigest_q<=programme_digest;pepoch_q<=programme_epoch;
  epoch_q<=authority_epoch;token_q<=authority_token;pos_q<=authority_position;gen_q<=authority_generation;
 end
 always @(posedge ck or negedge rn)
 if(!rn)begin we_q<=0;start_q<=0;av_q<=0;authorized_q<=0;end
 else begin we_q<=cfg_we;start_q<=start;av_q<=authority_valid;authorized_q<=programme_authorized;end
 reg[8:0]next_cfg;reg[5:0]cfg_stage,stage_q,index_q;reg[3:0]cfg_word;
 reg[63:0]bound_digest;reg[15:0]bound_epoch;reg[36:0]duration_sum;
 reg[31:0]shadow[0:7];
 reg[31:0]t_ctrl[0:35],t_k[0:35],t_v[0:35],t_issue[0:35],t_run[0:35];
 reg[31:0]t_writer[0:35],t_link[0:35],t_quiet[0:35],t_end[0:35];
 reg wq;reg[35:0]wq_stage;reg[8:0]wq_word;reg[31:0]wq_data;
 reg[31:0]r_ctrl,r_k,r_v,r_issue,r_run,r_writer,r_link,r_quiet,r_end;
 reg load_row;
 wire accept_cfg=we_q&&!configured&&!active&&!fault&&addr_q==next_cfg;
 reg bad_row;
 always @*begin
  bad_row=data_q[63:32]!=0;
  for(integer k=0;k<8;k=k+1)if(shadow[k]<3||shadow[k]>=data_q[31:0])bad_row=1;
  for(integer k=0;k<7;k=k+1)if(shadow[7]<=shadow[k])bad_row=1;
  if({1'b0,shadow[4]} < {1'b0,shadow[3]}+33'd4)bad_row=1;
  if(duration_sum+{5'b0,data_q[31:0]}>37'h0ffffffff)bad_row=1;
 end
 assign stage=(MUT==2)?(stage_q^6'd1):stage_q;
 assign layer=stage-6'd1;
 // Unreset table data flops are written in full before seal. One-hot boot
 // capture separates address decode from the 10,368 table enables/data sinks.
 always @(posedge ck or negedge rn)if(!rn)wq<=0;else wq<=accept_cfg&&addr_q<324;
 always @(posedge ck)begin
  wq_stage<=36'd1<<cfg_stage;wq_word<=9'd1<<cfg_word;wq_data<=data_q[31:0];
 end
 genvar g;
 generate for(g=0;g<36;g=g+1)begin:rows
  always @(posedge ck)if(wq&&wq_stage[g])begin
   if(wq_word[0])t_ctrl[g]<=wq_data;if(wq_word[1])t_k[g]<=wq_data;
   if(wq_word[2])t_v[g]<=wq_data;if(wq_word[3])t_issue[g]<=wq_data;
   if(wq_word[4])t_run[g]<=wq_data;if(wq_word[5])t_writer[g]<=wq_data;
   if(wq_word[6])t_link[g]<=wq_data;if(wq_word[7])t_quiet[g]<=wq_data;
   if(wq_word[8])t_end[g]<=wq_data;
  end
 end endgenerate
 always @(posedge ck)if(load_row)begin
  r_ctrl<=t_ctrl[index_q];r_k<=t_k[index_q];r_v<=t_v[index_q];r_issue<=t_issue[index_q];r_run<=t_run[index_q];
  r_writer<=t_writer[index_q];r_link<=t_link[index_q];r_quiet<=t_quiet[index_q];r_end<=t_end[index_q];
 end
 always @(posedge ck or negedge rn)begin
  if(!rn)begin
   ctrl_go<=0;kgo<=0;vgo<=0;attention_issue<=0;attention_run<=0;writer_start<=0;link_start<=0;
   stage_start<=0;stage_done<=0;expected_upstream_quiet<=0;completed_stage<=0;
   epoch<=0;token<=0;position<=0;ctx_t<=0;generation<=0;
   configured<=0;active<=0;done<=0;fault<=0;fault_code<=0;age<=0;token_cycles<=0;
   next_cfg<=0;cfg_stage<=0;cfg_word<=0;stage_q<=0;index_q<=0;load_row<=0;
   bound_digest<=0;bound_epoch<=0;duration_sum<=0;
  end else begin
   ctrl_go<=0;kgo<=0;vgo<=0;attention_issue<=0;attention_run<=0;writer_start<=0;link_start<=0;
   stage_start<=0;stage_done<=0;done<=0;load_row<=0;
   if(fault)active<=0;
   else begin
    if(we_q)begin
     if(!accept_cfg)begin fault<=1;fault_code[0]<=1;end
     else if(addr_q<324)begin
      if(data_q[63:32]!=0||(cfg_word==8&&bad_row))begin fault<=1;fault_code[1]<=1;end
      if(cfg_word<8)shadow[cfg_word[2:0]]<=data_q[31:0];
      else duration_sum<=duration_sum+{5'b0,data_q[31:0]};
      if(cfg_word==8)begin cfg_stage<=cfg_stage+1'b1;cfg_word<=0;end else cfg_word<=cfg_word+1'b1;
      next_cfg<=next_cfg+1'b1;
     end else if(addr_q==324)begin bound_digest<=data_q;next_cfg<=325;end
     else if(addr_q==325)begin
      if(data_q[63:16]!=0)begin fault<=1;fault_code[2]<=1;end
      bound_epoch<=data_q[15:0];next_cfg<=326;
     end else if(addr_q==326)begin
      if(data_q!=64'h514b564c59523336||cfg_stage!=36||duration_sum==0)begin fault<=1;fault_code[2]<=1;end
      else configured<=1;
     end else begin fault<=1;fault_code[0]<=1;end
    end
    if(start_q)begin
     if(!configured||active||we_q||!av_q||!authorized_q||pos_q>8191||pepoch_q!=bound_epoch||pdigest_q!=bound_digest)begin fault<=1;fault_code[3]<=1;end
     else begin
      epoch<=epoch_q;token<=token_q;position<=pos_q;ctx_t<=14'(pos_q+1);generation<=gen_q;
      stage_q<=1;index_q<=0;load_row<=1;active<=1;age<=0;token_cycles<=0;stage_start<=1;expected_upstream_quiet<=0;
     end
    end
    if(active)begin
     age<=age+1'b1;token_cycles<=token_cycles+1'b1;
     if(!load_row)begin
      ctrl_go<=age==r_ctrl-1;kgo<=age==r_k-1;vgo<=age==r_v-1;
      attention_issue<=age==r_issue-1;attention_run<=age==r_run-1;
      writer_start<=age==r_writer-((MUT==1)?32'd2:32'd1);link_start<=age==r_link-1;
      if(age==r_quiet-1)expected_upstream_quiet<=1;
      if(age==r_end-1)begin
       stage_done<=1;completed_stage<=stage_q;
       if(stage_q==36)begin active<=0;done<=1;end
       else begin stage_q<=stage_q+1'b1;index_q<=index_q+1'b1;load_row<=1;age<=0;stage_start<=1;expected_upstream_quiet<=0;end
      end
     end
     if(MUT==3)ctx_t<=14'(authority_position+1);
    end
   end
  end
 end
endmodule
