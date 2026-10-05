#if !defined(DSROM_S81_STATIC_CONTROL_STAGE) || !defined(DSROM_S81_STATIC_CONTROL_MODEL_STAGE)
#error "Tagged static PQ TU requires both actual static-cut stage bindings"
#endif
// Additive tagged-PQ successor TU; compile INSTEAD baseline/static TU, never together.
#ifndef DSROM_S81_PQ_TAGGED_MODEL
#error "This TU requires actual tagged PQ Vcut/Vpq/Vpb source builds; old untagged archives are not enrollment"
#endif
// Additive TU successor: compile this instead of s81_minimum_qe.cpp, never together.
// Opt-in full source-selected QAL/KVAL field. No host arithmetic/private clock.
#include "s81_minimum_qe.hpp"
#ifdef DSROM_S81_STATIC_CONTROL_STAGE
#ifndef DSROM_S81_STATIC_CONTROL_MODEL_STAGE
#error "Static controls require a source-pinned static-provider cut build, not the old runtime-array model"
#endif
static_assert(DSROM_S81_STATIC_CONTROL_STAGE == DSROM_S81_STATIC_CONTROL_MODEL_STAGE, "static source/model stage mismatch");
#include "s81_static_field_controls.hpp"
#endif
#include "s81_minimum_qe_dpi.hpp"
#include "s81_minimum_return_cut_join.hpp"
#include "s81_minimum_source_tags_component.hpp"
#include "Vpq.h"
#include "Vpb.h"
#include "Vretn.h"
#include "Vroot.h"
#include "Vcut___024root.h"
#include "svdpi.h"
#include <algorithm>
#include <deque>
#include <map>
#include <set>
#include <unordered_map>

using namespace dsrom_s81_minimum;
// Defined in the existing reservation provider; same counter/accepted ledger.
std::array<uint32_t,8> dsrom_s81_reserve_qe_root_tag(
 DsromS81MinimumRuntime&,uint64_t,unsigned,const ReturnPhaseBinding&,const CaptureOwner&);
