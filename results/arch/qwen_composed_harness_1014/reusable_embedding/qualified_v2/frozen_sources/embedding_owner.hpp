#pragma once
// Genuine reusable NW18/LV6/G1 embedding core. Only checkpoint code/scale ROM
// bytes are inputs. Accepted actual write faces fan out into the mutable VMs.
#include "Vot_qwen_tp8_embedding_core.h"
#include "Vot_qwen_tp8_embedding_core___024root.h"
#include "rom_vm_adapter.hpp"
#include "kernel_physical_rows.hpp"
#include <bitset>
class EmbeddingOwner {
 Vot_qwen_tp8_embedding_core rtl;
 std::vector<qwen_native::HexWord<32>> program;
 std::vector<qwen_native::HexWord<16>> codes;
 qwen_native::HexWord<32> pq{},next_pq{},observed_next{};
 qwen_native::HexWord<16> eq{},next_eq{};
 qwen_native::HexWord<64> aq{},bq{},cq{},next_a{},next_b{},next_c{};
 qwen_native::HexWord<128> constants{};
 uint16_t scale=0,sq=0,next_sq=0;
 struct Write{unsigned address;uint32_t value;};std::vector<Write> posted;
 bool running=false,observer_valid=false,sampled=false;
 bool loaded=false;qwen_native::HexWord<32> loaded_word{};
 std::bitset<4096> committed_x;std::bitset<64> requested_words;
 uint64_t accepted_tag=0;unsigned accepted_generation=0,accepted_token=0,accepted_position=0;
 uint64_t edges=0,begin_edge=0;unsigned issues=0,ends=0,requests=0,reductions=0;
public:
 struct RawEvent{unsigned pc;uint64_t edge;qwen_native::HexWord<32>bits;};
 struct CommitEvent{unsigned address;uint32_t value;uint64_t edge,tag;unsigned generation;};
 std::vector<RawEvent> raw_events;std::vector<CommitEvent> commits;
 EmbeddingOwner(VerilatedContext&ctx,const std::string&path):rtl(&ctx,"actual_stage0_embedding"),program(qwen_native::read_hex<32>(path)){
  if(program.size()!=2||(program[0][0]&3)!=2||(program[1][0]&3)!=0)throw std::runtime_error("actual embedding program must be SU plus END");
  rtl.clk=0;rtl.rst_n=0;rtl.start=0;rtl.native_contract_ready=0;rtl.native_ready=0;rtl.native_idle=1;rtl.native_fault=0;rtl.native_progress=0;
  rtl.su_descriptor_reserved=1;rtl.kv_write_drained=rtl.kv_ok=rtl.w_ok=rtl.emb_ok=rtl.me_mem_ok=1;rtl.eval();
 }
 void begin_after_actual_dispatch(const std::string&bank,uint64_t actual_tag,unsigned actual_generation,unsigned token,unsigned position){
  if(running||!rtl.rst_n||token>=151936||position>=8192||(actual_tag&((uint64_t(63)<<37)|63))||
     ((actual_tag>>19)&0x3ffff)!=token||((actual_tag>>6)&8191)!=position||actual_tag>>59||actual_generation>3)
   throw std::runtime_error("embedding start identity/state differs from actual stage0 held cohort");
  codes=qwen_native::read_hex<16>(bank+"/token"+std::to_string(token)+"/codes.hex");auto scales=qwen_native::read_hex<1>(bank+"/token"+std::to_string(token)+"/scale.hex");
  if(codes.size()!=64||scales.size()!=1||scales[0][0]>65535)throw std::runtime_error("actual embedding ROM bank shape");scale=scales[0][0];
  accepted_tag=actual_tag;accepted_generation=actual_generation;accepted_token=token;accepted_position=position;
  committed_x.reset();requested_words.reset();issues=ends=requests=reductions=0;raw_events.clear();commits.clear();observer_valid=false;
  rtl.token=token;rtl.pos=position;rtl.start=1;running=true;begin_edge=edges;
 }
 template<class Ranks>void low(Ranks&r,bool reset){
  if(running&&!reset)throw std::runtime_error("actual embedding reset during live token");
  rtl.clk=0;rtl.rst_n=reset;
  qwen_native::drive(rtl.prog_q,pq);qwen_native::drive(rtl.embed_code_q,eq);rtl.embed_scale_q=sq;
  qwen_native::drive(rtl.va_q,aq);qwen_native::drive(rtl.vb_q,bq);qwen_native::drive(rtl.vc_q,cq);qwen_native::drive(rtl.crom_q,constants);rtl.eval();
  next_pq=pq;next_eq=eq;next_sq=sq;next_a=aq;next_b=bq;next_c=cq;posted.clear();
  if(rtl.prog_re)next_pq=rtl.prog_addr<program.size()?program[rtl.prog_addr]:qwen_native::HexWord<32>{};
  if(rtl.embed_scale_re){if(!running||rtl.embed_scale_addr!=accepted_token)throw std::runtime_error("actual NW18 embedding scale address truncation/unowned request");next_sq=scale;}
  if(rtl.embed_code_re){unsigned base=accepted_token*64;if(!running||rtl.embed_code_addr<base||rtl.embed_code_addr>=base+64)throw std::runtime_error("actual NW18 embedding code address truncation/unowned request");unsigned index=rtl.embed_code_addr-base;if(requested_words[index])throw std::runtime_error("duplicate actual embedding code word request");requested_words.set(index);next_eq=codes[index];++requests;}
  for(unsigned lane=0;lane<64;lane++){
   uint64_t mask=uint64_t(1)<<lane;
   if(rtl.va_re&mask)next_a[lane]=r[0]->vm.load(qwen_native_services::get_bits(rtl.va_addr,24*lane,24));
   if(rtl.vb_re&mask)next_b[lane]=r[0]->vm.load(qwen_native_services::get_bits(rtl.vb_addr,24*lane,24));
   if(rtl.vc_re&mask)next_c[lane]=r[0]->vm.load(qwen_native_services::get_bits(rtl.vc_addr,24*lane,24));
   if(rtl.vw_su_we&mask){unsigned a=qwen_native_services::get_bits(rtl.vw_su_addr,24*lane,24);if(!running||a<4096||a>=8192||committed_x[a-4096])throw std::runtime_error("actual embedding destination/duplicate");committed_x.set(a-4096);posted.push_back({a,rtl.vw_su_data[lane]});}
  }
  if(rtl.vw_rd_we){if(!running||rtl.vw_rd_addr!=14240||reductions++)throw std::runtime_error("actual embedding SSX destination/count");posted.push_back({unsigned(rtl.vw_rd_addr),rtl.vw_rd_data});}
  if(rtl.instruction_issue||rtl.end_retired){unsigned pc=rtl.end_retired?rtl.end_pc:rtl.instruction_pc;
   if(!running||pc>=2||!observer_valid||observed_next!=program[pc]||(rtl.instruction_issue&&(pc!=0||rtl.instruction_unit!=2))||(rtl.end_retired&&pc!=1))throw std::runtime_error("actual embedding accepted FIFO/source ownership differs");
   raw_events.push_back({pc,edges,observed_next});if(rtl.end_retired)++ends;else ++issues;
   if(rtl.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__tok_r!=accepted_token||rtl.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__pos_r!=accepted_position)throw std::runtime_error("actual embedding latched token/position differs from held cohort");
  }
  loaded=rtl.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__load;
  if(loaded){auto&word=rtl.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__fq[rtl.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__fq_rd];for(unsigned j=0;j<32;j++)loaded_word[j]=word[j];}
  if(rtl.vw_me_we||rtl.vw_mx_we||rtl.kv_we)throw std::runtime_error("embedding requested unprovided operator");sampled=true;
 }
 template<class Ranks>void rise(Ranks&r){
  if(!sampled)throw std::runtime_error("embedding rise without frozen read/write faces");rtl.clk=1;rtl.eval();
  for(auto&w:posted){for(auto&rank:r)rank->vm.external_commit(w.address,w.value,"ACTUAL_STAGE0_EMBEDDING");commits.push_back({w.address,w.value,edges,accepted_tag,accepted_generation});}
  pq=next_pq;eq=next_eq;sq=next_sq;aq=next_a;bq=next_b;cq=next_c;if(loaded){observed_next=loaded_word;observer_valid=true;}
  rtl.start=0;sampled=false;++edges;if(rtl.fault)throw std::runtime_error("actual reusable NW18 embedding fault");
 }
 void fall(){rtl.clk=0;rtl.eval();}
 bool done(){if(!running||!rtl.done||rtl.start||edges==begin_edge)return false;if(!committed_x.all()||reductions!=1||issues!=1||ends!=1||requests!=64||!requested_words.all()||commits.size()!=4097||raw_events.size()!=2)throw std::runtime_error("actual embedding incomplete effects");return true;}
 void retire(){if(!done())throw std::runtime_error("embedding retire before actual complete");running=false;}
 bool idle()const{return !running;}
 uint64_t cycles()const{return edges-begin_edge;}
};
