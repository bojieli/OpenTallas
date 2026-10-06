// One released L20.attn.hc_pre_norm stage inside the actual selected ND2 parent.
// Lorentz owns generated graph, compilation, linkage and runtime. No fake RAM
// replies, accepted outputs, grants, checked-publication callbacks or force.
#include "Vtb_hbm_integrated_minimum_parent.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

using Row=std::array<uint32_t,32>;
static void require(bool ok,const std::string& text){if(!ok)throw std::runtime_error(text);}
template<class P> void zero(P& p){
 if constexpr(std::is_integral_v<P>)p=0;
 else for(size_t i=0;i<sizeof(P)/sizeof(uint32_t);++i)p[i]=0;
}
template<class P> unsigned capacity(const P&){return sizeof(P)*8;}
template<class P> uint32_t bits(const P& p,unsigned start,unsigned n){
 require(n<=32&&start+n<=capacity(p),"generated port width mismatch");
 uint32_t value=0;
 for(unsigned k=0;k<n;++k){unsigned i=start+k;
  if constexpr(std::is_integral_v<P>)value|=uint32_t((uint64_t(p)>>i)&1)<<k;
  else value|=((p[i/32]>>(i%32))&1U)<<k;
 }
 return value;
}
template<class P> void put(P& p,unsigned start,unsigned n,uint32_t value){
 require(n<=32&&start+n<=capacity(p),"generated port width mismatch");
 for(unsigned k=0;k<n;++k){unsigned i=start+k;
  if constexpr(std::is_integral_v<P>){auto mask=uint64_t(1)<<i;p=P((uint64_t(p)&~mask)|(((uint64_t(value)>>k)&1)<<i));}
  else {auto mask=uint32_t(1)<<(i%32);p[i/32]=(p[i/32]&~mask)|(((value>>k)&1U)<<(i%32));}
 }
}
// Full73 fields, never narrowed into a uint64_t or borrowed from a live signal.
constexpr uint32_t JOB=0x9234abcd,GEN=9,TOKEN=0x10001,POSITION=0xfffff;
template<class P> void frame(P& p,bool foreign=false){
 put(p,0,32,JOB);put(p,32,4,GEN);put(p,36,17,TOKEN^(foreign?0x10000:0));put(p,53,20,POSITION);
}
template<class P> bool owned(const P& p){return bits(p,0,32)==JOB&&bits(p,32,4)==GEN&&bits(p,36,17)==TOKEN&&bits(p,53,20)==POSITION;}
static std::vector<Row> hex(const std::filesystem::path& path,size_t count,unsigned width){
 std::ifstream f(path);require(bool(f),"missing retained input/gold: "+path.string());
 std::vector<Row> out;std::string s;
 while(f>>s){require(s.size()==width/4&&s.find_first_not_of("0123456789abcdefABCDEF")==std::string::npos,"invalid retained hex: "+path.string());Row r{};
  for(unsigned k=0;k<width/4;k+=8){unsigned n=std::min(8U,width/4-k);r[k/8]=std::stoul(s.substr(s.size()-k-n,n),nullptr,16);}out.push_back(r);
 }
 require(out.size()==count,"retained shape mismatch: "+path.string());return out;
}
struct Gold {
 std::vector<Row> y,c,e,q,cfg;
 explicit Gold(const std::filesystem::path& dir):y(hex(dir/"ey.mem",5120,32)),c(hex(dir/"eqc.mem",160,256)),e(hex(dir/"eqe.mem",160,16)),q(hex(dir/"eqy.mem",160,512)),cfg(hex(dir/"cfg.mem",6,32)){
  for(auto r:e)require((r[0]&0xffff)==((r[0]&0x3ff)|((r[0]&0x200)?0xfc00:0)),"noncanonical signed16 to signed10 scale");
 }
 Row row(unsigned i)const{Row r{};
  if(i<160){for(unsigned k=0;k<32;++k)r[k]=y[i*32+k][0];}
  else{unsigned b=(i-160)/3,t=(i-160)%3;
   if(t==0){for(unsigned k=0;k<8;++k){r[k]=c[2*b][k];r[8+k]=c[2*b+1][k];}}
   if(t==1)r[0]=(e[2*b][0]&0x3ff)|((e[2*b+1][0]&0x3ff)<<10);
   if(t==2){for(unsigned k=0;k<16;++k){r[k]=q[2*b][k];r[16+k]=q[2*b+1][k];}}
  }return r;
 }
};
struct Sim {
 VerilatedContext context;Vtb_hbm_integrated_minimum_parent dut{&context,"DUT"};
 uint64_t cycles=0;std::array<uint64_t,4> next{},half{};
 // Source-derived mechanism-progress bound, not a build/runtime wall deadline:
 // norm drain pipeline + HBM refresh/row/controller service + native SRAM
 // depth/256-lane scan/protected descriptor + parent reset/CDC/command drain.
 static constexpr unsigned ENGINE=7+(5+3*6+1)+(5+7*6+3*6)+7*6+9+8+6+(1+3*(3*5+6))+9+80+2*(5+1)+1+18+8+2;
 static constexpr unsigned STALL=ENGINE+(350000+10000+10000+19375+12500+16250+28125+1024+832)/833+512+4*256+2*72+256+64;
 std::string phase="reset";
 // Formatter watchdog includes the unchanged N96/P64/PF16 merger's eight
 // radix passes and filter pass, whose arithmetic can progress without I/O.
 std::function<void()> preedge_observer;
 Sim(int argc,char**argv){context.commandArgs(argc,argv);
  #include "hbm_integrated_minimum_parent_inputs.inc"
  // No W2 work is offered. Quiet is derived from this fixture's empty caller
  // inventory; no W2 installed weights or output extents are asserted.
  dut.w2_quiet=3;
  int precision=context.timeprecision();require(precision<=-12&&precision>=-15,"unsupported generated clock precision");
  uint64_t fs_per_tick=1;for(int p=-15;p<precision;++p)fs_per_tick*=10;
  const std::array<uint64_t,4> fs{2000000,416667,500000,450000};
  for(unsigned i=0;i<4;++i){half[i]=(fs[i]+fs_per_tick/2)/fs_per_tick;next[i]=half[i];}
  dut.eval();
 }
 bool event(){uint64_t at=*std::min_element(next.begin(),next.end());
  if(dut.eventsPending())at=std::min(at,dut.nextTimeSlot());
  require(at>=context.time(),"nonmonotone generated event");context.timeInc(at-context.time());
  bool rise=next[1]==at&&!dut.clk_sm;
  if(rise&&preedge_observer)preedge_observer();
  if(next[0]==at){dut.clk_host=!dut.clk_host;next[0]+=half[0];}
  if(next[1]==at){dut.clk_sm=!dut.clk_sm;next[1]+=half[1];}
  if(next[2]==at){dut.clk_mem=!dut.clk_mem;next[2]+=half[2];}
  if(next[3]==at){dut.clk_link=!dut.clk_link;next[3]+=half[3];}
  dut.eval();if(rise)++cycles;
  require(!context.gotFinish(),"RTL finished before fixture terminal");return rise;
 }
 void sm(){while(!event()){};}
 void neg(){while(!dut.clk_sm)event();while(dut.clk_sm)event();}
 void edges(unsigned n){while(n--)sm();}
 void settle(){dut.eval();}
 uint64_t progress()const{return uint64_t(dut.fixture_cp_requests)+dut.fixture_cp_returns+dut.fixture_ACKs+dut.fixture_bind_accepts+dut.fixture_enroll_accepts+dut.fixture_read_accepts+dut.fixture_rsp_accepts+dut.fixture_retire_accepts+dut.fixture_db_accepts+dut.fixture_cpl_accepts+dut.fixture_sfu_enroll_accepts+dut.fixture_sfu_cp_requests+dut.fixture_sfu_cp_returns+dut.fixture_sfu_ACKs+dut.fixture_sfu_TXs+dut.fixture_sfu_releases+dut.fixture_formatter_source_accepts+dut.fixture_formatter_source_ACKs+dut.fixture_formatter_mem_requests+dut.fixture_formatter_mem_returns+dut.fixture_formatter_desc_accepts+dut.fixture_formatter_begin_accepts+dut.fixture_formatter_record_accepts+dut.fixture_formatter_go_accepts+dut.fixture_formatter_pairs+dut.fixture_formatter_reservations+dut.fixture_formatter_reverses+dut.fixture_formatter_captured_words+dut.fixture_formatter_checked_sink_words;}
 void healthy(){require(!dut.sys_fault&&!dut.norm_fault&&!dut.sfu_fault&&!dut.sfu_vm_fault&&!dut.fixture_observer_fault&&!dut.fixture_formatter_fault&&!(dut.preinstall_fault&1),"actual parent/provider fault phase="+phase);}
 template<class F>void wait(F ready){unsigned idle=0;auto old=progress();settle();while(!ready()){
  sm();healthy();auto now=progress();idle=(now!=old)?0:idle+1;old=now;
  if(idle>STALL+(dut.fixture_formatter_enable?(8*(96*512/64+7)+96*512/16+9):0)){std::cerr<<"BLOCKED phase="<<phase<<" cycles="<<cycles<<" cp="<<dut.fixture_cp_requests<<"/"<<dut.fixture_cp_returns<<" ACK="<<dut.fixture_ACKs<<" enroll_r="<<unsigned(dut.norm_enroll_r)<<" stage_retained="<<unsigned(dut.norm_retained)<<" root_retained="<<unsigned(dut.sfu_vm_retained)<<" db_rdy="<<unsigned(dut.db_rdy)<<" cpl_v="<<unsigned(dut.cpl_v)<<"\n";throw std::runtime_error("no accepted mechanism progress; source-owner blocker, no qualification");}
 }}
 void held(){healthy();require((dut.norm_retained&1)&&(dut.sfu_vm_retained&1)&&owned(dut.norm_held_frame)&&owned(dut.sfu_vm_held_frame)&&!(dut.cpl_v&1),"held actual parent owner/debt changed");}
 void finish(){dut.final();}
};
#include "hbm_integrated_sfu_continuation.inc"
#include "hbm_integrated_formatter_continuation.inc"
int main(int argc,char**argv){try{
 std::filesystem::path dir,formatter_dir;bool wrong_release=false,sfu_next=false,continue_sfu=false,continue_formatter=false,formatter_next=false;
 for(int i=1;i<argc;++i){std::string a=argv[i];if(a.rfind("+DIR=",0)==0)dir=a.substr(5);if(a=="+WRONG_RELEASE")wrong_release=true;if(a=="+SFU_NEXT")sfu_next=true;if(a=="+CONTINUE_SFU")continue_sfu=true;if(a=="+CONTINUE_FORMATTER")continue_formatter=true;if(a=="+FORMATTER_NEXT")formatter_next=true;if(a.rfind("+FORMATTER_DIR=",0)==0)formatter_dir=a.substr(15);
  require(a.rfind("+gpu_sys_mem_prefix=",0)!=0,"shared prefix aliases both dies; use separate die0/die1 images");}
 require(!(wrong_release&&(sfu_next||continue_sfu||continue_formatter||formatter_next)),"poisoned norm cannot continue SFU");
 require(!dir.empty(),"+DIR=retained_stage_directory required");require(std::filesystem::exists("fixture_manifest.json"),"verified fixture preparation required");Gold gold(dir);
 // Default real parent memsys_adapter prefixes; generated HBM scheduler loads
 // these files itself. Images are prepared separately; C++ never writes SRAM.
 for(auto name:{"die0_p0.hex","die0_p1.hex","die1_p0.hex","die1_p1.hex"})require(std::filesystem::exists(name),std::string("missing actual provider image ")+name);
 Sim s(argc,argv);auto& d=s.dut;
 s.edges(32);s.neg();d.por_n=1;s.phase="actual reset domains";s.wait([&]{return d.rst_sm_n&&(d.db_rdy&1);});
 if(continue_formatter||formatter_next)require(!formatter_dir.empty(),"actual +FORMATTER_DIR=prepared_installed_fixture required");
 if(formatter_next){FormatterFixture f(formatter_dir);run_formatter_source_next(s,f);s.finish();return 0;}
 if(sfu_next){run_native_sfu_next(s,dir);if(continue_formatter){FormatterFixture f(formatter_dir);run_formatter_source_next(s,f);}s.finish();return 0;}
 // Real END-only CP context from Gibbs caller recipe; status2 is mandatory.
 // There is no mathematical RESULT producer in this one-stage session.
 s.neg();d.cmd_we=1;put(d.cmd_addr,0,8,0);put(d.cmd_wdata,0,32,0);put(d.cmd_wdata,32,32,0x20000000);s.sm();s.neg();d.cmd_we=0;
 put(d.db_token,0,17,TOKEN);put(d.db_pos,0,20,POSITION);put(d.db_job,0,32,JOB);put(d.db_generation,0,4,GEN);
 d.db_v=1;s.phase="accepted CP session";s.wait([&]{return d.fixture_db_accepts==1;});s.neg();d.db_v=0;
 // Loader/preloaded CP aperture is owned exclusively by this one die0 stage.
 // The acknowledged native root bind is the actual output allocation.
 frame(d.sfu_vm_bind_frame);put(d.sfu_vm_bind_rank,0,7,41);put(d.sfu_vm_bind_base,0,32,3584);put(d.sfu_vm_bind_span,0,32,12800);
 d.sfu_vm_bind_v=1;s.phase="actual native allocation";s.wait([&]{return d.fixture_bind_accepts==1;});s.neg();d.sfu_vm_bind_v=0;
 require((d.sfu_vm_retained&1)&&owned(d.sfu_vm_held_frame),"output allocation not accepted");
 frame(d.norm_allocation_frame);d.norm_allocation_valid=1;
 put(d.norm_xbase,0,24,0);put(d.norm_gain_base,0,24,20480);put(d.norm_ybase,0,24,3584);
 for(unsigned i=0;i<4;++i)put(d.norm_post_pre,i*32,32,gold.cfg[i][0]);
 put(d.norm_n_f,0,32,gold.cfg[4][0]);put(d.norm_eps,0,32,gold.cfg[5][0]);
 // Descriptor fields label the one actual native call, not a fake SM program.
 put(d.norm_enroll_pc,0,32,0);put(d.norm_enroll_op,0,32,0);put(d.norm_enroll_source,0,16,0);put(d.norm_enroll_count,0,9,1);
 // High TOKEN bit is the negative control, while bound allocation is held.
 frame(d.norm_enroll_frame,true);d.norm_enroll_v=1;s.phase="foreign full73 enrollment refusal";s.settle();
 for(unsigned i=0;i<7;++i){require(!(d.norm_enroll_r&1),"foreign full73 ready");s.sm();s.healthy();require(d.fixture_enroll_accepts==0&&!(d.norm_retained&1)&&(d.sfu_vm_retained&1)&&owned(d.sfu_vm_held_frame),"foreign full73 accepted or allocation lost");}
 s.neg();d.norm_enroll_v=0;frame(d.norm_enroll_frame);d.norm_enroll_v=1;s.phase="correct norm enrollment (pinned line855 circularity if refused)";
 s.wait([&]{return d.fixture_enroll_accepts==1;});s.neg();d.norm_enroll_v=0;
 frame(d.norm_publication_owner);s.phase="actual engine/provider publication";s.wait([&]{return (d.norm_publication_v&1)!=0;});s.held();
 require(d.fixture_cp_requests==25600&&d.fixture_cp_returns==25600&&d.fixture_ACKs==400&&d.fixture_final_ACK_addr==16352,"actual CP/400 checked ACK accounting incomplete");
 require(bits(d.norm_reserve_events,0,16)==160,"actual norm input/reservation shape");
 // Read all400 actual same-root rows, including code/scales/BF16 and padding.
 frame(d.sfu_vm_index_read_frame);put(d.sfu_vm_index_read_rank,0,7,41);put(d.sfu_vm_index_read_words,0,6,32);
 for(unsigned row=0;row<400;++row){s.neg();put(d.sfu_vm_index_read_addr,0,32,3584+row*32);put(d.sfu_vm_index_read_tag,0,8,row&255);
  d.sfu_vm_index_read_v=1;auto count=d.fixture_read_accepts;s.phase="same-bank read request row="+std::to_string(row);
  s.wait([&]{return d.fixture_read_accepts==count+1;});s.neg();d.sfu_vm_index_read_v=0;
  s.wait([&]{return (d.sfu_vm_index_rsp_v&1)!=0;});Row actual{};
  for(unsigned k=0;k<32;++k)actual[k]=bits(d.sfu_vm_index_rsp_data,k*32,32);
  for(unsigned hold=0;hold<3;++hold){s.held();require((d.sfu_vm_index_rsp_v&1)&&owned(d.sfu_vm_index_rsp_frame)&&bits(d.sfu_vm_index_rsp_tag,0,8)==(row&255)&&bits(d.sfu_vm_index_rsp_rank,0,7)==41,"held protected read response identity");
   for(unsigned k=0;k<32;++k)require(bits(d.sfu_vm_index_rsp_data,k*32,32)==actual[k],"held protected read data changed");s.sm();}
  auto expected=gold.row(row);for(unsigned k=0;k<32;++k)require(actual[k]==expected[k],"released stage golden mismatch word="+std::to_string(3584+row*32+k));
  s.neg();d.sfu_vm_index_rsp_r=1;count=d.fixture_rsp_accepts;s.wait([&]{return d.fixture_rsp_accepts==count+1;});s.neg();d.sfu_vm_index_rsp_r=0;
 }
 require(d.fixture_read_accepts==400&&d.fixture_rsp_accepts==400,"not all protected rows accepted");
 s.neg();d.cp_reset_req=1;s.phase="warm held caller lease";
 for(unsigned i=0;i<7;++i){s.sm();s.held();require(!(d.cp_reset_ack&1)&&!(d.norm_warm_ack&1)&&!(d.sfu_vm_warm_ack&1)&&(d.norm_publication_v&1),"warm reset freed held caller debt");}
 if(wrong_release){s.neg();frame(d.norm_publication_owner,true);d.norm_publication_r=1;s.edges(7);
  require((d.norm_fault&1)&&(d.norm_retained&1)&&(d.sfu_vm_retained&1)&&!(d.norm_publication_v&1)&&!(d.cp_reset_ack&1)&&d.fixture_cpl_accepts==0,"foreign full73 release not refused with retained debt");
  std::cout<<"PARENT_STAGE_WRONG_FULL73_RELEASE_REFUSED actual_golden_rows=400 ACK=400 held_owner=1 token_qualified=0 physical_qualified=0\n";s.finish();return 0;}
 s.neg();d.norm_publication_r=1;s.phase="real stage reverse release";s.wait([&]{return !(d.norm_retained&1);});s.neg();d.norm_publication_r=0;
 frame(d.sfu_vm_retire_frame);d.sfu_vm_retire_v=1;s.phase="actual root retirement";s.wait([&]{return d.fixture_retire_accepts==1;});s.neg();d.sfu_vm_retire_v=0;
 s.phase="actual CP completion after drains";s.wait([&]{return (d.cpl_v&1)!=0;});
 require(bits(d.cpl_data,37,4)==2&&bits(d.cpl_data,17,20)==POSITION&&bits(d.cpl_data,73,4)==GEN&&bits(d.cpl_data,77,32)==JOB,"END-only actual completion metadata/status mismatch");
 require(!(d.sfu_vm_retained&1)&&!(d.norm_retained&1),"completion before owners drained");
 s.neg();d.cpl_rdy=1;s.wait([&]{return d.fixture_cpl_accepts==1;});s.neg();d.cpl_rdy=0;
 s.phase="joint warm reset acknowledgment";s.wait([&]{return (d.cp_reset_ack&1)&&(d.norm_warm_ack&1)&&(d.sfu_vm_warm_ack&1);});
 if(continue_sfu){run_native_sfu_next(s,dir);if(continue_formatter){FormatterFixture f(formatter_dir);run_formatter_source_next(s,f);}s.finish();return 0;}
 if(continue_formatter){FormatterFixture f(formatter_dir);run_formatter_source_next(s,f);s.finish();return 0;}
 std::cout<<"PARENT_ONE_STAGE_PASS stage=L20.attn.hc_pre_norm actual_CP=25600/25600 ACK=400 readback_words=12800 lastWORD=16383 full73_refusal=1 warm_held=1 cpl_status=2 token_qualified=0 SFU_execution_covered=0 formatter_execution_covered=0 physical_qualified=0 cycles="<<s.cycles<<"\n";s.finish();return 0;
 }catch(const std::exception& e){std::cerr<<"PARENT_STAGE_FAIL "<<e.what()<<"\n";return 1;}}
