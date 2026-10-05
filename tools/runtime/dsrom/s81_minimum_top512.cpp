#include "s81_minimum_top512.hpp"
#include "VDsromTop512.h"
#include <memory>
#include <algorithm>

namespace {
struct Top512 {
 DsromS81MinimumRuntime& runtime;
 uint64_t identity;
 std::array<DsromS81MinimumSourceIo,4> io;
 std::function<void(unsigned,unsigned,const S81EmbeddingOutput&)> captured;
 std::function<void(unsigned)> consumed;
 VDsromTop512 leaf;
 // Exact prefetch witness from actual native VM reads; NOT an RTL FF price.
 std::array<std::array<uint32_t,1024>,4> input{};
 std::array<unsigned,4> fetched{};
 // Native has no output ready. Reserve ALL512 IDs before accepting GO.
 std::array<S81EmbeddingOutput,32> output{};
 std::array<unsigned,4> published{};
 std::array<bool,4> offered{};
 unsigned load=0,outputs=0,index=0;
 bool cold=false,started=false,go_seen=false,done_seen=false,complete=false,stopped=false;
 bool armed=false;
 static constexpr unsigned score=446816,ids=365024,dest=447360,stride=262144;
 static void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
 static uint32_t field(const DsromS81PrefixOperation& op,unsigned offset,unsigned width) {
  uint32_t v=0;for(unsigned b=0;b<width;b++)v|=((op.instruction[(offset+b)/32]>>((offset+b)%32))&1u)<<b;
  return v;
 }
 static void literal(const DsromS81PrefixOperation& op) {
  require(op.unit==6&&field(op,0,3)==6&&field(op,1826,2)==2&&
    field(op,1828,30)==score&&field(op,1858,30)==dest&&field(op,1888,21)==512&&
    field(op,1909,12)==512&&field(op,1921,30)==ids&&field(op,2042,6)==36&&
    op.template_sha256&&std::string(op.template_sha256)==
     "05d739b6fb2b665c0ba204a5259c169ad37faa6655e6d1fe3b89bf3c89c0caab",
    "native TOP512 requires literal L20.I47 and actual SC1 stride binding");
 }
 Top512(DsromS81MinimumRuntime& r,uint64_t id,const std::array<DsromS81MinimumSourceIo,4>& sources,
  std::function<void(unsigned,unsigned,const S81EmbeddingOutput&)> c,std::function<void(unsigned)> retired)
 :runtime(r),identity(id),io(sources),captured(std::move(c)),consumed(std::move(retired)),
  leaf(r.context,"minimum_native_crossrank_top512") {
  require(runtime.context&&runtime.cycle&&identity<(1ull<<47)&&bool(captured),
          "native merge needs shared context/identity and actual publisher");
  for(const auto& p:io)require(p.read_word&&p.span_lease&&p.offer&&p.visible,
                              "native merge requires all four actual rank VMs");
  leaf.clk=0;leaf.rst_n=0;leaf.go=0;leaf.ld_valid=0;leaf.ld_id=0;leaf.ld_rank=0;leaf.ld_word=0;
  leaf.n=512;leaf.k=512;leaf.stride=stride;
  for(unsigned i=0;i<64;i++)leaf.ld_data[i]=0;
 }
 bool leases()const {
  for(const auto& p:io)if(!p.span_lease(identity,score,512)||!p.span_lease(identity,ids,512))return false;
  return true;
 }
 bool ready()const{return cold&&!stopped&&!armed&&!started&&!leaf.busy;}
 bool inputs_ready(const DsromS81PrefixOperation& op) {
  literal(op);
  if(!ready()||!leases())return false;
  // Prefetch uses the sole participant's prepare edges, never a private tick.
  return std::all_of(fetched.begin(),fetched.end(),[](unsigned n){return n==1024;});
 }
 void drive(const DsromS81PrefixOperation& op,bool go) {
  literal(op);
  if(!go)return;
  require(inputs_ready(op)&&runtime.identity&&*runtime.identity==identity,
          "TOP512 GO lacks four real published inputs or source context");
  require(!complete,"same selection cannot be readmitted without source rebind");
  index=op.index;armed=true;
 }
 void prepare(const DsromS81PairResult&) {
  try {
   require(!stopped&&!leaf.fault,"TOP512 native fault quarantines retained obligations");
   leaf.go=0;leaf.ld_valid=0;leaf.n=512;leaf.k=512;leaf.stride=stride;
   if(cold&&!armed&&!started&&!complete&&leases()) {
    for(unsigned r=0;r<4;r++)if(fetched[r]<1024) {
     const unsigned n=fetched[r];auto value=io[r].read_word(identity,(n<512?score:ids)+(n%512));
     if(value) {
      // Protocol bounds/order only. No host compare/sort of score values.
      if(n>=512)require(*value<stride&&(n==512||*value>input[r][n-1]),
                         "rank native IDs not unique ascending local source indices");
      input[r][n]=*value;fetched[r]++;
     }
    }
   }
   if(armed&&load<64) {
    require(leases(),"TOP512 accepted input lease revoked before native capture");
    leaf.ld_id=load>=32;leaf.ld_word=load%32;leaf.ld_rank=0;
    for(unsigned r=0;r<4;r++)for(unsigned j=0;j<16;j++)
     leaf.ld_data[r*16+j]=input[r][(load>=32?512:0)+(load%32)*16+j];
    leaf.ld_valid=1;
   }else if(armed&&!go_seen)leaf.go=1;
   for(unsigned r=0;r<4;r++)if(published[r]<outputs) {
    auto& out=output[published[r]];
    if(!offered[r])offered[r]=io[r].offer(out,16);
    if(offered[r]&&io[r].visible(out,16)){published[r]++;offered[r]=false;}
   }
   if(done_seen) {
    require(outputs==32,"TOP512 native done before all512 outputs");
    if(std::all_of(published.begin(),published.end(),[](unsigned n){return n==32;})) {
     require(!leaf.busy,"TOP512 publication cannot erase native activity");
     complete=true;armed=false;started=false;
    }
   }
  }catch(...){stopped=true;throw;}
 }
 void rising(bool released) {
  try {
   require(!stopped,"TOP512 quarantined");
   if(!released)require(!armed&&!started&&!go_seen,"reset cannot discard accepted merge debt");
   // Pins frozen in prepare are the OLD inputs of this one native edge.
   const bool take=leaf.ld_valid&&released;
   const bool go=leaf.go&&released;
   leaf.rst_n=released;leaf.clk=1;leaf.eval();
   if(!released){cold=true;return;}
   if(take) {
    require(armed&&load<64&&!go_seen,"native load lacks retained accepted source");
    ++load;
    if(load==64&&consumed)for(unsigned r=0;r<4;r++)consumed(r);
   }
   if(go){require(armed&&load==64&&!go_seen,"duplicate or premature native TOP512 GO");go_seen=true;started=true;}
   require(!leaf.fault,"native TOP512 refused candidate/command; no fallback");
   if(leaf.out_valid) {
    require(go_seen&&!done_seen&&leaf.out_nw>=1&&leaf.out_nw<=4&&
            outputs+leaf.out_nw<=32,"native merge output exceeds reserved512 ID span");
    for(unsigned w=0;w<leaf.out_nw;w++) {
     auto& out=output[outputs];out={};out.vm_valid=1;out.vm_identity=identity;
     out.vm_address=dest+outputs*16;
     for(unsigned j=0;j<16;j++)out.vm_data[j]=leaf.out_data[w*16+j];
     for(unsigned r=0;r<4;r++)captured(r,index,out);
     ++outputs;
    }
    require(bool(leaf.out_last)==(outputs==32),"native final-output marker/count mismatch");
   }
   if(leaf.done){require(go_seen&&!done_seen&&outputs==32,"foreign/early merge done");done_seen=true;}
  }catch(...){stopped=true;throw;}
 }
 DsromS81PrefixNativeEngine engine(std::shared_ptr<Top512> self) {
  return {{"native_L20_I47_crossrank_top512",
    [self](const auto& r){self->prepare(r);},[self](bool r){self->rising(r);},
    [self](bool r){self->leaf.rst_n=r;self->leaf.clk=0;self->leaf.eval();},
    [self](){return self->stopped||bool(self->leaf.fault);}},
   [self](){return self->ready();},[self](){return !self->armed&&!self->started&&(!self->go_seen||self->complete);},
   [self](const auto& op){return self->inputs_ready(op);},
   [self](const auto& op,bool go){self->drive(op,go);}};
 }
};
}
DsromS81PrefixNativeEngine dsrom_s81_bind_native_top512(
 DsromS81MinimumRuntime& r,uint64_t id,const std::array<DsromS81MinimumSourceIo,4>& io,
 std::function<void(unsigned,unsigned,const S81EmbeddingOutput&)> captured,
 std::function<void(unsigned)> consumed) {
 auto owner=std::make_shared<Top512>(r,id,io,std::move(captured),std::move(consumed));
 return owner->engine(owner);
}
