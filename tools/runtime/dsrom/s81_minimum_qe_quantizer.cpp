#include "s81_minimum_qe_quantizer.hpp"
#include "s81_minimum_source_tags_component.hpp"
#include <memory>
#include <deque>
namespace {
uint32_t field(const DsromS81PrefixOperation&o,unsigned offset,unsigned width){
 uint32_t v=0;for(unsigned b=0;b<width;b++)v|=((o.instruction[(offset+b)/32]>>((offset+b)%32))&1u)<<b;return v;
}
struct NativeQuant {
 DsromS81MinimumRuntime&r;uint64_t id;dsrom_s81_minimum::PrefixPublication&pub;
 DsromS81MinimumSourceIo io;DsromS81NativeQeQuantizerPorts&hooks;VDsromQeQuant leaf;
 std::optional<DsromS81PrefixOperation> op;std::vector<uint32_t> staged;
 size_t fetched=0;unsigned mode=0,nb=0;uint32_t xb=0,ob=0;
 bool admitted=false,stopped=false,old_go=false,old_read=false,old_write=false;
 uint32_t old_read_address=0,old_write_address=0,old_write_mask=0;
 std::array<uint32_t,32> old_write_data{},old_read_data{};
 struct Out {S81EmbeddingOutput value{};bool offered=false;};std::deque<Out> outputs;
 static void require(bool ok,const char*s){if(!ok)throw std::runtime_error(s);}
 NativeQuant(DsromS81MinimumRuntime&runtime,uint64_t identity,dsrom_s81_minimum::PrefixPublication&p,
 const DsromS81MinimumSourceIo&source,DsromS81NativeQeQuantizerPorts&ports)
 :r(runtime),id(identity),pub(p),io(source),hooks(ports),leaf(r.context,"source_native_qe_quantizer"){
  require(r.context&&r.cycle&&io.read_word&&io.span_lease&&io.offer&&io.visible,"QE actual SourceIo/commoncontext required");
  leaf.clk=0;leaf.rst_n=0;leaf.go=0;leaf.vi_q=0;leaf.qr_issue_ready=0;
  for(unsigned j=0;j<32;j++)leaf.xr_q[j]=0;
  for(unsigned j=0;j<136;j++)leaf.qr_q[j]=0;
 }
 bool inputs(const DsromS81PrefixOperation&o){
  require(!stopped&&o.unit==3,"QE quantizer operation/source fault");
  if(op&&op->index!=o.index){
   require(idle(),"QE quantizer source rebind before actual visibility/drain");op.reset();staged.clear();fetched=0;admitted=false;
  }
  if(!op){
   mode=field(o,1245,2);nb=field(o,1278,8);xb=field(o,1248,30);ob=field(o,1419,30);
   require(mode>=1&&mode<=3&&nb&&nb<=192&&field(o,1358,1)==0,"QE mode1/2/3 exact NB192 no indirect weights");
   unsigned selector=field(o,1449,6);
   if(selector){require(bool(hooks.actual_dynamic),"QE native effective destination requires actual DY");
    auto d=hooks.actual_dynamic(selector);if(!d)return false;
    uint64_t effective=uint64_t(ob)+*d;require(effective<(1ull<<30),"QE effective AW30 destination overflow");ob=effective;}
   require(uint64_t(xb)+32*nb<=(1u<<19),"QE operand actual VM19 extent");
   if(mode!=3)require(uint64_t(ob)+32*nb<=(1u<<19),"QE ordinary output VM19 extent");
   else require(bool(hooks.ckv_writes_visible),"QE QDQ4E requires actual CKV backend visibility owner");
   op=o;staged.resize(32*nb);
   leaf.i_mode=mode;leaf.i_fp4=field(o,1247,1);leaf.i_unrounded=field(o,1960,1);
   leaf.i_xbase=xb;leaf.i_nb=nb;leaf.i_nout=field(o,1286,21);leaf.i_tiles=field(o,1307,21);
   leaf.i_wbase=field(o,1328,30);leaf.i_ind=0;leaf.i_ibase=field(o,1359,30);leaf.i_istride=field(o,1389,30);
   leaf.i_obase=ob;leaf.i_m=field(o,1723,3);leaf.i_xps=field(o,1726,30);leaf.i_ops=field(o,1756,30);
  }
  require(op->instruction==o.instruction,"QE held literal changed");
  if(admitted)return false;
  if(!io.span_lease(id,xb,32*nb))return false;
  if(fetched<staged.size()){
   auto v=io.read_word(id,xb+fetched);if(!v)return false;
   require(io.span_lease(id,xb,32*nb),"QE input version changed at actual response");staged[fetched++]=*v;
  }
  return fetched==staged.size();
 }
 bool idle()const {
  return !fault()&&leaf.idle&&outputs.empty()&&(!admitted||(mode==3?hooks.ckv_writes_visible(*op):pub.complete(id,op->index)));
 }
 bool fault()const{return stopped||leaf.fault||leaf.kvb_fault||pub.fault();}
 void drive(const DsromS81PrefixOperation&o,bool go){
  leaf.go=0;if(!go)return;
  require(op&&op->index==o.index&&op->instruction==o.instruction&&!admitted&&
   fetched==staged.size()&&leaf.ready&&io.span_lease(id,xb,32*nb),"QE GO before actual operand/version/ready");leaf.go=1;
 }
 void prepare(){
  require(!fault(),"QE quantizer quarantined");old_go=leaf.go&&leaf.ready;
  old_read=leaf.xr_re;old_read_address=leaf.xr_addr;
  old_write=leaf.w_we&1;old_write_address=leaf.w_addr;old_write_mask=leaf.w_mask;
  for(unsigned j=0;j<32;j++)old_write_data[j]=leaf.w_data[j];
  require(!leaf.qr_re&&!leaf.vi_re,"QE quantizer unexpectedly requested weights/indirect index");
  if(old_read){
   require(admitted&&old_read_address>=xb&&uint64_t(old_read_address)+32<=uint64_t(xb)+staged.size()&&
    io.span_lease(id,xb,32*nb),"QE native staged read unowned/lost-version");
   for(unsigned j=0;j<32;j++)old_read_data[j]=staged.at(old_read_address-xb+j);
  }
  if(!outputs.empty()){
   auto&h=outputs.front();if(!h.offered)h.offered=io.offer(h.value,1);
   if(h.offered&&io.visible(h.value,1))outputs.pop_front();
  }
 }
 void rising(bool rn){
  if(!rn)require(!admitted,"QE reset would erase accepted quantizer debt");
  if(rn&&old_go){require(op&&r.identity&&*r.identity==id&&!admitted,"QE actual admission identity");admitted=true;}
  if(rn&&old_write){
   require(admitted&&op&&old_write_address>=ob&&uint64_t(old_write_address)+32<=uint64_t(ob)+32*nb&&
    old_write_mask==0xffffffffu,"QE native output outside accepted descriptor");
   if(mode!=3)for(unsigned j=0;j<32;j++){
    uint32_t address=old_write_address+j;
    auto c=dsrom_s81_reserve_native_scalar_tag(r,id,op->index,address,old_write_data[j]);
    pub.native_scalar(op->index,c,true);Out h{};h.value.vm_valid=true;h.value.vm_identity=id;
    h.value.vm_address=address;h.value.vm_data[0]=old_write_data[j];outputs.push_back(h);
   }
   // mode3 remains real native ww_q data wired by Noether's OLD prepare to CKV
   // service. No host encoding/publication or synthetic w_done callback here.
  }
  leaf.clk=1;leaf.rst_n=rn;leaf.eval();
  // Match the existing synchronous VM read: the edge consumes the PREVIOUS
  // response with OLD x_v, then the OLD xr_re request installs the next block.
  // Supplying this in prepare shifts each block forward while x_v is delayed.
  if(rn&&old_read)for(unsigned j=0;j<32;j++)leaf.xr_q[j]=old_read_data[j];
 }
 void falling(bool rn){leaf.clk=0;leaf.rst_n=rn;leaf.eval();}
};
}
DsromS81PrefixNativeEngine dsrom_s81_bind_minimum_qe_quantizer(DsromS81MinimumRuntime&r,uint64_t id,
 dsrom_s81_minimum::PrefixPublication&pub,const DsromS81MinimumSourceIo&io,DsromS81NativeQeQuantizerPorts&hooks){
 auto p=std::make_shared<NativeQuant>(r,id,pub,io,hooks);
 hooks.native=[p]()->const VDsromQeQuant&{return p->leaf;};
 hooks.held_operation=[p](){if(!p->op)throw std::runtime_error("QE no actual held op");return *p->op;};
 hooks.held_mode=[p](){return p->mode;};
 hooks.accepts_on_current_shared_edge=[p](){return bool(p->leaf.go&&p->leaf.ready);};
 return {{"source-QE-quantizer",[p](const auto&){try{p->prepare();}catch(...){p->stopped=true;throw;}},
  [p](bool rn){try{p->rising(rn);}catch(...){p->stopped=true;throw;}},[p](bool rn){p->falling(rn);},[p](){return p->fault();}},
  [p](){return p->op&&!p->admitted&&p->fetched==p->staged.size()&&bool(p->leaf.ready);},[p](){return p->idle();},
  [p](const auto&o){return p->inputs(o);},[p](const auto&o,bool go){p->drive(o,go);}};
}
DsromS81PrefixNativeEngine dsrom_s81_bind_qe_modes(DsromS81PrefixNativeEngine field_engine,DsromS81PrefixNativeEngine quantizer){
 struct Modes {DsromS81PrefixNativeEngine f,q;bool quant=false;};
 auto p=std::make_shared<Modes>(Modes{std::move(field_engine),std::move(quantizer),false});
 return {{"source-field-and-native-quantizer",[p](const auto&r){p->f.participant.prepare(r);p->q.participant.prepare(r);},
  [p](bool rn){p->f.participant.rising(rn);p->q.participant.rising(rn);},
  [p](bool rn){p->f.participant.falling(rn);p->q.participant.falling(rn);},
  [p](){return p->f.participant.fault()||p->q.participant.fault();}},
  [p](){return (p->quant?p->q:p->f).ready();},[p](){return (p->quant?p->q:p->f).idle();},
  [p](const auto&o){p->quant=field(o,1245,2)!=0;return (p->quant?p->q:p->f).inputs_ready(o);},
  [p](const auto&o,bool go){if(!go){p->f.drive(o,false);p->q.drive(o,false);}else (p->quant?p->q:p->f).drive(o,true);}};
}
