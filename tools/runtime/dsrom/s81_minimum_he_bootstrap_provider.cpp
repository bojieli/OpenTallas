#include "s81_native_he_bootstrap_source.hpp"
#include <s81_minimum_prefix_io.hpp>
#include <fstream>
#include <sstream>
#include <unordered_map>
#include <cstdlib>
#include <unistd.h>
#include <sys/wait.h>

namespace {
using namespace dsrom_s81_minimum;
void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
// No shell, no interpolation: verify the enrolled immutable raw weight image.
std::string file_sha(const std::string& path) {
 int fd[2];require(pipe(fd)==0,"HE source hash pipe failed");
 const auto child=fork();require(child>=0,"HE source hash child failed");
 if(!child){close(fd[0]);dup2(fd[1],STDOUT_FILENO);close(fd[1]);
  execlp("sha256sum","sha256sum","--",path.c_str(),nullptr);_exit(127);}
 close(fd[1]);std::string result;char bytes[256];ssize_t count;
 while((count=read(fd[0],bytes,sizeof bytes))>0)result.append(bytes,count);
 close(fd[0]);int status=0;waitpid(child,&status,0);
 require(WIFEXITED(status)&&WEXITSTATUS(status)==0&&result.size()>=64,"HE image SHA failed");
 return result.substr(0,64);
}
struct WeightImage {
 std::vector<std::array<uint32_t,8>> words;
 explicit WeightImage(const std::string& dir):words(61440) {
  // Parent source emitter enrolls the exact bytes; no missing/zero defaults.
  std::ifstream meta(dir+"/hbank.source");std::string revision,tensor,shape,layout,pin;
  std::getline(meta,revision);std::getline(meta,tensor);std::getline(meta,shape);
  std::getline(meta,layout);std::getline(meta,pin);
  require(revision=="dba1be0a40aa45a94ad051997016db3960a90277"&&
          tensor=="layers.0.hc_attn_fn"&&shape=="F32 24 20480"&&
          layout=="HHW8 bankline=(wbase+row*320+run)*8+term lane=chunk"&&
          pin.size()==64,"actual source HE image provenance required");
  const auto path=dir+"/hbank.hex";
  require(file_sha(path)==pin,"actual HE image changed");
  std::ifstream file(path);require(bool(file),"actual HE bank image absent");
  std::vector<bool> seen(61440);std::string line;uint64_t address=0;
  while(std::getline(file,line)) {
   if(line.empty())continue;
   if(line[0]=='@'){address=std::stoull(line.substr(1),nullptr,16);continue;}
   require(line.size()==64,"HE bank word must contain eight raw FP32 lanes");
   if(address<words.size()) {
    require(!seen[address],"duplicate HE weight bank address");seen[address]=true;
    for(unsigned lane=0;lane<8;lane++)words[address][lane]=std::stoul(line.substr(56-8*lane,8),nullptr,16);
   }
   ++address;
  }
  require(std::all_of(seen.begin(),seen.end(),[](bool v){return v;}),"incomplete actual L0 HE image");
 }
};
struct Source {
 DsromS81MinimumRuntime& runtime;uint64_t identity;PrefixPublication& publication;
 DsromS81MinimumSourceIo io;DsromS81MinimumSourceTags tags;
 DsromS81MinimumOperandSpan<256> h_span;
 DsromS81MinimumPrefixOutputBatch output_batch;
 WeightImage weights;
 std::array<uint32_t,20480> H{};unsigned H_count=0;
 std::array<uint32_t,64> w_delay{};std::array<uint32_t,8> x_delay{};
 struct Write {S81EmbeddingOutput out{};bool offered=false;};
 std::unordered_map<uint32_t,Write> held;
 bool stopped=false;
 Source(DsromS81MinimumRuntime& r,uint64_t id,PrefixPublication& p,DsromS81MinimumSourceIo i,DsromS81MinimumSourceTags t,
        const std::string& dir):runtime(r),identity(id),publication(p),io(std::move(i)),tags(std::move(t)),
        h_span(id,io),output_batch(r,id,p,io,tags),weights(dir) {
  require(id<(1ull<<47)&&io.read_word&&io.span_lease&&io.offer&&io.visible&&tags.record,
          "actual same-VM SourceIo and reserved SourceTags required");
 }
 bool offer(unsigned producer,uint32_t address,uint32_t bits) {
  auto found=held.find(address);
  if(found==held.end()) {
   Write w;w.out.vm_valid=1;w.out.vm_identity=identity;w.out.vm_address=address;w.out.vm_data[0]=bits;
   // Reserve immutable command first; neither call acknowledges acceptance.
   output_batch.capture(producer,w.out,1,true);
   found=held.emplace(address,w).first;
  }
  require(found->second.out.vm_data[0]==bits,"native scalar changed while held");
  if(!found->second.offered)found->second.offered=output_batch.progress();
  return found->second.offered;
 }
 bool visible(uint32_t address,uint32_t bits) {
  auto found=held.find(address);require(found!=held.end()&&found->second.out.vm_data[0]==bits,
                                       "visibility lacks immutable actual native scalar");
  // progress() already consumed the canonical same-batch visibility predicate.
  // Keep its completion plus actual scalar publication; do not poll twice or
  // manufacture an acceptance/ACK from the retained software command.
  return found->second.offered&&publication.source_span_lease(identity,address,1);
 }
 std::optional<std::array<uint32_t,256>> vector(uint64_t id,uint32_t base) {
  require(id==identity&&!(base&255)&&base<20480,"native H vector coordinate changed");
  if(!io.span_lease(id,base,256))return std::nullopt;
  require(H_count==base,"changed pending actual H source span");
  auto raw=h_span.poll(id,base);
  if(!raw)return std::nullopt;
  std::copy(raw->begin(),raw->end(),H.begin()+base);H_count+=256;
  return raw;
 }
 bool inputs(const DsromS81PrefixOperation& op) {
  require(op.unit==5&&op.index==1&&op.instruction==dsrom_s81_l0_prefix_operations()[1].instruction,
          "HE provider only enrolls literal selected L0I1");
  return H_count==20480&&publication.complete(PrefixPublication::SSX)&&
         publication.complete(PrefixPublication::PF)&&io.span_lease(identity,0,20480);
 }
 void memory(uint64_t id,const S81NativeHeBootstrapOutput& out,S81NativeHeBootstrapInput& in) {
  require(id==identity,"HE memory context changed");
  std::copy(w_delay.begin(),w_delay.end(),in.he_w_data);std::copy(x_delay.begin(),x_delay.end(),in.he_x_q);
  // Registered address at N -> first staging at N+1 -> input at N+2.
  for(unsigned bank=0;bank<8;bank++) {
   if(out.he_w_re&(1u<<bank)) {
    const uint64_t line=uint64_t(out.he_w_addr[bank])*8+bank;
    require(line<weights.words.size(),"HE weight address lacks actual enrolled source word");
    std::copy(weights.words[line].begin(),weights.words[line].end(),w_delay.begin()+bank*8);
   }
   if(out.he_x_re&(1u<<bank)) {
    const auto address=out.he_x_addr[bank];
    require(address<H_count&&io.span_lease(id,address,1),"HE fixed-latency input lacks retained actual H lease");
    x_delay[bank]=H[address]; // actual previously returned VM bits, no host FP
   }
  }
 }
};
}

