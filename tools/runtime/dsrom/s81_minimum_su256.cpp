// Selected SUN256 native SU; host copies opaque payload bits only.
#include "s81_minimum_prefix_io.hpp"
#include "s81_minimum_su256_ports.hpp"
#include "s81_minimum_su256_constants.hpp"
#include "VDsromSu256.h"
#include "verilated.h"
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <deque>
#include <memory>
#include <sstream>
namespace {
uint32_t field(const DsromS81PrefixOperation&o,unsigned off,unsigned width){
 uint32_t v=0;for(unsigned j=0;j<width;++j)v|=((o.instruction[(off+j)/32]>>((off+j)%32))&1u)<<j;return v;
}
struct NativeSu {
 DsromS81MinimumRuntime& runtime;uint64_t id;dsrom_s81_minimum::PrefixPublication& publication;
 DsromS81MinimumSourceIo io;VDsromSu256 leaf;
 DsromS81NativeSuPorts* hooks=nullptr;bool kv_pending=false;
 std::optional<DsromS81PrefixOperation> op;
 std::vector<uint32_t> addresses;std::map<uint32_t,uint32_t> staged;
 std::map<uint32_t,uint64_t> crom;bool crom_loaded=false;
 size_t fetched=0;bool admitted=false,stopped=false,offered=false;
 bool indirect_planned=false;std::vector<uint32_t> index_addresses;
 size_t index_fetched=0;
 std::deque<S81EmbeddingOutput> outputs;
 NativeSu(DsromS81MinimumRuntime&r,uint64_t identity,dsrom_s81_minimum::PrefixPublication&p,
          const DsromS81MinimumSourceIo& source):runtime(r),id(identity),publication(p),io(source),leaf(r.context,"minimum_native_su256"){
  if(!r.context||!r.cycle||identity>=(1ull<<47)||
     !io.read_word||!io.span_lease||!io.offer||!io.visible)
   throw std::runtime_error("SU256 requires same runtime/context and actual scalar SourceIo");
  leaf.clk=0;leaf.rst_n=0;leaf.go=0;for(unsigned j=0;j<1024;++j)leaf.rd_q[j]=0;
  for(unsigned j=0;j<256;++j)leaf.vi_q[j]=0;
 }
 static void require(bool b,const char*s){if(!b)throw std::runtime_error(s);}
 void constants(){
  if(crom_loaded)return;
  const char* path=std::getenv("DSROM_S81_MINIMUM_CROM_HEX");
  require(path&&*path,"SU requires actual layer-enrolled CROM file DSROM_S81_MINIMUM_CROM_HEX; no synthetic constants");
  std::ifstream f(path);require(bool(f),"actual CROM source unavailable");
  uint32_t a=0;std::string line,token;
  while(std::getline(f,line)){
   auto comment=line.find("//");if(comment!=std::string::npos)line.resize(comment);
   std::istringstream ss(line);while(ss>>token){
    size_t n=0;if(token[0]=='@'){auto v=std::stoull(token.substr(1),&n,16);require(n==token.size()-1&&v<(1u<<19),"CROM address19");a=v;}
    else {auto v=std::stoull(token,&n,16);require(n==token.size()&&token.size()<=16&&a<(1u<<19)&&!crom.count(a),"CROM payload/duplicate/address");crom.emplace(a++,v);}
   }
  }crom_loaded=true;
 }
 uint32_t external(unsigned src,uint32_t a,unsigned operand){
  require(src==1||src==2,"prefix does not enroll WROM provider");
  require(bool(op),"SU constant read without held source operation");
  a=dsrom_s81_su_constant_address(*op,operand,src,a);constants();
  auto p=crom.find(a);require(p!=crom.end(),"native source address missing from actual CROM");
  return src==1?uint32_t(p->second):uint32_t(p->second>>32);
 }
 uint32_t dynamic(unsigned selector){
  if(!selector)return 0;
  require(hooks&&hooks->actual_dynamic,"SU requires captured source dynamic selector");
  auto value=hooks->actual_dynamic(selector);require(bool(value),"SU dynamic value not yet captured");return *value;
 }
 uint32_t address(const DsromS81PrefixOperation&o,unsigned base,unsigned selector){
  const uint64_t v=uint64_t(field(o,base,30))+dynamic(field(o,selector,6));
  require(v<(1ull<<30),"SU effective native address30 overflow");return v;
 }
 void decode(const DsromS81PrefixOperation&o){
  const uint64_t no=uint64_t(field(o,482,21))+dynamic(field(o,524,6));
  const uint64_t ni=uint64_t(field(o,503,21))+dynamic(field(o,530,6));
  require(no<=65535&&ni<=65535,"retained native SU NW16 cannot truncate effective count");
  leaf.i_nout=no;
  leaf.i_nin=ni;
  leaf.i_chase=field(o,1698,21);
  leaf.i_m1=field(o,966,3);
  leaf.i_m2=field(o,969,2);
  leaf.i_qm=field(o,971,3);
  leaf.i_ad=field(o,974,3);
  leaf.i_sfu=field(o,977,3);
  leaf.i_e1=field(o,980,3);
  leaf.i_e2=field(o,983,2);
  leaf.i_rnd=field(o,985,1);
  leaf.i_dst=field(o,986,2);
  leaf.i_imm1=field(o,1149,32);
  leaf.i_imm2=field(o,1181,32);
  leaf.i_imm3=field(o,1213,32);
  leaf.i_red=field(o,1084,2);
  leaf.i_asrc=field(o,536,2);
  leaf.i_abase=address(o,538,628);
  leaf.i_aso=field(o,568,30);
  leaf.i_asi=field(o,598,30);
  leaf.i_bsrc=field(o,666,2);
  leaf.i_bbase=address(o,668,758);
  leaf.i_bso=field(o,698,30);
  leaf.i_bsi=field(o,728,30);
  leaf.i_csrc=field(o,765,2);
  leaf.i_cbase=address(o,767,857);
  leaf.i_cso=field(o,797,30);
  leaf.i_csi=field(o,827,30);
  leaf.i_dsrc=field(o,864,2);
  leaf.i_dbase=address(o,866,956);
  leaf.i_dso=field(o,896,30);
  leaf.i_dsi=field(o,926,30);
  leaf.i_aind=field(o,634,2);
  leaf.i_aibase=field(o,636,30);
  leaf.i_bhalf=field(o,764,1);
  leaf.i_cpair=field(o,863,1);
  leaf.i_arnd=field(o,962,1);
  leaf.i_arelu=field(o,963,1);
  leaf.i_amin=field(o,964,1);
  leaf.i_cclip=field(o,965,1);
  leaf.i_obase=leaf.i_dst==3?field(o,988,30):address(o,988,1078);
  leaf.i_oso=field(o,1018,30);
  leaf.i_osi=field(o,1048,30);
  leaf.i_redsq=field(o,1086,1);
  leaf.i_redwhole=field(o,1087,1);
  leaf.i_redtree=field(o,1697,1);
  leaf.i_redrnd=field(o,1088,1);
  leaf.i_rbase=field(o,1089,30);
  leaf.i_rso=field(o,1119,30);
  leaf.i_m=field(o,1723,3);
  leaf.i_xps=field(o,1726,30);
  leaf.i_ops=field(o,1756,30);
  leaf.i_orow=dynamic(field(o,1078,6)); // source core uses the same captured O_D
 }
 bool inputs(const DsromS81PrefixOperation&o){
  try {
   require(!stopped,"SU quarantined");
   require(runtime.identity&&*runtime.identity==id,"SU operand staging requires accepted source context");
   if(admitted)return false;
   if(op&&op->index==o.index)require(op->unit==o.unit&&op->instruction==o.instruction,
    "SU held literal changed during operand staging");
   if(!op||op->index!=o.index){
    require(leaf.idle&&outputs.empty(),"SU prefetch overlaps old native publication");
    require(o.index<(1u<<14)&&o.unit==2,"SU literal unit/index14");
    require(field(o,634,2)<3,"native SU indirect selector");
    for(unsigned selector:{524u,530u,628u,758u,857u,956u,1078u})if(field(o,selector,6)){
     require(hooks&&hooks->actual_dynamic,"SU dynamic source callback absent");
     if(!hooks->actual_dynamic(field(o,selector,6)))return false;
    }
    op=o;decode(o);staged.clear();addresses.clear();fetched=0;
    indirect_planned=false;index_addresses.clear();index_fetched=0;
    const unsigned count=leaf.i_aind==1?leaf.i_nin:leaf.i_aind==2?leaf.i_nout:0;
    for(unsigned j=0;j<count;++j){
     uint64_t a=uint64_t(leaf.i_aibase)+j;require(a<(1u<<19),"actual SU index VM19");
     index_addresses.push_back(a);
    }
   }
   if(index_fetched<index_addresses.size()){
    auto a=index_addresses[index_fetched];if(!io.span_lease(id,a,1))return false;
    auto v=io.read_word(id,a);if(!v)return false;
    require(io.span_lease(id,a,1),"SU index version lost before native response");
    staged.emplace(a,*v);++index_fetched;return false;
   }
   if(!indirect_planned){
    std::set<uint32_t> unique;
    const uint32_t src[]={leaf.i_asrc,leaf.i_bsrc,leaf.i_csrc,leaf.i_dsrc};
    const uint32_t base[]={leaf.i_abase,leaf.i_bbase,leaf.i_cbase,leaf.i_dbase};
    const uint32_t so[]={leaf.i_aso,leaf.i_bso,leaf.i_cso,leaf.i_dso};
    const uint32_t si[]={leaf.i_asi,leaf.i_bsi,leaf.i_csi,leaf.i_dsi};
    for(unsigned out=0;out<leaf.i_nout;++out)for(unsigned i=0;i<leaf.i_nin;++i){
     const uint32_t index=leaf.i_aind?staged.at(leaf.i_aibase+(leaf.i_aind==1?i:out))&0x3fffffffu:0;
     const uint64_t ao=leaf.i_aind==2?index:out,ai=leaf.i_aind==1?index:i;
     const uint64_t a=uint64_t(base[0])+ao*so[0]+ai*si[0];
     for(unsigned p=0;p<4;++p){
      uint64_t address=p==0?a:p==2&&leaf.i_cpair?(a^1u):
       uint64_t(base[p])+uint64_t(out)*so[p]+uint64_t((p==1||p==3)&&leaf.i_bhalf?i/2:i)*si[p];
      require(address<(1ull<<30),"actual SU effective address30 overflow");
      if(src[p]==0){require(address<(1u<<19),"actual SU source VM19 alias");if(!staged.count(address))unique.insert(address);}
      else (void)external(src[p],address,p);
     }
    }
    // Snapshot is bounded by the actual selected VM's19-bit address space.
    // Software-only staging, not an extra physical VM or free seat allocation.
    require(unique.size()+staged.size()<=(1u<<19),"native SU scalar snapshot exceeds VM19");
    addresses.assign(unique.begin(),unique.end());indirect_planned=true;
   }
   // ONE actual SourceIo request. No invented wide-read acceptance or credits.
   if(fetched<addresses.size()){
    auto a=addresses[fetched];if(!io.span_lease(id,a,1))return false;
    auto v=io.read_word(id,a);if(!v)return false;
    require(io.span_lease(id,a,1),"SU input version revoked before captured reply");
    staged.emplace(a,*v);++fetched;
   }
   if(fetched==addresses.size())for(const auto& a:staged)
    require(io.span_lease(id,a.first,1),"SU prefetched input version lost before GO");
   return fetched==addresses.size();
  }catch(...){stopped=true;throw;}
 }
 void drive(const DsromS81PrefixOperation&o,bool go){
  leaf.go=0;if(!go)return;
  require(!stopped&&runtime.identity&&*runtime.identity==id,"SU GO requires accepted source context");
  require(op&&op->index==o.index&&op->instruction==o.instruction&&indirect_planned&&
          index_fetched==index_addresses.size()&&fetched==addresses.size()&&!admitted,"SU GO before actual prefetch");
  leaf.go=1;
  // Effective dynamic native ports stay fixed from the staged operand capture.
 }
 void prepare(const DsromS81PairResult&){
  if(!outputs.empty()){
   if(!offered)offered=io.offer(outputs.front(),1);
   if(offered&&io.visible(outputs.front(),1)){outputs.pop_front();offered=false;}
  }
  if(admitted&&leaf.idle&&outputs.empty()&&(!kv_pending||(hooks&&hooks->kv_writes_visible&&hooks->kv_writes_visible()))){
   kv_pending=false;
   admitted=false;op.reset(); // next generation must reread actual operand versions
  }
 }
 uint32_t memory(unsigned src,uint32_t a,unsigned operand=0){
  if(src)return external(src,a,operand);
  auto v=staged.find(a);
  require(v!=staged.end(),"native fixed read outside actual staged scalars");return v->second;
 }
 static uint32_t bits(uint32_t w,unsigned off,unsigned n){
  require(n==1&&off<32,"scalar native port width");return (w>>off)&1u;
 }
 template<class W>static uint32_t bits(const W&w,unsigned off,unsigned n){
  uint32_t v=0;for(unsigned j=0;j<n;++j)v|=((w[(off+j)/32]>>((off+j)%32))&1u)<<j;return v;
 }
 void capture(uint32_t a,uint32_t payload){
  require(op&&admitted&&outputs.size()<(1u<<19),"actual SU output lacks admitted bounded context");
  S81EmbeddingOutput o{};o.vm_valid=true;o.vm_identity=id;o.vm_address=a;o.vm_data[0]=payload;
  // This reserves once at native output capture, never on equal-value retry.
  dsrom_s81_capture_minimum_prefix_scalar(runtime,publication,op->index,o,0,true);
  outputs.push_back(o);
 }
 void rising(bool released){
  try {
   const bool acc=released&&leaf.go&&leaf.ready;
   std::array<uint32_t,1024> q{};
   std::array<uint32_t,256> vi{};
   for(unsigned j=0;j<256;++j){
    vi[j]=leaf.vi_q[j];
    if(released&&bits(leaf.vi_re,j,1))vi[j]=memory(0,bits(leaf.vi_addr,j*30,30));
   }
   for(unsigned j=0;j<1024;++j){
    q[j]=leaf.rd_q[j];if(released&&bits(leaf.rd_re,j,1))
     q[j]=memory(bits(leaf.rd_src,j*2,2),bits(leaf.rd_addr,j*30,30),j%4);
   }
   if(acc)admitted=true;
   leaf.rst_n=released;leaf.clk=1;leaf.eval(); // OLD synchronous-memory Q at edge
   for(unsigned j=0;j<1024;++j)leaf.rd_q[j]=q[j]; // register memory Q after edge
   for(unsigned j=0;j<256;++j)leaf.vi_q[j]=vi[j]; // same native one-register index RAM
   if(released){
    require(!leaf.fault,"actual native SU arithmetic/control fault");
    bool any_kv=false;for(unsigned j=0;j<256;++j)any_kv|=bool(bits(leaf.kv_we,j,1));
    if(any_kv){
     require(hooks&&hooks->kv_write&&hooks->kv_writes_visible&&op&&admitted,"native KV writer has no bound sink/completion");
     kv_pending=true;hooks->kv_write(leaf,*op); // actual registered outputs; no ACK implied
    }
    for(unsigned j=0;j<256;++j){
     if(bits(leaf.vm_we,j,1))capture(bits(leaf.vm_waddr,j*30,30),leaf.vm_wdata[j]);
    }
    for(unsigned j=0;j<32;++j)if(bits(leaf.res_we,j,1))capture(bits(leaf.res_addr,j*30,30),leaf.res_data[j]);
   }
  }catch(...){stopped=true;throw;}
 }
 void falling(bool released){leaf.rst_n=released;leaf.clk=0;leaf.eval();}
 bool fault()const{return stopped||leaf.fault||publication.fault();}
};
}
DsromS81PrefixNativeEngine dsrom_s81_bind_minimum_su256(
 DsromS81MinimumRuntime&r,uint64_t id,dsrom_s81_minimum::PrefixPublication&pub,
 const DsromS81MinimumSourceIo&io,const DsromS81MinimumSourceTags&tags){
 if(!tags.scalar_accept||!tags.read_accept)throw std::runtime_error("same-bank actual accepts required");
 auto p=std::make_shared<NativeSu>(r,id,pub,io);
 return {{"native-SUN256-SU-only",[p](const auto&v){p->prepare(v);},
  [p](bool rn){p->rising(rn);},[p](bool rn){p->falling(rn);},[p](){return p->fault();}},
  [p](){return bool(p->leaf.ready)&&!p->admitted;},
  [p](){return bool(p->leaf.idle)&&p->outputs.empty()&&!p->admitted;},
  [p](const auto&o){return p->inputs(o);},[p](const auto&o,bool go){p->drive(o,go);}};
}

