#pragma once
#include <cstring>
#include <algorithm>
#include <cstdlib>
// Candidate executed-layer harness. No fixture QR/current-KV writes exist here.
// Expected vectors are observers; all collective inputs come from actual VM.
#include "Vot_hdc_core_vector_weight_native_candidate.h"
#include "core_instruction_probe.hpp"
#include "Vot_qwen_tp8_native_services_frontend_native59.h"
#include "Vot_qwen_tp8_attention_service.h"
#include "Vot_qwen_tp8_kv_sector_adapter.h"
#include "rom_vm_adapter.hpp"
#include "services_vm_adapter.hpp"
#include "kernel_physical_rows.hpp"
#include <filesystem>
#include <iostream>
#include <iomanip>
#include <regex>
using namespace qwen_native_services;
using namespace qwen_actual_phy;
namespace fs=std::filesystem;
struct Layer {unsigned number,epoch,position;std::string image,program,oracle;};
static std::vector<Layer> read_plan(const std::string&path){
 std::ifstream file(path);if(!file)throw std::runtime_error("missing actual layer plan");
 std::vector<Layer> layers;std::string line;
 while(std::getline(file,line)){if(line.empty()||line[0]=='#')continue;std::istringstream in(line);Layer l;if(!(in>>l.number>>l.epoch>>l.position>>l.image>>l.program>>l.oracle))throw std::runtime_error("layer plan needs number epoch position image program oracle");std::string tail;if(in>>tail)throw std::runtime_error("extra layer plan field");if(l.number>=36||l.epoch>65535||l.position>=8192)throw std::runtime_error("layer plan bounds");if(!layers.empty()&&(l.number!=layers.back().number+1||l.epoch!=layers.back().epoch||l.position!=layers.back().position))throw std::runtime_error("noncontiguous layer or epoch/position plan");layers.push_back(l);}
 if(layers.empty())throw std::runtime_error("empty actual layer plan");return layers;
}
struct Rank {
 unsigned rank,first_layer;Layer active;uint64_t prior_target=0,layer_begin_edge=0,collector_cycles=0;VerilatedContext&ctx;
 qwen_native::RomVmAdapter vm;
 RowBackend backend;
 Vot_hdc_core_vector_weight_native_candidate core;
 Vot_qwen_tp8_native_services_frontend_native59 front;
 Vot_qwen_tp8_attention_service kernel;
 Vot_qwen_tp8_kv_sector_adapter sector;
 VmReceiver receiver;KernelRows reads;SectorWrites writes;
 struct Effect{unsigned pc,address,value;uint64_t edge;std::string port;};std::vector<Effect> effects;
 struct Descriptor{unsigned pc;uint64_t edge;std::vector<unsigned> values;};std::vector<Descriptor> su_descriptors;
 struct KvCommit{unsigned pc,address,value;uint64_t edge;};std::vector<KvCommit> kv_commits;
 struct RawWitness{unsigned pc,unit;uint64_t edge;bool end;qwen_native::HexWord<32> bits;};
 std::vector<RawWitness> raw_witnesses;qwen_native::HexWord<32> observer_next{};bool observer_next_valid=false;
 int su_owner=-1,rom_owner=-1;unsigned rom_written=0,rom_expected=0;
 bool epoch_reserved=false,head_stage=false,token_grant_ready=false,host_reset_bound=false,host_die_reset_n=false;uint64_t start_edge=0;
 Rank(VerilatedContext&context,unsigned r,const Layer& layer,const std::string& initial_x,bool zero_cold_vm=false)
 :rank(r),first_layer(layer.number),active(layer),ctx(context),vm(layer.image+"/die"+std::to_string(r),layer.program+"/die"+std::to_string(r)+"/program.hex",initial_x,zero_cold_vm),
 backend(context,layer.position,"rank"+std::to_string(r)+"_pc_"),
 core(&context,("rank"+std::to_string(r)+"_core").c_str()),front(&context,("rank"+std::to_string(r)+"_front").c_str()),
 kernel(&context,("rank"+std::to_string(r)+"_kernel").c_str()),sector(&context,("rank"+std::to_string(r)+"_sector").c_str()),
 receiver(vm.vm),reads(backend),writes(backend){
  if(const char*e=std::getenv("OT_SPLIT_LINK_LATENCY"))receiver.link_latency=unsigned(std::stoul(e));
  core.clk=front.clk=kernel.clk=sector.clk=0;core.rst_n=front.rst_n=kernel.rst_n=sector.rst_n=0;
  core.start=0;core.token=0;core.pos=layer.position;front.epoch=layer.epoch;front.layer=layer.number;front.pos=layer.position;front.token=0;front.epoch_begin=0;front.fused_program_capability=1;
#ifdef OT_CORE_HIERARCHICAL
  // Hierarchical children are registered lazily by the first eval. Construct
  // them serially at time zero, before worker phases advance the shared time.
  // Clock and reset are low, so this adds no functional clock edge.
  if(context.time()!=0)throw std::runtime_error("hierarchical rank initialization requires time zero");
  core.eval();
#endif
  enqueue_history();
 }
 // Input-memoised core evaluation: a Verilated eval whose 28 input ports all
 // equal those of its previous eval (and with no clock change) re-settles the
 // same combinational state and fires no process, so it is skipped. Exactly
 // equivalent; it removes the redundant second eval of each settle iteration.
 // The port list is the LV6 public header's complete VL_IN set (header sha
 // d1de5265...; core_input_ports_complete() re-checks the count at link time).
 std::vector<uint32_t> core_in_last,core_in_now;bool core_in_valid=false;uint64_t core_evals=0,core_evals_skipped=0;
 template<class T>static void push_port(std::vector<uint32_t>&v,const T&x){const uint32_t*p=reinterpret_cast<const uint32_t*>(&x);size_t n=(sizeof(T)+3)/4;
  if(sizeof(T)%4){uint32_t w=0;std::memcpy(&w,&x,sizeof(T)<4?sizeof(T):4);v.push_back(w);if(sizeof(T)<4)return;}
  v.insert(v.end(),p,p+sizeof(T)/4);}
 void core_eval(){
  auto&v=core_in_now;v.clear();auto&c=core;
  push_port(v,c.clk);
  push_port(v,c.rst_n);
  push_port(v,c.start);
  push_port(v,c.native_contract_ready);
  push_port(v,c.native_ready);
  push_port(v,c.native_idle);
  push_port(v,c.native_fault);
  push_port(v,c.su_descriptor_reserved);
  push_port(v,c.kv_write_drained);
  push_port(v,c.kv_ok);
  push_port(v,c.w_ok);
  push_port(v,c.emb_ok);
  push_port(v,c.me_mem_ok);
  push_port(v,c.token);
  push_port(v,c.pos);
  push_port(v,c.native_progress);
  push_port(v,c.embed_scale_q);
  push_port(v,c.prog_q);
  push_port(v,c.wrom_q);
  push_port(v,c.int8_wrom_q);
  push_port(v,c.scale_q);
  push_port(v,c.embed_code_q);
  push_port(v,c.crom_q);
  push_port(v,c.kv_q);
  push_port(v,c.vx_q);
  push_port(v,c.va_q);
  push_port(v,c.vb_q);
  push_port(v,c.vc_q);
  if(core_in_valid&&v==core_in_last){++core_evals_skipped;return;}
  if(memo_eval(v)){core_in_last=v;core_in_valid=true;return;}
  core.eval();++core_evals;core_in_last.swap(core_in_now);core_in_valid=true;
  memo_after_eval();
 }
 // Exact state memo (OT_EVAL_MEMO=0 disables). A Verilated eval is a pure
 // function of the generated root object (every signal, port, trigger and
 // previous-clock byte; 37.6 MB of plain data, no heap members; the only DPI
 // imports are the stateless ot_v41x_fadd/fmul and the model never reads
 // time). If the root bytes equal those before an earlier eval, that eval's
 // result bytes are reproduced instead of re-evaluating. The harness writes
 // only the 28 input ports, so the root = (non-port bytes) + (input vector):
 // non-port states are interned once (full masked compare at record time) and
 // tracked by id; a hit needs the same state id and the same input vector, and
 // applies the recorded byte delta pre->post. An idle core (startup before
 // HOST dispatch, waits on HBM/collective/attention) cycles through two
 // (state,input) pairs. OT_EVAL_MEMO_VERIFY=k re-evaluates every k-th hit and
 // throws if the result differs from the recorded post state.
 struct EvalMemo{std::vector<uint32_t> in;int pre=-1,post=-1;std::vector<std::pair<uint32_t,uint32_t>> runs;std::vector<uint8_t> delta;uint64_t used=0;};
 std::vector<EvalMemo> memo;std::vector<std::vector<uint8_t>> memo_snaps;std::vector<std::vector<uint32_t>> memo_recent;std::vector<uint8_t> memo_pre;
 std::vector<std::pair<size_t,size_t>> port_ranges;int memo_cur=-1;
 bool memo_recording=false;uint64_t memo_tick=0,memo_hits=0,memo_verified=0,memo_records=0,memo_dry=0;
 static size_t root_size(){static const size_t n=size_t(actual_core_root_bytes());return n;}
 // Hierarchical RTL FP units own sequential pipeline state outside rootp.
 // Replaying only root bytes cannot advance those child objects. Even VERIFY=1
 // checks only the parent and is insufficient, so disable this optimisation.
 static unsigned memo_slots(){
#ifdef OT_CORE_HIERARCHICAL
  return 0;
#else
  static const unsigned n=[]{const char*e=std::getenv("OT_EVAL_MEMO");return e?unsigned(std::stoul(e)):4u;}();return n;
#endif
 }
 static uint64_t memo_verify_every(){static const uint64_t n=[]{const char*e=std::getenv("OT_EVAL_MEMO_VERIFY");return e?uint64_t(std::stoull(e)):0ull;}();return n;}
 uint8_t*root_bytes(){return reinterpret_cast<uint8_t*>(core.rootp);}
 template<class T>void port_range(const T&x){auto o=reinterpret_cast<const uint8_t*>(&x)-root_bytes();
  if(o<0||size_t(o)+sizeof(T)>root_size())throw std::runtime_error("input port outside generated root");port_ranges.push_back({size_t(o),sizeof(T)});}
 void memo_ports(){if(!port_ranges.empty())return;auto&c=core;
  port_range(c.clk);port_range(c.rst_n);port_range(c.start);port_range(c.native_contract_ready);port_range(c.native_ready);port_range(c.native_idle);
  port_range(c.native_fault);port_range(c.su_descriptor_reserved);port_range(c.kv_write_drained);port_range(c.kv_ok);port_range(c.w_ok);port_range(c.emb_ok);
  port_range(c.me_mem_ok);port_range(c.token);port_range(c.pos);port_range(c.native_progress);port_range(c.embed_scale_q);port_range(c.prog_q);port_range(c.wrom_q);
  port_range(c.int8_wrom_q);port_range(c.scale_q);port_range(c.embed_code_q);port_range(c.crom_q);port_range(c.kv_q);port_range(c.vx_q);port_range(c.va_q);
  port_range(c.vb_q);port_range(c.vc_q);std::sort(port_ranges.begin(),port_ranges.end());}
 void mask(uint8_t*p){for(auto&r:port_ranges)std::memset(p+r.first,0,r.second);}
 // root (live ports) equals a masked snapshot outside the port bytes
 bool same_state(const uint8_t*root,const uint8_t*snap){size_t at=0;
  for(auto&r:port_ranges){if(r.first>at&&std::memcmp(root+at,snap+at,r.first-at))return false;at=std::max(at,r.first+r.second);}
  return std::memcmp(root+at,snap+at,root_size()-at)==0;}
 int intern(std::vector<uint8_t>&&snap){for(size_t i=0;i<memo_snaps.size();i++)if(memo_snaps[i]==snap)return int(i);memo_snaps.push_back(std::move(snap));return int(memo_snaps.size()-1);}
 bool memo_eval(const std::vector<uint32_t>&v){
  memo_recording=false;if(!memo_slots()||core_evals<4)return false;memo_ports();
  uint8_t*root=root_bytes();
  for(auto&m:memo){
   if(m.in!=v)continue;
   if(memo_cur<0&&same_state(root,memo_snaps[m.pre].data()))memo_cur=m.pre;
   if(memo_cur!=m.pre)continue;
   m.used=++memo_tick;++memo_hits;memo_dry=0;
   if(memo_verify_every()&&memo_hits%memo_verify_every()==0){
    core.eval();++core_evals;++memo_verified;
    if(!same_state(root,memo_snaps[m.post].data()))throw std::runtime_error("EXACT EVAL MEMO DIVERGENCE rank "+std::to_string(rank));
   }else{size_t k=0;for(auto&r:m.runs){std::memcpy(root+r.first,m.delta.data()+k,r.second);k+=r.second;}}
   memo_cur=m.post;return true;
  }
  // Record only a (state,input) pair whose input vector recurs (idle period);
  // back off while recordings produce no hits (streaming compute).
  bool recur=false;for(auto&x:memo_recent)recur|=x==v;
  if(recur&&(memo_dry<8||memo_dry%32==0)){memo_pre.assign(root,root+root_size());memo_recording=true;}
  if(recur)++memo_dry;
  return false;
 }
 void memo_after_eval(){
  memo_cur=-1;
  if(memo_slots()){memo_recent.push_back(core_in_last);if(memo_recent.size()>4)memo_recent.erase(memo_recent.begin());}
  if(!memo_recording)return;memo_recording=false;
  const size_t n=root_size();std::vector<uint8_t> post(root_bytes(),root_bytes()+n);mask(post.data());mask(memo_pre.data());
  if(memo_snaps.size()>=16){memo.clear();memo_snaps.clear();}
  EvalMemo e;e.in=core_in_last;
  for(size_t i=0;i<n;){if(memo_pre[i]==post[i]){++i;continue;}size_t j=i;while(j<n&&memo_pre[j]!=post[j])++j;
   e.runs.push_back({uint32_t(i),uint32_t(j-i)});e.delta.insert(e.delta.end(),post.begin()+i,post.begin()+j);i=j;}
  e.pre=intern(std::move(memo_pre));e.post=intern(std::move(post));memo_pre.clear();
  if(memo.size()>=memo_slots()){auto it=memo.begin();for(auto jt=memo.begin();jt!=memo.end();++jt)if(jt->used<it->used)it=jt;memo.erase(it);}
  e.used=++memo_tick;memo.push_back(std::move(e));++memo_records;memo_cur=memo.back().post;
 }
 void enqueue_history(){
  prior_target=backend.write_acks+8*active.position;
  for(unsigned kind=0;kind<2;kind++){
   std::ifstream f(active.oracle+"/die"+std::to_string(rank)+"/prior_"+(kind?"V":"K")+"_fp8.bin",std::ios::binary);
   if(!f)throw std::runtime_error("missing declared prior cache");
   for(unsigned t=0;t<active.position;t++)for(unsigned q=0;q<4;q++){Quarter bytes{};for(unsigned j=0;j<32;j++){int b=f.get();if(b<0)throw std::runtime_error("short declared prior cache");bytes[j/4]|=unsigned(b)<<(8*(j%4));}backend.enqueue_prior_quarter_via_actual_controller({{active.epoch,active.number,t,kind},q},bytes);}
   if(f.get()!=EOF)throw std::runtime_error("extra prior cache bytes");
  }
 }
 void switch_layer(const Layer&layer){
  if(!core.done||!front.native_idle||!core.su_is_idle||!reads.drained()||!writes.drained()||!receiver.acks.empty()&&receiver.inflight.empty()||!receiver.responses.empty()||rom_written!=rom_expected)
   throw std::runtime_error("actual layer switch before provider drain");
  if(layer.position!=active.position||layer.number!=active.number+1||layer.epoch!=active.epoch)throw std::runtime_error("invalid warm layer identity");
  auto actual_vm=vm.vm; // equality check only; never an oracle/reference state
  vm.writes.clear();vm.switch_banks(layer.image+"/die"+std::to_string(rank),layer.program+"/die"+std::to_string(rank)+"/program.hex");
  if(vm.vm!=actual_vm)throw std::runtime_error("ROM bank switch altered actual VM/X carry");
  active=layer;front.epoch=layer.epoch;front.layer=layer.number;front.pos=layer.position;core.pos=layer.position;
  effects.clear();su_descriptors.clear();kv_commits.clear();raw_witnesses.clear();su_owner=rom_owner=-1;rom_written=rom_expected=0;
  epoch_reserved=false;collector_cycles=0;enqueue_history();
 }
 void switch_head(const std::string&image,const std::string&program){
  if(!core.done||!front.native_idle||!core.su_is_idle||!reads.drained()||!writes.drained()||!receiver.acks.empty()&&receiver.inflight.empty()||!receiver.responses.empty()||rom_written!=rom_expected)
   throw std::runtime_error("actual head switch before layer provider drain");
  auto actual_vm=vm.vm;vm.writes.clear();
  vm.switch_banks(image+"/die"+std::to_string(rank),program+"/die"+std::to_string(rank)+"/program.hex",1600,0,1200);
  if(vm.vm!=actual_vm)throw std::runtime_error("head ROM switch changed actual final layer VM");
  effects.clear();su_descriptors.clear();kv_commits.clear();raw_witnesses.clear();su_owner=rom_owner=-1;rom_written=rom_expected=0;
  head_stage=true;start_edge=backend.core_edges+2;layer_begin_edge=backend.core_edges;
 }
 // Head-only seeded run: a freshly constructed rank (no edge yet, nothing in
 // flight) takes the head banks exactly as switch_head() does after layer 35.
 void prepare_head_first(const std::string&image,const std::string&program){
  if(backend.core_edges!=0||!vm.writes.empty())throw std::runtime_error("head-first preparation after the first edge");
  vm.switch_banks(image+"/die"+std::to_string(rank),program+"/die"+std::to_string(rank)+"/program.hex",1600,0,1200);
  head_stage=true;start_edge=2;layer_begin_edge=0;
 }
 void connect_core(){
  auto&c=core;auto&f=front;
  c.native_contract_ready=1;c.native_ready=f.native_ready;c.native_idle=f.native_idle;c.native_fault=f.fault;c.native_progress=f.native_progress;c.kv_write_drained=f.kv_committed;
  unsigned pc=c.su_pc+vm.segment_base;bool kv=c.su_descriptor_valid&&c.su_desc_dst==2;
  if(kv&&pc!=3&&pc!=8&&pc!=10)throw std::runtime_error("unexpected actual KV descriptor PC");
  f.kv_issue_kind=pc==3?0:pc==8?1:2;f.kv_issue_nout=c.su_desc_nout;f.kv_issue_nin=c.su_desc_nin;
  c.su_descriptor_reserved=!kv||f.kv_admit_ready;
  f.kv_issue_accepted=c.su_issue&&kv;f.kv_we=c.kv_we;
  for(unsigned j=0;j<48;j++)f.kv_waddr[j]=c.kv_waddr[j];for(unsigned j=0;j<64;j++)f.kv_wdata[j]=c.kv_wdata[j];
  f.native_go=c.native_go;f.native_xbase=c.native_xbase;f.native_obase=c.native_obase;f.native_nout=c.native_nout;f.native_k=c.native_k;f.native_pos=c.native_pos;
 }
 void low(bool start){
  core.clk=front.clk=kernel.clk=sector.clk=0;
  core.rst_n=front.rst_n=kernel.rst_n=sector.rst_n=backend.hbm_edges>=8&&(!host_reset_bound||host_die_reset_n);
  core.start=start;front.epoch_begin=0;
  if(!epoch_reserved){WriteAck prior;while(backend.pop_write_ack(prior)){};}
  if(token_grant_ready&&!epoch_reserved&&backend.write_acks==prior_target&&front.epoch_ready){front.epoch_begin=1;receiver.reserve(active.epoch,active.number,unsigned(front.token),active.position);epoch_reserved=true;start_edge=backend.core_edges+4;layer_begin_edge=backend.core_edges;}
  if(!epoch_reserved){WriteAck a;while(backend.pop_write_ack(a)){}front.store_ack_v=0;sector.ack_v=0;}
  else writes.prepare_acks(sector,front);
  receiver.drive(front);reads.drive(kernel);vm.drive_responses(core);
  // Every model eval repeats at least twice. Check all cross-model admission,
  // valid and payload faces; preserve same-edge nonblocking read semantics.
  auto face=[&](){std::vector<uint32_t>v={unsigned(core.native_go),unsigned(core.su_issue),unsigned(core.su_descriptor_reserved),unsigned(front.native_ready),unsigned(front.native_idle),unsigned(front.kv_admit_ready),unsigned(front.row_v),unsigned(front.row_ready),unsigned(sector.row_ready),unsigned(kernel.result_valid),unsigned(kernel.q_ready)};for(unsigned j=0;j<32;j++)v.push_back(front.row_data[j]);for(unsigned j=0;j<37;j++)v.push_back(sector.commands[j]);return v;};
  bool stable=false;for(unsigned n=0;n<24;n++){auto before=face();connect_core();core_eval();connect_core();SectorWrites::connect(sector,front);sector.eval();settle(front,kernel);SectorWrites::connect(sector,front);sector.eval();connect_core();core_eval();if(n>0&&before==face()){stable=true;break;}}
  if(!stable)throw std::runtime_error("actual core/frontend interfaces did not settle");
  // Read-only witness of the actual FIFO word captured by NEXT. Sample old
  // NEXT ownership before a simultaneous load replaces it on this rising edge.
  auto actual_instruction=read_actual_core_instruction_face(core);
  if(!core.rst_n)observer_next_valid=false;
  else {
   if(core.instruction_issue||core.end_retired){
    unsigned pc=vm.segment_base+(core.end_retired?core.end_pc:core.instruction_pc);
    if(!observer_next_valid||!actual_instruction.nx_valid||pc>=vm.program.size()||observer_next!=vm.program[pc])
     throw std::runtime_error("actual FIFO-to-NEXT accepted raw instruction differs from pinned source");
    raw_witnesses.push_back({pc,unsigned(core.end_retired?0:core.instruction_unit),vm.edge,bool(core.end_retired),observer_next});
   }
   if(actual_instruction.load){observer_next=actual_instruction.actual_fifo_word;observer_next_valid=true;}
  }
  vm.snapshot_edge(core);receiver.sample(front);writes.sample(sector);reads.sample(kernel);
  // Sample the old owner's registered write faces BEFORE accepting a new
  // descriptor on this edge. Ownership is never taken from fetch or NEXT.
  for(auto&w:vm.writes){int owner=(w.port=="SU"||w.port=="REDUCER")?su_owner:rom_owner;if(owner<0)throw std::runtime_error("unowned actual VM commit");effects.push_back({unsigned(owner),w.address,w.value,w.edge,w.port});if(w.port=="ME")++rom_written;}
  for(unsigned lane=0;lane<64;lane++)if(core.kv_we&(uint64_t(1)<<lane)){if(su_owner<0)throw std::runtime_error("unowned actual KV commit");kv_commits.push_back({unsigned(su_owner),get_bits(core.kv_waddr,24*lane,24),core.kv_wdata[lane],backend.core_edges});}
  if(core.instruction_issue){unsigned pc=vm.segment_base+core.instruction_pc;
   if(core.instruction_unit==2){if(!core.su_is_idle)throw std::runtime_error("SU owner changed before actual idle/drain");su_owner=pc;
    su_descriptors.push_back({pc,vm.edge,{core.su_desc_nout,core.su_desc_nin,core.su_desc_dst,core.su_desc_red,core.su_desc_ma,core.su_desc_mb,core.su_desc_sfu,core.su_desc_ad,core.su_desc_a_src,core.su_desc_b_src,core.su_desc_c_src,core.su_desc_mc,core.su_desc_md,core.su_desc_redsq,core.su_desc_imm1,core.su_desc_imm2,core.su_desc_a_base,core.su_desc_a_so,core.su_desc_a_si,core.su_desc_b_base,core.su_desc_b_so,core.su_desc_b_si,core.su_desc_c_base,core.su_desc_c_so,core.su_desc_c_si,core.su_desc_d_base,core.su_desc_d_so,core.su_desc_d_si,core.su_desc_r_base,core.su_desc_r_so}});
   }
   else if(core.instruction_unit==1&&(head_stage||pc!=11)){if(rom_owner>=0&&rom_written!=rom_expected)throw std::runtime_error("ROM owner changed before exact old output drain");rom_owner=pc;rom_written=0;rom_expected=head_stage?0:pc==1?768:pc==16?3072:4096;}
  }
 }
 void rise(){
  backend.core_edge(true);core.clk=front.clk=kernel.clk=sector.clk=1;core_eval();front.eval();kernel.eval();sector.eval();
  vm.commit_after_edge();for(auto&w:vm.writes)receiver.observe_write(w.address);
  receiver.store_after_edge();for(auto&w:receiver.landed){for(unsigned j=0;j<16;j++){vm.external_commit(w.address+j,w.data[j],"NATIVE_ATTN");effects.push_back({11,w.address+j,w.data[j],vm.edge,"NATIVE_ATTN"});}}
  if(core.fault||front.fault||kernel.fault||sector.fault)throw std::runtime_error("actual RTL fault rank "+std::to_string(rank));
 }
 void fall(){backend.core_edge(false);core.clk=front.clk=kernel.clk=sector.clk=0;core_eval();front.eval();kernel.eval();sector.eval();}
};
static fs::path layer_output(const Layer&layer,const fs::path&root,size_t count){return count==1?root:root/("layer"+std::to_string(layer.number));}
static unsigned save_layer(std::array<std::unique_ptr<Rank>,8>&r,const Layer&layer,const fs::path&output){
 unsigned errors=0;
 fs::create_directories(output);for(unsigned rank=0;rank<8;rank++){
  auto&x=*r[rank];auto gold=qwen_native::read_hex<1>(layer.oracle+"/die"+std::to_string(rank)+"/X_final_fp32.hex");if(gold.size()!=4096)throw std::runtime_error("final X observer dimensions");
  for(unsigned j=0;j<4096;j++)errors+=x.vm.vm[4096+j]!=gold[j][0];
  if(x.vm.accepted.size()!=22||x.vm.retired!=std::vector<unsigned>{13,21,24}||x.receiver.commit_acks!=32*(layer.number-r[0]->first_layer+1)||x.writes.committed!=8*(layer.number-r[0]->first_layer+1)||x.rom_written!=x.rom_expected||!x.reads.drained()||!x.writes.drained())throw std::runtime_error("missing executed layer effects rank "+std::to_string(rank));
  std::ofstream f(output/("rank"+std::to_string(rank)+"_VM.hex"));for(auto bits:x.vm.vm)f<<std::hex<<std::setfill('0')<<std::setw(8)<<bits<<"\n";
  std::ofstream a(output/("rank"+std::to_string(rank)+"_accepted.txt"));for(auto op:x.vm.accepted)a<<op.global_pc<<" "<<op.unit<<" "<<op.edge<<"\n";
  std::ofstream bits(output/("rank"+std::to_string(rank)+"_accepted_source_words.hex"));for(auto op:x.vm.accepted){for(unsigned word=0;word<32;word++)bits<<std::hex<<std::setfill('0')<<std::setw(8)<<op.instruction[31-word];bits<<"\n";}
  if(x.raw_witnesses.size()!=25)throw std::runtime_error("missing actual FIFO-to-NEXT accepted witnesses");
  std::ofstream raw(output/("rank"+std::to_string(rank)+"_accepted_actual_words.txt"));
  for(auto&w:x.raw_witnesses){raw<<w.pc<<" "<<w.unit<<" "<<w.edge<<" "<<w.end<<" ";for(unsigned j=0;j<32;j++)raw<<std::hex<<std::setfill('0')<<std::setw(8)<<w.bits[31-j];raw<<std::dec<<"\n";}
  if(x.receiver.q_tag_events.size()!=16)throw std::runtime_error("missing actual TAG59 QVM request/response observations");
  std::ofstream tags(output/("rank"+std::to_string(rank)+"_QVM_tags.txt"));for(auto&t:x.receiver.q_tag_events)tags<<t.edge<<" "<<std::hex<<t.tag<<std::dec<<" "<<t.epoch<<" "<<t.chunk<<" "<<t.response<<"\n";
  if(x.receiver.attn_tag_events.size()!=64)throw std::runtime_error("missing actual ATT write/ACK TAG59 observations");
  std::ofstream att_tags(output/("rank"+std::to_string(rank)+"_ATTN_tags.txt"));for(auto&t:x.receiver.attn_tag_events)att_tags<<t.edge<<" "<<std::hex<<t.tag<<std::dec<<" "<<t.address<<" "<<t.beat<<" "<<t.ack<<"\n";
  std::ofstream k(output/("rank"+std::to_string(rank)+"_KV.txt"));for(auto w:x.kv_commits)k<<w.address<<" "<<std::hex<<std::setfill('0')<<std::setw(8)<<w.value<<std::dec<<" "<<w.edge<<" "<<w.pc<<"\n";
  std::ofstream v(output/("rank"+std::to_string(rank)+"_VM_commits.txt"));for(auto w:x.vm.commits)v<<w.address<<" "<<std::hex<<std::setfill('0')<<std::setw(8)<<w.value<<std::dec<<" "<<w.edge<<" "<<w.port<<"\n";
  std::ofstream e(output/("rank"+std::to_string(rank)+"_operation_commits.txt"));for(auto w:x.effects)e<<w.pc<<" "<<w.address<<" "<<std::hex<<std::setfill('0')<<std::setw(8)<<w.value<<std::dec<<" "<<w.edge<<" "<<w.port<<"\n";
  std::ofstream s(output/("rank"+std::to_string(rank)+"_accepted_SU_descriptors.txt"));for(auto d:x.su_descriptors){s<<d.pc<<" "<<d.edge;for(auto value:d.values)s<<" "<<value;s<<"\n";}
 }
 std::ofstream cycles(output/"functional_cycles.json");cycles<<"{\"layer\":"<<layer.number<<",\"epoch\":"<<layer.epoch<<",\"core_begin\":"<<r[0]->layer_begin_edge<<",\"core_end\":"<<r[0]->backend.core_edges<<",\"core_cycles\":"<<r[0]->backend.core_edges-r[0]->layer_begin_edge<<",\"actual_persistent_collector_CORE_edges\":"<<r[0]->collector_cycles<<",\"unified_clock_measurement\":true,\"production_rate_qualified\":false,\"errors\":"<<errors<<"}\n";
 return errors;
}
static void save_head(std::array<std::unique_ptr<Rank>,8>&r,const fs::path&output){
 fs::create_directories(output);std::ofstream local(output/"local_argmax.txt");
 for(unsigned rank=0;rank<8;rank++){
  auto&x=*r[rank];if(!x.core.done||x.vm.retired!=std::vector<unsigned>{unsigned(x.vm.program.size()-1)}||x.vm.accepted.size()+1!=x.vm.program.size()||x.raw_witnesses.size()!=x.vm.program.size()||x.rom_written!=0||x.kv_commits.size()!=0||unsigned(x.core.next_token)>=18992)throw std::runtime_error("invalid actual local head retirement");
  local<<rank<<" "<<unsigned(x.core.next_token)<<" "<<std::hex<<std::setfill('0')<<std::setw(8)<<x.core.next_val<<std::dec<<" "<<x.backend.core_edges-x.layer_begin_edge<<"\n";
  std::ofstream vm(output/("rank"+std::to_string(rank)+"_VM.hex"));for(auto v:x.vm.vm)vm<<std::hex<<std::setfill('0')<<std::setw(8)<<v<<"\n";
  std::ofstream commits(output/("rank"+std::to_string(rank)+"_operation_commits.txt"));for(auto w:x.effects)commits<<w.pc<<" "<<w.address<<" "<<std::hex<<std::setfill('0')<<std::setw(8)<<w.value<<std::dec<<" "<<w.edge<<" "<<w.port<<"\n";
  std::ofstream accepted(output/("rank"+std::to_string(rank)+"_accepted.txt"));for(auto op:x.vm.accepted)accepted<<op.global_pc<<" "<<op.unit<<" "<<op.edge<<"\n";
  std::ofstream raw(output/("rank"+std::to_string(rank)+"_accepted_actual_words.txt"));for(auto&w:x.raw_witnesses){raw<<w.pc<<" "<<w.unit<<" "<<w.edge<<" "<<w.end<<" ";for(unsigned j=0;j<32;j++)raw<<std::hex<<std::setfill('0')<<std::setw(8)<<w.bits[31-j];raw<<std::dec<<"\n";}
 }
}