namespace {
void require(bool v,const char* s){if(!v)throw std::runtime_error(s);}
struct WordOwner {int stage,rank,pair;std::vector<uint64_t> cfg;DsromS81QeWordReader read;};
thread_local WordOwner* registering_qe=nullptr;
std::unordered_map<const void*,std::pair<WordOwner*,unsigned>> qe_rom;
std::unordered_map<const void*,WordOwner*> qe_cfg;
struct Pair {
 virtual ~Pair()=default;
 virtual void drive(const DsromS81PairDrive&,uint8_t)=0;
 virtual DsromS81PairResult result()const=0;
 virtual void edge(bool,bool)=0;
};
template<class Model>struct TypedPair:Pair {
 Model model;
 TypedPair(VerilatedContext*c,const char*n):model(c,n){}
 void drive(const DsromS81PairDrive&p,uint8_t actual_go_tag)override {
  model.go_tag=actual_go_tag;
  model.cfg_go=p.cfg_go;model.cfg_ph=p.cfg_ph;model.cfg_np=p.cfg_np;
  model.go=p.go;model.go_bf=p.go_bf;model.xs_v=p.xs_v;model.xs_p=p.xs_p;
  model.xs_b=p.xs_b;model.xs_sv=p.xs_sv;model.xs_e0=p.xs_e0;model.xs_e1=p.xs_e1;
  model.xs_pos=p.xs_pos;model.xb_pos=p.xb_pos;model.xb_v=p.xb_v;model.xb_b=p.xb_b;
  model.xb_sv=p.xb_sv;model.xb_u=p.xb_u;
  for(unsigned j=0;j<8;j++){model.xs_q0[j]=p.xs_q0[j];model.xs_q1[j]=p.xs_q1[j];}
  for(unsigned j=0;j<32;j++)model.xb_d[j]=p.xb_d[j];
 }
 DsromS81PairResult result()const override {
  return {model.pv,model.perr,model.ppos,model.pseg,model.pnseg,model.prow,
   model.pval,bool(model.busy),bool(model.quiet),bool(model.fault)};
 }
 void edge(bool clk,bool rn)override{model.clk=clk;model.rst_n=rn;model.eval();}
};
DsromS81PairDrive pins(const Vcut&c){
 DsromS81PairDrive p{};
 p.cfg_go=c.fb_cfg_go;p.cfg_ph=c.fb_cfg_ph;p.cfg_np=c.fb_cfg_np;
 p.go=c.fb_go;p.go_bf=c.fb_go_bf;p.xs_v=c.fb_xs_v;p.xs_p=c.fb_xs_p;
 p.xs_b=c.fb_xs_b;p.xs_sv=c.fb_xs_sv;p.xs_e0=c.fb_xs_e0;p.xs_e1=c.fb_xs_e1;
 p.xs_pos=c.fb_xs_pos;p.xb_pos=c.fb_xb_pos;p.xb_v=c.fb_xb_v;p.xb_b=c.fb_xb_b;
 p.xb_sv=c.fb_xb_sv;p.xb_u=c.fb_xb_u;
 for(unsigned j=0;j<8;j++){p.xs_q0[j]=c.fb_xs_q0[j];p.xs_q1[j]=c.fb_xs_q1[j];}
 for(unsigned j=0;j<32;j++)p.xb_d[j]=c.fb_xb_d[j];
 return p;
}
}
bool dsrom_s81_qe_register_rom(const char* instance){
 if(!registering_qe)return false;
 require(instance&&*instance,"QE ROM native instance missing");
 qe_rom.emplace(svGetScope(),std::make_pair(registering_qe,unsigned(instance[std::char_traits<char>::length(instance)-1]=='b')));
 return true;
}
bool dsrom_s81_qe_register_cfg(){
 if(!registering_qe)return false;
 qe_cfg.emplace(svGetScope(),registering_qe);return true;
}
bool dsrom_s81_qe_rom_read(int address,uint32_t*out){
 auto s=qe_rom.find(svGetScope());if(s==qe_rom.end())return false;
 require(address>=0&&address<8192,"QE logical ROM8192 address");
 auto& owner=*s->second.first;
 auto q=owner.read(owner.stage,owner.rank,4*owner.pair+2*s->second.second+(address&1),address>>1);
 require(!(q[8]>>18),"QE actual word exceeds274 bits");
 for(unsigned j=0;j<9;j++)out[j]=q[j];
 return true;
}
bool dsrom_s81_qe_cfg_read(int address,long long&out){
 auto s=qe_cfg.find(svGetScope());if(s==qe_cfg.end())return false;
 const auto&cfg=s->second->cfg;
 require(address>=0&&size_t(address)<cfg.size(),"QE actual CFG address");
 out=static_cast<long long>(cfg[address]);return true;
}

