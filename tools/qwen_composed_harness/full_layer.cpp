// Candidate executed-layer harness. No fixture QR/current-KV writes exist here.
// Expected vectors are observers; all collective inputs come from actual VM.
#include "Vot_hdc_core_vector_weight_native_candidate.h"
#include "Vot_hdc_core_vector_weight_native_candidate___024root.h"
#include "Vot_qwen_tp8_native_services_frontend.h"
#include "Vot_qwen_tp8_attention_service.h"
#include "Vot_qwen_tp8_kv_sector_adapter.h"
#include "rom_vm_adapter.hpp"
#include "services_vm_adapter.hpp"
#include "kernel_physical_rows.hpp"
#include <filesystem>
#include <iostream>
#include <iomanip>
#include <regex>
#include <sys/wait.h>
#include <unistd.h>
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
 Vot_qwen_tp8_native_services_frontend front;
 Vot_qwen_tp8_attention_service kernel;
 Vot_qwen_tp8_kv_sector_adapter sector;
 VmReceiver receiver;KernelRows reads;SectorWrites writes;
 struct Effect{unsigned pc,address,value;uint64_t edge;std::string port;};std::vector<Effect> effects;
 struct Descriptor{unsigned pc;uint64_t edge;std::vector<unsigned> values;};std::vector<Descriptor> su_descriptors;
 struct KvCommit{unsigned pc,address,value;uint64_t edge;};std::vector<KvCommit> kv_commits;
 struct RawWitness{unsigned pc,unit;uint64_t edge;bool end;qwen_native::HexWord<32> bits;};
 std::vector<RawWitness> raw_witnesses;qwen_native::HexWord<32> observer_next{};bool observer_next_valid=false;
 int su_owner=-1,rom_owner=-1;unsigned rom_written=0,rom_expected=0;
 bool epoch_reserved=false,head_stage=false;uint64_t start_edge=0;
 Rank(VerilatedContext&context,unsigned r,const Layer& layer,const std::string& initial_x)
 :rank(r),first_layer(layer.number),active(layer),ctx(context),vm(layer.image+"/die"+std::to_string(r),layer.program+"/die"+std::to_string(r)+"/program.hex",initial_x),
 backend(context,layer.position,"rank"+std::to_string(r)+"_pc_"),
 core(&context,("rank"+std::to_string(r)+"_core").c_str()),front(&context,("rank"+std::to_string(r)+"_front").c_str()),
 kernel(&context,("rank"+std::to_string(r)+"_kernel").c_str()),sector(&context,("rank"+std::to_string(r)+"_sector").c_str()),
 receiver(vm.vm),reads(backend),writes(backend){
  core.clk=front.clk=kernel.clk=sector.clk=0;core.rst_n=front.rst_n=kernel.rst_n=sector.rst_n=0;
  core.start=0;core.token=0;core.pos=layer.position;front.epoch=layer.epoch;front.layer=layer.number;front.pos=layer.position;front.epoch_begin=0;front.fused_program_capability=1;
  enqueue_history();
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
  if(!core.done||!front.native_idle||!core.su_is_idle||!reads.drained()||!writes.drained()||!receiver.acks.empty()||!receiver.responses.empty()||rom_written!=rom_expected)
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
  if(!core.done||!front.native_idle||!core.su_is_idle||!reads.drained()||!writes.drained()||!receiver.acks.empty()||!receiver.responses.empty()||rom_written!=rom_expected)
   throw std::runtime_error("actual head switch before layer provider drain");
  auto actual_vm=vm.vm;vm.writes.clear();
  vm.switch_banks(image+"/die"+std::to_string(rank),program+"/die"+std::to_string(rank)+"/program.hex",1600,0,1200);
  if(vm.vm!=actual_vm)throw std::runtime_error("head ROM switch changed actual final layer VM");
  effects.clear();su_descriptors.clear();kv_commits.clear();raw_witnesses.clear();su_owner=rom_owner=-1;rom_written=rom_expected=0;
  head_stage=true;start_edge=backend.core_edges+2;layer_begin_edge=backend.core_edges;
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
  core.rst_n=front.rst_n=kernel.rst_n=sector.rst_n=backend.hbm_edges>=8;
  core.start=start;front.epoch_begin=0;
  if(!epoch_reserved){WriteAck prior;while(backend.pop_write_ack(prior)){};}
  if(!epoch_reserved&&backend.write_acks==prior_target&&front.epoch_ready){front.epoch_begin=1;receiver.reserve(active.epoch,active.number);epoch_reserved=true;start_edge=backend.core_edges+4;layer_begin_edge=backend.core_edges;}
  if(!epoch_reserved){WriteAck a;while(backend.pop_write_ack(a)){}front.store_ack_v=0;sector.ack_v=0;}
  else writes.prepare_acks(sector,front);
  receiver.drive(front);reads.drive(kernel);vm.drive_responses(core);
  // Every model eval repeats at least twice. Check all cross-model admission,
  // valid and payload faces; preserve same-edge nonblocking read semantics.
  auto face=[&](){std::vector<uint32_t>v={unsigned(core.native_go),unsigned(core.su_issue),unsigned(core.su_descriptor_reserved),unsigned(front.native_ready),unsigned(front.native_idle),unsigned(front.kv_admit_ready),unsigned(front.row_v),unsigned(front.row_ready),unsigned(sector.row_ready),unsigned(kernel.result_valid),unsigned(kernel.q_ready)};for(unsigned j=0;j<32;j++)v.push_back(front.row_data[j]);for(unsigned j=0;j<37;j++)v.push_back(sector.commands[j]);return v;};
  bool stable=false;for(unsigned n=0;n<24;n++){auto before=face();connect_core();core.eval();connect_core();SectorWrites::connect(sector,front);sector.eval();settle(front,kernel);SectorWrites::connect(sector,front);sector.eval();connect_core();core.eval();if(n>0&&before==face()){stable=true;break;}}
  if(!stable)throw std::runtime_error("actual core/frontend interfaces did not settle");
  // Read-only witness of the actual FIFO word captured by NEXT. Sample old
  // NEXT ownership before a simultaneous load replaces it on this rising edge.
  auto&root=*core.rootp;
  if(!core.rst_n)observer_next_valid=false;
  else {
   if(core.instruction_issue||core.end_retired){
    unsigned pc=vm.segment_base+(core.end_retired?core.end_pc:core.instruction_pc);
    if(!observer_next_valid||!root.ot_hdc_core_vector_weight_native_candidate__DOT__nx_v||pc>=vm.program.size()||observer_next!=vm.program[pc])
     throw std::runtime_error("actual FIFO-to-NEXT accepted raw instruction differs from pinned source");
    raw_witnesses.push_back({pc,unsigned(core.end_retired?0:core.instruction_unit),vm.edge,bool(core.end_retired),observer_next});
   }
   if(root.ot_hdc_core_vector_weight_native_candidate__DOT__load){
    auto&actual=root.ot_hdc_core_vector_weight_native_candidate__DOT__fq[root.ot_hdc_core_vector_weight_native_candidate__DOT__fq_rd];
    for(unsigned w=0;w<32;w++)observer_next[w]=actual[w];observer_next_valid=true;
   }
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
  backend.core_edge(true);core.clk=front.clk=kernel.clk=sector.clk=1;core.eval();front.eval();kernel.eval();sector.eval();
  vm.commit_after_edge();for(auto&w:vm.writes)receiver.observe_write(w.address);
  receiver.store_after_edge();if(!receiver.writes.empty()&&receiver.writes.back().edge+1==receiver.edge){auto&w=receiver.writes.back();for(unsigned j=0;j<16;j++){vm.external_commit(w.address+j,w.data[j],"NATIVE_ATTN");effects.push_back({11,w.address+j,w.data[j],vm.edge,"NATIVE_ATTN"});}}
  if(core.fault||front.fault||kernel.fault||sector.fault)throw std::runtime_error("actual RTL fault rank "+std::to_string(rank));
 }
 void fall(){backend.core_edge(false);core.clk=front.clk=kernel.clk=sector.clk=0;core.eval();front.eval();kernel.eval();sector.eval();}
};
static void run_process(std::vector<std::string>args){std::vector<char*>v;for(auto&s:args)v.push_back(s.data());v.push_back(nullptr);pid_t p=fork();if(p<0)throw std::runtime_error("collective fork failed");if(!p){execv(v[0],v.data());_exit(127);}int status=0;if(waitpid(p,&status,0)!=p||!WIFEXITED(status)||WEXITSTATUS(status))throw std::runtime_error("actual production collective failed");}
static uint64_t collective(std::array<std::unique_ptr<Rank>,8>&r,const std::string&runtime,const std::string&exe,const fs::path&out){
 fs::create_directories(out);std::vector<std::string>args={"/usr/bin/python3",runtime,"--exe",exe,"--words","256","--out",(out/"actual").string(),"--ranks"};
 for(unsigned rank=0;rank<8;rank++){auto p=out/("partial"+std::to_string(rank)+".hex");std::ofstream f(p);for(unsigned w=0;w<256;w++){for(unsigned j=0;j<16;j++)f<<std::hex<<std::setfill('0')<<std::setw(8)<<r[rank]->vm.vm[16*w+15-j];f<<"\n";}f.close();args.push_back(p.string());}
 run_process(args);
 for(unsigned rank=0;rank<8;rank++){auto data=qwen_native::read_hex<16>((out/"actual"/("rank"+std::to_string(rank)+".hex")).string());if(data.size()!=256)throw std::runtime_error("actual collective returned incorrect word count");for(unsigned w=0;w<256;w++)for(unsigned j=0;j<16;j++)r[rank]->vm.external_commit(16*w+j,data[w][j],"ACTUAL_TP8_COLLECTIVE");}
 std::ifstream log(out/"actual"/"run.log");std::string text((std::istreambuf_iterator<char>(log)),std::istreambuf_iterator<char>());std::smatch match;
 if(!std::regex_search(text,match,std::regex("first=([0-9]+) last=([0-9]+)")))throw std::runtime_error("missing genuine collector cycle observations");
 uint64_t first=std::stoull(match[1]),last=std::stoull(match[2]);if(last<first)throw std::runtime_error("invalid genuine collector cycle range");
 return last-first+1;
}
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
  std::ofstream k(output/("rank"+std::to_string(rank)+"_KV.txt"));for(auto w:x.kv_commits)k<<w.address<<" "<<std::hex<<std::setfill('0')<<std::setw(8)<<w.value<<std::dec<<" "<<w.edge<<" "<<w.pc<<"\n";
  std::ofstream v(output/("rank"+std::to_string(rank)+"_VM_commits.txt"));for(auto w:x.vm.commits)v<<w.address<<" "<<std::hex<<std::setfill('0')<<std::setw(8)<<w.value<<std::dec<<" "<<w.edge<<" "<<w.port<<"\n";
  std::ofstream e(output/("rank"+std::to_string(rank)+"_operation_commits.txt"));for(auto w:x.effects)e<<w.pc<<" "<<w.address<<" "<<std::hex<<std::setfill('0')<<std::setw(8)<<w.value<<std::dec<<" "<<w.edge<<" "<<w.port<<"\n";
  std::ofstream s(output/("rank"+std::to_string(rank)+"_accepted_SU_descriptors.txt"));for(auto d:x.su_descriptors){s<<d.pc<<" "<<d.edge;for(auto value:d.values)s<<" "<<value;s<<"\n";}
 }
 std::ofstream cycles(output/"functional_cycles.json");cycles<<"{\"layer\":"<<layer.number<<",\"epoch\":"<<layer.epoch<<",\"core_begin\":"<<r[0]->layer_begin_edge<<",\"core_end\":"<<r[0]->backend.core_edges<<",\"core_cycles\":"<<r[0]->backend.core_edges-r[0]->layer_begin_edge<<",\"actual_isolated_collector_cycles\":"<<r[0]->collector_cycles<<",\"unified_clock_measurement\":false,\"production_rate_qualified\":false,\"errors\":"<<errors<<"}\n";
 return errors;
}
static void save_head(std::array<std::unique_ptr<Rank>,8>&r,const fs::path&output){
 fs::create_directories(output);std::ofstream local(output/"local_argmax.txt");
 for(unsigned rank=0;rank<8;rank++){
  auto&x=*r[rank];if(!x.core.done||x.vm.retired.size()!=1||x.rom_written!=0||x.kv_commits.size()!=0||unsigned(x.core.next_token)>=18992)throw std::runtime_error("invalid actual local head retirement");
  local<<rank<<" "<<unsigned(x.core.next_token)<<" "<<std::hex<<std::setfill('0')<<std::setw(8)<<x.core.next_val<<std::dec<<" "<<x.backend.core_edges-x.layer_begin_edge<<"\n";
  std::ofstream vm(output/("rank"+std::to_string(rank)+"_VM.hex"));for(auto v:x.vm.vm)vm<<std::hex<<std::setfill('0')<<std::setw(8)<<v<<"\n";
  std::ofstream commits(output/("rank"+std::to_string(rank)+"_operation_commits.txt"));for(auto w:x.effects)commits<<w.pc<<" "<<w.address<<" "<<std::hex<<std::setfill('0')<<std::setw(8)<<w.value<<std::dec<<" "<<w.edge<<" "<<w.port<<"\n";
  std::ofstream accepted(output/("rank"+std::to_string(rank)+"_accepted.txt"));for(auto op:x.vm.accepted)accepted<<op.global_pc<<" "<<op.unit<<" "<<op.edge<<"\n";
 }
}
int main(int argc,char**argv){try{
 if(argc!=7&&argc!=8&&argc!=9&&argc!=11)throw std::runtime_error("image program oracle collective_runtime collective_exe output [layer_plan [actual_initial_VM [head_image head_program]]] required");
 auto layers=argc>=8?read_plan(argv[7]):std::vector<Layer>{{0,17,255,argv[1],argv[2],argv[3]}};
 if(layers.front().number!=0&&argc<9)throw std::runtime_error("nonzero standalone layer needs explicit actual initial VM input");
 std::string initial_vm=argc>=9?argv[8]:std::string(argv[3])+"/vm_x_fp32.hex";
 VerilatedContext ctx;ctx.threads(1);std::array<std::unique_ptr<Rank>,8>r;for(unsigned rank=0;rank<8;rank++)r[rank]=std::make_unique<Rank>(ctx,rank,layers[0],initial_vm);
 uint64_t cn=553667,hn=512000;bool ch=false,hh=false;unsigned segment=0,layer_index=0;unsigned total_errors=0;bool running=false,finished=false,head=false;uint64_t restart=0;
 for(uint64_t events=0;uint64_t(events)<8000000ULL*(layers.size()+1)&&!finished;events++){
  bool core=cn<=hn;ctx.time(core?cn:hn);if(!core){hn+=512000;hh=!hh;for(auto&x:r)x->backend.hbm_edge(hh);continue;}cn+=416667;ch=!ch;
  if(!ch){for(auto&x:r)x->fall();continue;}
  bool launch=!running;for(auto&x:r)launch&=x->epoch_reserved&&x->backend.core_edges>=std::max(restart,x->start_edge);
  for(auto&x:r)x->low(launch);for(auto&x:r)x->rise();if(launch){running=true;std::cerr<<"segment "<<segment<<" launched core "<<r[0]->backend.core_edges<<"\n";}
  bool all_done=running;for(auto&x:r)all_done&=x->core.done;
  if(all_done){std::cerr<<"segment "<<segment<<" completed core "<<r[0]->backend.core_edges<<"\n";
   if(head){save_head(r,fs::path(argv[6])/"head");finished=true;break;}
   fs::create_directories(layer_output(layers[layer_index],argv[6],layers.size()));for(unsigned rank=0;rank<8;rank++){std::ofstream snap(layer_output(layers[layer_index],argv[6],layers.size())/("rank"+std::to_string(rank)+"_segment"+std::to_string(segment)+"_VM.hex"));for(auto bits:r[rank]->vm.vm)snap<<std::hex<<std::setfill('0')<<std::setw(8)<<bits<<"\n";}
   if(segment==2){
    total_errors+=save_layer(r,layers[layer_index],layer_output(layers[layer_index],argv[6],layers.size()));
    if(total_errors)throw std::runtime_error("actual layer output mismatch; refusing later bank transition");
    if(++layer_index==layers.size()){
     if(argc!=11){finished=true;break;}
     for(auto&x:r)x->switch_head(argv[9],argv[10]);head=true;running=false;restart=r[0]->backend.core_edges+2;continue;
    }
    for(auto&x:r)x->switch_layer(layers[layer_index]);segment=0;running=false;restart=r[0]->backend.core_edges+2;continue;
   }
   auto coll_cycles=collective(r,argv[4],argv[5],layer_output(layers[layer_index],argv[6],layers.size())/("collective"+std::to_string(segment)));for(auto&x:r)x->collector_cycles+=coll_cycles;
   ++segment;for(auto&x:r)x->vm.segment_base=segment==1?14:22;running=false;restart=r[0]->backend.core_edges+2;
  }
 }
 if(!finished)throw std::runtime_error("actual layer sequence timeout");
 std::cout<<"{\"scope\":\"ACTUAL_EIGHT_RANK_LAYER_SEQUENCE_FUNCTIONAL_CANDIDATE\",\"layer_instruction_issues_per_rank\":22,\"layer_END_retirements_per_rank\":3,\"expected_X_words\":32768,\"errors\":"<<total_errors<<",\"past_cache_policy\":\"declared_synthetic_FP8_history_written_through_actual_controllers\",\"current_KV_policy\":\"actual_core_SU_writes_only\",\"executed_layers\":"<<layers.size()<<",\"layer_transitions_proved\":"<<(layers.size()>1?"true":"false")<<",\"local_head_executed\":"<<(head?"true":"false")<<",\"global18bit_token_proved\":false,\"physical_VM_proved\":false,\"throughput_qualified\":false}\n";return total_errors?1:0;
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 2;}}
