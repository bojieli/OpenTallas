// Candidate executed-layer harness. No fixture QR/current-KV writes exist here.
// Expected vectors are observers; all collective inputs come from actual VM.
#include "Vot_hdc_core_vector_weight_native_candidate.h"
#include "Vot_qwen_tp8_native_services_frontend.h"
#include "Vot_qwen_tp8_attention_service.h"
#include "Vot_qwen_tp8_kv_sector_adapter.h"
#include "rom_vm_adapter.hpp"
#include "services_vm_adapter.hpp"
#include "kernel_physical_rows.hpp"
#include <filesystem>
#include <iostream>
#include <iomanip>
#include <sys/wait.h>
#include <unistd.h>
using namespace qwen_native_services;
using namespace qwen_actual_phy;
namespace fs=std::filesystem;
struct Rank {
 unsigned rank;VerilatedContext&ctx;
 qwen_native::RomVmAdapter vm;
 RowBackend backend;
 Vot_hdc_core_vector_weight_native_candidate core;
 Vot_qwen_tp8_native_services_frontend front;
 Vot_qwen_tp8_attention_service kernel;
 Vot_qwen_tp8_kv_sector_adapter sector;
 VmReceiver receiver;KernelRows reads;SectorWrites writes;
 struct Effect{unsigned pc,address,value;uint64_t edge;std::string port;};std::vector<Effect> effects;
 struct KvCommit{unsigned pc,address,value;uint64_t edge;};std::vector<KvCommit> kv_commits;
 int su_owner=-1,rom_owner=-1;unsigned rom_written=0,rom_expected=0;
 bool epoch_reserved=false;uint64_t start_edge=0;
 Rank(VerilatedContext&context,unsigned r,const std::string& image,const std::string& program,const std::string& oracle)
 :rank(r),ctx(context),vm(image+"/die"+std::to_string(r),program+"/die"+std::to_string(r)+"/program.hex",oracle+"/vm_x_fp32.hex"),
 backend(context,255,"rank"+std::to_string(r)+"_pc_"),
 core(&context,("rank"+std::to_string(r)+"_core").c_str()),front(&context,("rank"+std::to_string(r)+"_front").c_str()),
 kernel(&context,("rank"+std::to_string(r)+"_kernel").c_str()),sector(&context,("rank"+std::to_string(r)+"_sector").c_str()),
 receiver(vm.vm),reads(backend),writes(backend){
  core.clk=front.clk=kernel.clk=sector.clk=0;core.rst_n=front.rst_n=kernel.rst_n=sector.rst_n=0;
  core.start=0;core.token=0;core.pos=255;front.epoch=17;front.layer=0;front.pos=255;front.epoch_begin=0;front.fused_program_capability=1;
  for(unsigned kind=0;kind<2;kind++){
   std::ifstream f(oracle+"/die"+std::to_string(r)+"/prior_"+(kind?"V":"K")+"_fp8.bin",std::ios::binary);
   if(!f)throw std::runtime_error("missing declared prior cache");
   for(unsigned t=0;t<255;t++)for(unsigned q=0;q<4;q++){Quarter bytes{};for(unsigned j=0;j<32;j++){int b=f.get();if(b<0)throw std::runtime_error("short declared prior cache");bytes[j/4]|=unsigned(b)<<(8*(j%4));}backend.enqueue_prior_quarter_via_actual_controller({{17,0,t,kind},q},bytes);}
   if(f.get()!=EOF)throw std::runtime_error("extra prior cache bytes");
  }
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
  if(!epoch_reserved&&backend.write_acks==2040&&front.epoch_ready){front.epoch_begin=1;receiver.reserve(17,0);epoch_reserved=true;start_edge=backend.core_edges+4;}
  if(!epoch_reserved){WriteAck a;while(backend.pop_write_ack(a)){}front.store_ack_v=0;sector.ack_v=0;}
  else writes.prepare_acks(sector,front);
  receiver.drive(front);reads.drive(kernel);vm.drive_responses(core);
  // Every model eval repeats at least twice. Check all cross-model admission,
  // valid and payload faces; preserve same-edge nonblocking read semantics.
  auto face=[&](){std::vector<uint32_t>v={unsigned(core.native_go),unsigned(core.su_issue),unsigned(core.su_descriptor_reserved),unsigned(front.native_ready),unsigned(front.native_idle),unsigned(front.kv_admit_ready),unsigned(front.row_v),unsigned(front.row_ready),unsigned(sector.row_ready),unsigned(kernel.result_valid),unsigned(kernel.q_ready)};for(unsigned j=0;j<32;j++)v.push_back(front.row_data[j]);for(unsigned j=0;j<37;j++)v.push_back(sector.commands[j]);return v;};
  bool stable=false;for(unsigned n=0;n<24;n++){auto before=face();connect_core();core.eval();connect_core();SectorWrites::connect(sector,front);sector.eval();settle(front,kernel);SectorWrites::connect(sector,front);sector.eval();connect_core();core.eval();if(n>0&&before==face()){stable=true;break;}}
  if(!stable)throw std::runtime_error("actual core/frontend interfaces did not settle");
  vm.snapshot_edge(core);receiver.sample(front);writes.sample(sector);reads.sample(kernel);
  // Sample the old owner's registered write faces BEFORE accepting a new
  // descriptor on this edge. Ownership is never taken from fetch or NEXT.
  for(auto&w:vm.writes){int owner=(w.port=="SU"||w.port=="REDUCER")?su_owner:rom_owner;if(owner<0)throw std::runtime_error("unowned actual VM commit");effects.push_back({unsigned(owner),w.address,w.value,w.edge,w.port});if(w.port=="ME")++rom_written;}
  for(unsigned lane=0;lane<64;lane++)if(core.kv_we&(uint64_t(1)<<lane)){if(su_owner<0)throw std::runtime_error("unowned actual KV commit");kv_commits.push_back({unsigned(su_owner),get_bits(core.kv_waddr,24*lane,24),core.kv_wdata[lane],backend.core_edges});}
  if(core.instruction_issue){unsigned pc=vm.segment_base+core.instruction_pc;
   if(core.instruction_unit==2){if(!core.su_is_idle)throw std::runtime_error("SU owner changed before actual idle/drain");su_owner=pc;}
   else if(core.instruction_unit==1&&pc!=11){if(rom_owner>=0&&rom_written!=rom_expected)throw std::runtime_error("ROM owner changed before exact old output drain");rom_owner=pc;rom_written=0;rom_expected=pc==1?768:pc==16?3072:4096;}
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
static void collective(std::array<std::unique_ptr<Rank>,8>&r,const std::string&runtime,const std::string&exe,const fs::path&out){
 fs::create_directories(out);std::vector<std::string>args={"/usr/bin/python3",runtime,"--exe",exe,"--words","256","--out",(out/"actual").string(),"--ranks"};
 for(unsigned rank=0;rank<8;rank++){auto p=out/("partial"+std::to_string(rank)+".hex");std::ofstream f(p);for(unsigned w=0;w<256;w++){for(unsigned j=0;j<16;j++)f<<std::hex<<std::setfill('0')<<std::setw(8)<<r[rank]->vm.vm[16*w+15-j];f<<"\n";}f.close();args.push_back(p.string());}
 run_process(args);
 for(unsigned rank=0;rank<8;rank++){auto data=qwen_native::read_hex<16>((out/"actual"/("rank"+std::to_string(rank)+".hex")).string());if(data.size()!=256)throw std::runtime_error("actual collective returned incorrect word count");for(unsigned w=0;w<256;w++)for(unsigned j=0;j<16;j++)r[rank]->vm.external_commit(16*w+j,data[w][j],"ACTUAL_TP8_COLLECTIVE");}
}
int main(int argc,char**argv){try{
 if(argc!=7)throw std::runtime_error("image fused_program production_oracle collective_runtime collective_exe output required");
 VerilatedContext ctx;ctx.threads(1);std::array<std::unique_ptr<Rank>,8>r;for(unsigned rank=0;rank<8;rank++)r[rank]=std::make_unique<Rank>(ctx,rank,argv[1],argv[2],argv[3]);
 uint64_t cn=553667,hn=512000;bool ch=false,hh=false;unsigned segment=0;bool running=false,finished=false;uint64_t restart=0;
 for(unsigned events=0;events<8000000&&!finished;events++){
  bool core=cn<=hn;ctx.time(core?cn:hn);if(!core){hn+=512000;hh=!hh;for(auto&x:r)x->backend.hbm_edge(hh);continue;}cn+=416667;ch=!ch;
  if(!ch){for(auto&x:r)x->fall();continue;}
  bool launch=!running;for(auto&x:r)launch&=x->epoch_reserved&&x->backend.core_edges>=std::max(restart,x->start_edge);
  for(auto&x:r)x->low(launch);for(auto&x:r)x->rise();if(launch){running=true;std::cerr<<"segment "<<segment<<" launched core "<<r[0]->backend.core_edges<<"\n";}
  bool all_done=running;for(auto&x:r)all_done&=x->core.done;
  if(all_done){std::cerr<<"segment "<<segment<<" completed core "<<r[0]->backend.core_edges<<"\n";
   fs::create_directories(argv[6]);for(unsigned rank=0;rank<8;rank++){std::ofstream snap(fs::path(argv[6])/("rank"+std::to_string(rank)+"_segment"+std::to_string(segment)+"_VM.hex"));for(auto bits:r[rank]->vm.vm)snap<<std::hex<<std::setfill('0')<<std::setw(8)<<bits<<"\n";}
   if(segment==2){finished=true;break;}
   collective(r,argv[4],argv[5],fs::path(argv[6])/("collective"+std::to_string(segment)));
   ++segment;for(auto&x:r)x->vm.segment_base=segment==1?14:22;running=false;restart=r[0]->backend.core_edges+2;
  }
 }
 if(!finished)throw std::runtime_error("actual layer timeout");unsigned errors=0;
 fs::create_directories(argv[6]);for(unsigned rank=0;rank<8;rank++){
  auto&x=*r[rank];auto gold=qwen_native::read_hex<1>(std::string(argv[3])+"/die"+std::to_string(rank)+"/X_final_fp32.hex");if(gold.size()!=4096)throw std::runtime_error("final X observer dimensions");
  for(unsigned j=0;j<4096;j++)errors+=x.vm.vm[4096+j]!=gold[j][0];
  if(x.vm.accepted.size()!=22||x.vm.retired!=std::vector<unsigned>{13,21,24}||x.receiver.commit_acks!=32||x.writes.committed!=8||!x.reads.drained()||!x.writes.drained())throw std::runtime_error("missing executed layer effects rank "+std::to_string(rank));
  std::ofstream f(fs::path(argv[6])/("rank"+std::to_string(rank)+"_VM.hex"));for(auto bits:x.vm.vm)f<<std::hex<<std::setfill('0')<<std::setw(8)<<bits<<"\n";
  std::ofstream a(fs::path(argv[6])/("rank"+std::to_string(rank)+"_accepted.txt"));for(auto op:x.vm.accepted)a<<op.global_pc<<" "<<op.unit<<" "<<op.edge<<"\n";
  std::ofstream bits(fs::path(argv[6])/("rank"+std::to_string(rank)+"_accepted_source_words.hex"));for(auto op:x.vm.accepted){for(unsigned word=0;word<32;word++)bits<<std::hex<<std::setfill('0')<<std::setw(8)<<op.instruction[31-word];bits<<"\n";}
  std::ofstream k(fs::path(argv[6])/("rank"+std::to_string(rank)+"_KV.txt"));for(auto w:x.kv_commits)k<<w.address<<" "<<std::hex<<std::setfill('0')<<std::setw(8)<<w.value<<std::dec<<" "<<w.edge<<" "<<w.pc<<"\n";
  std::ofstream v(fs::path(argv[6])/("rank"+std::to_string(rank)+"_VM_commits.txt"));for(auto w:x.vm.commits)v<<w.address<<" "<<std::hex<<std::setfill('0')<<std::setw(8)<<w.value<<std::dec<<" "<<w.edge<<" "<<w.port<<"\n";
  std::ofstream e(fs::path(argv[6])/("rank"+std::to_string(rank)+"_operation_commits.txt"));for(auto w:x.effects)e<<w.pc<<" "<<w.address<<" "<<std::hex<<std::setfill('0')<<std::setw(8)<<w.value<<std::dec<<" "<<w.edge<<" "<<w.port<<"\n";
 }
 std::cout<<"{\"scope\":\"ACTUAL_EIGHT_RANK_LAYER0_FUNCTIONAL_CANDIDATE\",\"instruction_issues_per_rank\":22,\"END_retirements_per_rank\":3,\"expected_X_words\":32768,\"errors\":"<<errors<<",\"past_cache_policy\":\"declared_synthetic_FP8_history_written_through_actual_controllers\",\"current_KV_policy\":\"actual_core_SU_writes_only\",\"layer_transitions_proved\":false,\"physical_VM_proved\":false,\"throughput_qualified\":false}\n";return errors?1:0;
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<"\n";return 2;}}