struct DsromS81NativeQe::Impl {
 struct Owned {
  WordOwner word;DsromS81QePairBinding binding;std::unique_ptr<Pair> pair;
  ~Owned(){
   for(auto i=qe_rom.begin();i!=qe_rom.end();)if(i->second.first==&word)i=qe_rom.erase(i);else ++i;
   for(auto i=qe_cfg.begin();i!=qe_cfg.end();)if(i->second==&word)i=qe_cfg.erase(i);else ++i;
  }
 };
 struct Wire {bool v=false,e=false;uint32_t t=0,d=0;};
 struct Node {int a,b;std::unique_ptr<Vretn> model;};
 struct Root {int input;ReturnPhaseBinding bound;std::unique_ptr<Vroot> model;NativeRootPorts sample;};
 struct Held {MacroWrite command;S81EmbeddingOutput out{};bool offered=false,accepted=false,visible=false;};
 DsromS81MinimumRuntime&r;uint64_t id;PrefixPublication&pub;DsromS81MinimumSourceIo io;
 Vcut&cut;DsromS81QePhase phase;std::function<bool()> prior_drained;
 std::map<unsigned,std::unique_ptr<Owned>> owners;
 std::vector<Node> nodes;std::map<unsigned,Root> roots;
 std::vector<Held> records;std::map<std::array<uint32_t,8>,size_t> record_owner;
 std::set<unsigned> captured_rows;size_t offered_head=0;unsigned accepted_count=0,visible_count=0;
 unsigned loaded=0,go_count=0,pair_go_count=0,rows=0,phase_number=0,k=0;
 bool cold=false,configured=false,running=false,accepted=false,finished=false,stopped=false;
 uint8_t issued_go_tag=0; bool issued_go_tag_valid=false;
 Impl(DsromS81MinimumRuntime&runtime,uint64_t identity,PrefixPublication&p,
      const DsromS81MinimumSourceIo&source,Vcut&native,DsromS81QePhase binding,
      DsromS81QeWordReader read,std::function<bool()> preceding)
 :r(runtime),id(identity),pub(p),io(source),cut(native),phase(std::move(binding)),prior_drained(std::move(preceding)) {
  require(r.context&&cut.contextp()==r.context&&r.stage>=0&&r.stage<81&&r.rank>=0&&r.rank<4&&
   id<(1ull<<47)&&io.read_word&&io.span_lease&&io.offer&&io.visible&&read&&r.cycle&&prior_drained,
   "QE actual common context/SourceIo/native source/prior publication required");
  rows=(phase.phrom[0]>>46)&65535;
  require(rows<=16384,"PQ actual row domain exceeds packed row14/tag2 contract");k=(phase.phrom[0]>>1)&8191;
  require((phase.operation.unit==3||phase.operation.unit==1)&&phase.operation.index<(1u<<14)&&
   rows>0&&rows<=65535&&phase.ops==rows&&!phase.pairs.empty()&&phase.pairs.size()<=2417,
   "QE complete selected matrix phase geometry required");
  require(k>0&&k<=6144&&phase.phrom[1]<=65535&&
   phase.stream.size()==((phase.phrom[0]>>14)&65535),"QE literal native PHROM/stream mismatch");
  const auto base=(phase.phrom[0]>>30)&65535;
  require(!phase.stream.empty()&&base+phase.stream.size()<=16384&&
   uint64_t(phase.xbase)+k<=(1u<<19)&&uint64_t(phase.cut_input_alias)+k<=65536&&phase.cut_output_alias+rows<=65536&&
   !(phase.cut_output_alias<phase.cut_input_alias+k&&phase.cut_input_alias<phase.cut_output_alias+rows),
   "QE cut-only alias/input/stream aperture");
  if(phase.operation.unit==1){
   require(phase.actual_input_addresses.size()==k&&phase.actual_output_addresses.size()==rows,
    "ME field execution needs exact original input/output source mapping, not QE relabeling");
  }
  if(!phase.actual_input_addresses.empty()){
   require(phase.actual_input_addresses.size()==k,"field ordered-K input mapping extent");
   for(auto a:phase.actual_input_addresses)require(a<(1u<<19),"field mapped input VM19");
  }
  if(!phase.actual_output_addresses.empty()){
   require(phase.actual_output_addresses.size()==rows,"field source output mapping extent");
   std::set<uint32_t> mapped;
   for(auto a:phase.actual_output_addresses)require(a<(1u<<19)&&mapped.insert(a).second,"field mapped output VM19/alias");
  }
  std::set<unsigned> row_set;bool first=true;
  for(const auto&x:phase.pairs){
   const auto&b=x.returned;
   if(first){phase_number=b.phase;first=false;}
   require(b.stage>=0&&b.stage<81&&b.rank==r.rank&&b.identity==id&&b.phase==phase_number&&b.phase<1024&&
    b.positions_minus_one==0&&b.format<3&&b.phrom0==phase.phrom[0]&&b.phrom1==phase.phrom[1]&&
    b.output_position_stride==rows&&b.output_base+rows<=(1u<<19)&&
    b.root<128&&b.pair>=0&&b.pair<2417&&!b.component_rows.empty()&&
    b.branch_a_leaf==2*unsigned(b.pair)&&b.branch_b_leaf==2*unsigned(b.pair)+1&&
    b.region_pair_begin<=b.pair&&b.pair<b.region_pair_end&&b.region_pair_end<=2417&&
    b.region_pair_end-b.region_pair_begin<=32&&x.config.size()==25*(phase_number+1)&&
    b.source_matrix_sha256.size()==64&&!b.emitted_key.empty()&&!b.cfg_path.empty(),
    "QE actual complete-K physical pair/phase/root ownership required");
   const auto&ref=phase.pairs.front().returned;
   require(b.stage==ref.stage&&b.output_base==ref.output_base&&b.emitted_key==ref.emitted_key&&
    b.source_matrix_sha256==ref.source_matrix_sha256,"QE phase identity alias");
   require(!(phase.phrom[0]&1)||x.physical_bf_site,"QE BF phase assigned to non-BF physical site");
   for(auto w:x.config)require(w<(1ull<<48),"QE CFG48");
   for(auto row:b.component_rows)require(row<rows&&(row/2)%128==b.root&&row_set.insert(row).second,
    "QE source row ownership/alias");
   require(!owners.count(b.pair),"QE duplicate physical pair");
   auto o=std::make_unique<Owned>();o->binding=x;o->word={b.stage,b.rank,b.pair,x.config,read};
   registering_qe=&o->word;
   try{
    auto name="native_qe_producer_"+std::to_string(phase.operation.index)+"_stage_"+std::to_string(b.stage)+"_phase_"+std::to_string(phase_number)+"_pair_"+std::to_string(b.pair);
    if(x.physical_bf_site)o->pair=std::make_unique<TypedPair<Vpb>>(r.context,name.c_str());
    else o->pair=std::make_unique<TypedPair<Vpq>>(r.context,name.c_str());
    o->pair->drive({},0);o->pair->edge(false,false);
   }catch(...){registering_qe=nullptr;throw;}
   registering_qe=nullptr;owners.emplace(b.pair,std::move(o));
   auto i=roots.find(b.root);
   if(i==roots.end()){Root rt{};rt.bound=b;roots.emplace(b.root,std::move(rt));}
   else {
    require(i->second.bound.region_pair_begin==b.region_pair_begin&&i->second.bound.region_pair_end==b.region_pair_end,
     "QE physical region ownership disagreement");
    i->second.bound.component_rows.insert(i->second.bound.component_rows.end(),b.component_rows.begin(),b.component_rows.end());
   }
  }
  require(row_set.size()==rows,"QE ALL selected native rows required before admission");
  for(auto w:phase.stream)require(w<(1ull<<48),"QE native stream48");
  // Literal source region: 32 pair seats, 64 leaves, six levels. Retain EVERY
  // active ancestor, including unary delay/WAIT nodes. No per-pair root copies.
  for(auto& rr:roots){
   auto&rt=rr.second;const auto&b=rt.bound;
   require(b.component_rows.size()==native_root_quota(b.phrom0,0,b.root),"QE whole root quota incomplete");
   std::vector<int> layer(64,-1);
   for(const auto& pp:owners)if(pp.second->binding.returned.root==b.root){
    unsigned seat=pp.first-b.region_pair_begin;
    layer[2*seat]=2*pp.first;layer[2*seat+1]=2*pp.first+1;
   }
   for(unsigned level=0;level<6;level++){
    std::vector<int> next;
    for(unsigned seat=0;seat<layer.size();seat+=2){
     int a=layer[seat],bb=layer[seat+1];
     if(a<0&&bb<0){next.push_back(-1);continue;}
     auto name="native_qe_producer_"+std::to_string(phase.operation.index)+"_stage_"+std::to_string(b.stage)+"_phase_"+std::to_string(phase_number)+"_region_"+std::to_string(b.root)+
      "_level_"+std::to_string(level)+"_node_"+std::to_string(seat/2);
     Node n{a,bb,std::make_unique<Vretn>(r.context,name.c_str())};
     n.model->clk=0;n.model->rst_n=0;n.model->a_v=0;n.model->b_v=0;
     n.model->a_e=0;n.model->b_e=0;n.model->a_t=0;n.model->b_t=0;n.model->a_d=0;n.model->b_d=0;n.model->eval();
     next.push_back(4834+nodes.size());nodes.push_back(std::move(n));
    }
    layer=std::move(next);
   }
   require(layer.size()==1&&layer[0]>=4834,"QE retained region topology incomplete");rt.input=layer[0];
   auto name="native_qe_producer_"+std::to_string(phase.operation.index)+"_stage_"+std::to_string(b.stage)+"_phase_"+std::to_string(phase_number)+"_root_"+std::to_string(b.root);
   rt.model=std::make_unique<Vroot>(r.context,name.c_str());
   rt.model->clk=0;rt.model->rst_n=0;rt.model->i_v=0;rt.model->i_e=0;
   rt.model->i_t=0;rt.model->i_d=0;rt.model->eval();
  }
  records.reserve(rows);
 }
 Wire old_wire(int index)const {
  if(index<0)return {};
  if(index>=4834){const auto&m=*nodes.at(index-4834).model;return {bool(m.o_v),bool(m.o_e),m.o_t,m.o_d};}
  const auto pp=owners.find(unsigned(index)/2);require(pp!=owners.end(),"QE missing native leaf");
  auto p=partial(pp->second->pair->result(),index&1);
  return {p.valid,p.error,p.valid?native_partial_tag(p):0,p.fp32_bits};
 }
 bool all_quiet()const {
  for(const auto&o:owners)if(!o.second->pair->result().quiet||o.second->pair->result().fault)return false;
  for(const auto&n:nodes)if(!n.model->quiet||n.model->o_v||n.model->fault)return false;
  for(const auto&rr:roots){const auto&m=*rr.second.model;
   if(m.fault||m.r_v||m.obs_qc||m.obs_held||m.obs_add||m.obs_sv)return false;}
  return true;
 }
 bool done()const {
  return running&&records.size()==rows&&accepted_count==rows&&visible_count==rows&&offered_head==rows&&
   !cut.fault&&cut.idle&&!cut.obs_rows_left&&pub.complete(id,phase.operation.index)&&all_quiet();
 }
 uint32_t input_address(unsigned i)const {
  return phase.actual_input_addresses.empty()?phase.xbase+i:phase.actual_input_addresses.at(i);
 }
 bool input_owned()const {
  if(phase.actual_input_addresses.empty())return io.span_lease(id,phase.xbase,k);
  for(auto a:phase.actual_input_addresses)if(!io.span_lease(id,a,1))return false;
  return true;
 }
 bool inputs(const DsromS81PrefixOperation&op){
  require(op.index==phase.operation.index&&op.unit==phase.operation.unit&&op.instruction==phase.operation.instruction,"QE held source instruction changed");
  require(!stopped&&!finished,"QE source producer cannot be silently reused");
  if(running)return false;
  if(!configured){
   if(!cold||!cut.idle||cut.obs_rows_left||!all_quiet()||!prior_drained())return false;
#ifdef DSROM_S81_STATIC_CONTROL_STAGE
   require(phase.pairs.front().returned.stage==DSROM_S81_STATIC_CONTROL_STAGE,
           "immutable compiled cut stage differs from actual source binding");
   dsrom_s81_static_controls::validate(DSROM_S81_STATIC_CONTROL_STAGE,phase_number,phase.phrom,phase.stream);
   // Actual compiled static-provider model serves the immutable relocated body.
   // No host phrom/strom writes. GO retains canonical phase, native VM bases and ownership.
#else
   const unsigned base=(phase.phrom[0]>>30)&65535;
   cut.rootp->dsrom_source_cut__DOT__dut__DOT__u_sp__DOT__phrom[2*phase_number]=phase.phrom[0];
   cut.rootp->dsrom_source_cut__DOT__dut__DOT__u_sp__DOT__phrom[2*phase_number+1]=phase.phrom[1];
   for(unsigned j=0;j<phase.stream.size();j++)cut.rootp->dsrom_source_cut__DOT__dut__DOT__u_sp__DOT__strom[base+j]=phase.stream[j];
#endif
   cut.i_ph=phase_number;cut.i_np=0;cut.i_xbase=phase.cut_input_alias;cut.i_xps=0;cut.i_obase=phase.cut_output_alias;cut.i_ops=phase.ops;cut.go=0;
   configured=true;
  }
  if(!input_owned())return false;
  if(loaded<k){
   auto v=io.read_word(id,input_address(loaded));if(!v)return false;
   require(input_owned(),"QE actual XN version lost at read response");
   cut.rootp->dsrom_source_cut__DOT__dut__DOT__vm[phase.cut_input_alias+loaded]=*v;++loaded;
  }
  return loaded==k;
 }
 void drive(const DsromS81PrefixOperation&op,bool go){
  if(!configured)return;
  if(go)require(!running&&op.index==phase.operation.index&&op.instruction==phase.operation.instruction&&
   loaded==k&&cut.ready&&cut.idle&&input_owned(),"QE GO before actual input/version/ready");
  cut.go=go;
 }
 void prepare(const DsromS81PairResult&){
  require(!fault(),"QE quarantined; native debts retained");accepted=configured&&cut.go&&cut.ready;
  if(configured){
   r.drive({}); // singleton fixture is not an additional source pair
   for(unsigned j=0;j<4;j++){cut.fr_v[j]=0;cut.fr_e[j]=0;}cut.fr_fault=0;
   for(auto&rr:roots){auto&rt=rr.second;const auto&m=*rt.model;unsigned root=rr.first;
    rt.sample={bool(m.r_v),bool(m.r_e),uint16_t(m.r_row),uint16_t(m.r_bf16),uint8_t(m.r_pos),uint32_t(m.r_fp32)};
    root_pin_field(cut.fr_v,root,1,rt.sample.valid);root_pin_field(cut.fr_e,root,1,rt.sample.error);
    root_pin_field(cut.fr_row,root*16,16,rt.sample.row);root_pin_field(cut.fr_pos,root*3,3,rt.sample.position);
    root_pin_field(cut.fr_fp32,root*32,32,rt.sample.fp32);root_pin_field(cut.fr_bf16,root*16,16,rt.sample.bf16);
    cut.fr_fault=bool(cut.fr_fault)||bool(m.fault);
   }
  }else for(auto&rr:roots)rr.second.sample={};
  auto drive=running?pins(cut):DsromS81PairDrive{};
  if(running&&drive.go){require(bool(drive.go_bf)==bool(phase.phrom[0]&1),"QE native input format differs from selected PHROM");require(!issued_go_tag_valid,"PQ duplicate issued GO tag");issued_go_tag=cut.fb_go_tag;issued_go_tag_valid=true;pair_go_count++;}
  for(auto&o:owners)o.second->pair->drive(drive,cut.fb_go_tag);
  for(auto&n:nodes){auto a=old_wire(n.a),b=old_wire(n.b);auto&m=*n.model;
   require(running||(!a.v&&!b.v),"QE leaf valid before native admission");
   m.a_v=a.v;m.a_e=a.e;m.a_t=a.t;m.a_d=a.d;m.b_v=b.v;m.b_e=b.e;m.b_t=b.t;m.b_d=b.d;
  }
  for(auto&rr:roots){auto w=old_wire(rr.second.input);auto&m=*rr.second.model;m.i_v=w.v;m.i_e=w.e;m.i_t=w.t;m.i_d=w.d;}
  if(offered_head<records.size()){
   auto&h=records[offered_head];if(!h.offered)h.offered=io.offer(h.out,1);
   if(h.offered&&io.visible(h.out,1))++offered_head;
  }
  if(done()){require(go_count==1&&pair_go_count==1,"QE source accepted GO count mismatch");
   finished=true;running=false;configured=false;cut.go=0;}
 }
 void capture(Root&rt){
  auto s=rt.sample;if(!s.valid)return;
  require(issued_go_tag_valid&&(s.row>>14)==issued_go_tag,"PQ foreign native root tag");
  s.row &= 0x3fff; // source-defined tag2/row14 split, after positive owner-tag check
  const auto&b=rt.bound;
  require(running&&!s.error&&s.position==0&&s.row<rows&&(s.row/2)%128==b.root&&
   std::find(b.component_rows.begin(),b.component_rows.end(),s.row)!=b.component_rows.end()&&
   captured_rows.insert(s.row).second,"QE unowned/duplicate/faulted native root pulse");
  const uint32_t address=phase.actual_output_addresses.empty()?b.output_base+s.row:phase.actual_output_addresses.at(s.row);
  const ReturnPhaseBinding* actual_pair=nullptr;
  for(const auto&pp:owners){const auto&candidate=pp.second->binding.returned;
   if(candidate.root==b.root&&std::find(candidate.component_rows.begin(),candidate.component_rows.end(),s.row)!=candidate.component_rows.end()){
    require(!actual_pair,"QE ambiguous source pair for completed row");actual_pair=&candidate;
   }
  }
  require(actual_pair,"QE source pair absent for completed row");
  CaptureOwner owner{id,uint16_t(phase_number),s.row,b.root,s.position,address};
  MacroWrite c{};c.source=owner;c.word.address=address>>4;c.word.mask=1u<<(address&15);
  const bool fp32=b.format==1||(b.format==0&&((s.row<(b.phrom1&65535))?((b.phrom0>>62)&1):((b.phrom0>>63)&1)));
  c.word.data[address&15]=fp32?s.fp32:uint32_t(s.bf16)<<16;
  // Same existing provider's reservation counter; no accept at capture/offer.
  c.word.owner=dsrom_s81_reserve_qe_root_tag(r,id,phase.operation.index,*actual_pair,owner);
  require(record_owner.emplace(c.word.owner,records.size()).second,"QE reused root reservation");
  pub.native_scalar(phase.operation.index,c,true);
  Held h{};h.command=c;h.out.vm_valid=true;h.out.vm_identity=id;h.out.vm_address=address;
  h.out.vm_data[0]=c.word.data[address&15];records.push_back(h);
 }
 void rising(bool rn){
  if(!rn){require(!running&&!go_count,"QE reset cannot erase accepted phase");cold=true;}
  if(rn&&accepted){require(!running&&configured&&loaded==k&&r.identity&&*r.identity==id,
   "QE duplicate/unowned native admission");running=true;go_count++;}
  for(auto&o:owners)o.second->pair->edge(true,rn);
  for(auto&n:nodes){n.model->clk=1;n.model->rst_n=rn;n.model->eval();}
  for(auto&rr:roots){auto&m=*rr.second.model;m.clk=1;m.rst_n=rn;m.eval();if(rn)capture(rr.second);}
  // Borrowed Vcut is evaluated ONLY by Sagan's shared participant.
 }
 void falling(bool rn){
  for(auto&o:owners)o.second->pair->edge(false,rn);
  for(auto&n:nodes){n.model->clk=0;n.model->rst_n=rn;n.model->eval();}
  for(auto&rr:roots){rr.second.model->clk=0;rr.second.model->rst_n=rn;rr.second.model->eval();}
 }
 bool fault()const {
  if(stopped||pub.fault()||(configured&&cut.fault))return true;
  for(const auto&o:owners)if(o.second->pair->result().fault)return true;
  for(const auto&n:nodes)if(n.model->fault)return true;
  for(const auto&rr:roots)if(rr.second.model->fault)return true;
  return false;
 }
 Held& matched(unsigned bank,const MacroWrite&c){
  require(running&&c.source.identity==id&&c.source.phase==phase_number&&bank==((c.source.element_address>>4)&3),
   "QE callback source phase/context/bank");
  auto it=record_owner.find(c.word.owner);require(it!=record_owner.end(),"QE callback absent actual native root capture");
  auto&h=records.at(it->second);require(h.command.source.element_address==c.source.element_address&&
   h.command.source.root==c.source.root&&h.command.source.row==c.source.row&&
   h.command.word.address==c.word.address&&h.command.word.mask==c.word.mask&&h.command.word.data==c.word.data,
   "QE callback mutated held root tuple");return h;
 }
};
DsromS81NativeQe::DsromS81NativeQe(DsromS81MinimumRuntime&r,uint64_t id,PrefixPublication&p,
 const DsromS81MinimumSourceIo&io,Vcut&cut,DsromS81QePhase phase,DsromS81QeWordReader read,
 std::function<bool()> prior_drained)
 :impl(std::make_shared<Impl>(r,id,p,io,cut,std::move(phase),std::move(read),std::move(prior_drained))){}