DsromS81PrefixNativeEngine dsrom_s81_bind_minimum_su256(
 DsromS81MinimumRuntime&r,uint64_t id,dsrom_s81_minimum::PrefixPublication&pub,
 const DsromS81MinimumSourceIo&io,const DsromS81MinimumSourceTags&tags,
 DsromS81NativeSuPorts&hooks){
 if(!tags.scalar_accept||!tags.read_accept)throw std::runtime_error("same-bank actual accepts required");
 auto p=std::make_shared<NativeSu>(r,id,pub,io);p->hooks=&hooks;
 hooks.native=[p]()->const VDsromSu256&{return p->leaf;};
 hooks.held_operation=[p](){if(!p->op)throw std::runtime_error("SU has no held source operation");return *p->op;};
 hooks.accepts_on_current_shared_edge=[p](){return bool(p->leaf.go&&p->leaf.ready);};
 return {{"native-SUN256-SU-only",[p](const auto&v){p->prepare(v);},
  [p](bool rn){p->rising(rn);},[p](bool rn){p->falling(rn);},[p](){return p->fault();}},
  [p](){return bool(p->leaf.ready)&&!p->admitted;},
  [p](){return bool(p->leaf.idle)&&p->outputs.empty()&&!p->admitted;},
  [p](const auto&o){return p->inputs(o);},[p](const auto&o,bool go){p->drive(o,go);}};
}