DsromS81MinimumHeBootstrapProvider dsrom_s81_bind_minimum_he_bootstrap(
 DsromS81MinimumRuntime& runtime,uint64_t identity,PrefixPublication& publication,
 const DsromS81MinimumSourceIo& io,const DsromS81MinimumSourceTags& tags) {
 require(runtime.stage==0&&runtime.rank==0&&runtime.pair==0,"native minimum HE source scope");
 const char* dir=std::getenv("DSROM_S81_MINIMUM_SELECTED_DIR");
 require(dir&&*dir,"actual selected source directory required");
 auto source=std::make_shared<Source>(runtime,identity,publication,io,tags,dir);
 DsromS81NativeHeBootstrapSourcePorts p;
 p.H_visible=[source](auto id){return source->io.span_lease(id,0,20480);};
 p.H_read=[source](auto id,auto base){return source->vector(id,base);};
 p.inputs_ready=[source](const auto& op){return source->inputs(op);};
 p.bootstrap_accepted=[source](){source->publication.begin(source->identity,PrefixPublication::SSX);
                              source->publication.begin(source->identity,PrefixPublication::PF);};
 p.memory_prepare=[source](auto id,const auto&o,auto&i){source->memory(id,o,i);};
 p.scalar_offer=[source](auto id,auto a,auto bits){require(id==source->identity,"bootstrap output context changed");
   return source->offer(a==40960?PrefixPublication::SSX:PrefixPublication::PF,a,bits);};
 p.scalar_visible=[source](auto id,auto a,auto bits){require(id==source->identity,"bootstrap receipt context changed");return source->visible(a,bits);};
 p.HE_offer=[source](auto id,auto a,auto mask,const auto&data){require(id==source->identity&&mask==1,"actual HE output mask/context changed");return source->offer(1,a,data[0]);};
 p.HE_visible=[source](auto id,auto a,auto mask,const auto&data){require(id==source->identity&&mask==1,"actual HE receipt mask/context changed");return source->visible(a,data[0]);};
 p.fault=[source](){return source->stopped||source->publication.fault();};
 auto native=std::make_shared<DsromS81NativeHeBootstrapSource>(identity,std::move(p));
 DsromS81MinimumHeBootstrapProvider result;
 result.he=native->engine();result.bootstrap=native->participant();
 // All callbacks retain the ONE leaf. No second construction or clock owner.
 auto keep=native;auto base=result.he;
 result.he.ready=[keep,base](){return base.ready();};
 result.he.idle=[keep,base](){return base.idle();};
 result.start_bootstrap=[keep,source](){
  require(source->runtime.identity&&*source->runtime.identity==source->identity&&
          source->io.span_lease(source->identity,0,20480),"bootstrap arm lacks actual admitted H source lease");
  keep->arm();
 };
 return result;
}