DsromS81PrefixNativeEngine DsromS81NativeQe::engine(){
 auto p=impl;
 return {{"native-full-QAL-KVAL-source-return-graph",[p](const auto&r){try{p->prepare(r);}catch(...){p->stopped=true;throw;}},
  [p](bool rn){try{p->rising(rn);}catch(...){p->stopped=true;throw;}},
  [p](bool rn){p->falling(rn);},[p](){return p->fault();}},
  [p](){return p->configured&&!p->running&&!p->finished&&p->loaded==p->k&&bool(p->cut.ready)&&p->all_quiet();},
  [p](){return ((!p->running&&p->records.empty()&&p->all_quiet())||p->finished)&&!p->fault();},
  [p](const auto&o){try{return p->inputs(o);}catch(...){p->stopped=true;throw;}},
  [p](const auto&o,bool go){p->drive(o,go);}};
}
void DsromS81NativeQe::scalar_accept(unsigned bank,const MacroWrite&c){
 auto&h=impl->matched(bank,c);require(!h.accepted,"QE duplicate actual bank acceptance");h.accepted=true;impl->accepted_count++;
}
void DsromS81NativeQe::scalar_visible(unsigned bank,const MacroWrite&c,const VmReceipt&v){
 auto&h=impl->matched(bank,c);require(h.accepted&&!h.visible&&v.owner==c.word.owner&&v.address==c.word.address&&v.mask==c.word.mask,
  "QE VM visibility lacks accepted matching old tuple");h.visible=true;impl->visible_count++;
 // SourceFactory retires the SAME reservation once; this hook observes only.
}
bool DsromS81NativeQe::active()const{return impl->configured;}
bool DsromS81NativeQe::complete()const{return impl->finished&&!impl->fault();}

bool DsromS81NativeQe::owns(const MacroWrite&c)const{
 return impl->record_owner.count(c.word.owner)!=0;
}
unsigned DsromS81NativeQe::producer()const{return impl->phase.operation.index;}
DsromS81PrefixNativeEngine dsrom_s81_qe_dispatch(const std::vector<std::shared_ptr<DsromS81NativeQe>>&phases){
 struct Dispatcher {
  std::vector<std::shared_ptr<DsromS81NativeQe>> owners;
  std::map<unsigned,DsromS81PrefixNativeEngine> engines;
  std::optional<unsigned> selected;
  bool fault()const {for(const auto&e:engines)if(e.second.participant.fault())return true;return false;}
 };
 auto d=std::make_shared<Dispatcher>();d->owners=phases;
 if(phases.empty())throw std::runtime_error("QE dispatcher needs actual source phases");
 for(const auto&p:phases)if(!p||!d->engines.emplace(p->producer(),p->engine()).second)
  throw std::runtime_error("QE duplicate/null producer binding");
 return {{"full-source-QE-unit3-dispatch",
  [d](const auto&r){for(auto&e:d->engines)e.second.participant.prepare(r);},
  [d](bool rn){for(auto&e:d->engines)e.second.participant.rising(rn);},
  [d](bool rn){for(auto&e:d->engines)e.second.participant.falling(rn);},
  [d](){return d->fault();}},
  [d](){return d->selected&&d->engines.at(*d->selected).ready();},
  [d](){return !d->selected||d->engines.at(*d->selected).idle();},
  [d](const auto&op){
   if((op.unit!=3&&op.unit!=1)||!d->engines.count(op.index))throw std::runtime_error("QE operation not actually enrolled");
   if(d->selected&&*d->selected!=op.index&&!d->engines.at(*d->selected).idle())
    throw std::runtime_error("QE rearm before actual prior return/publication drain");
   d->selected=op.index;return d->engines.at(op.index).inputs_ready(op);
  },
  [d](const auto&op,bool go){
   if(!go){for(auto&e:d->engines)e.second.drive(op,false);return;}
   if(!d->selected||*d->selected!=op.index)throw std::runtime_error("QE GO lacks source-selected actor");
   d->engines.at(*d->selected).drive(op,true);
  }};
}
