#include "s81_minimum_l20_index_writer.hpp"
#include "VDsromS81IndexWriter.h"
#include <bitset>
#include <cstring>
namespace dsrom_s81_minimum {
namespace {
constexpr char I36_SHA[]="436e442bdf1b4743ac79abc55ab08892561afe7bfdf29803d631ed531180c072";
// Pinned L20.I36 has dst3/o_base0: its native KV address space is
// IK-region-relative. The scorer separately maps I44 region0 to 0x1000000.
// Preserve SU addresses and let the unchanged writer use relative cfg base0.
constexpr uint32_t I36_IK_BASE=0;
// 9 + ordered canonical source-node index; this is not literal PC36.
constexpr unsigned I36_PRODUCER=2507;
void need(bool b,const char*why){if(!b)throw std::runtime_error(why);}
template<class Wide> uint32_t bits(const Wide&w,unsigned off,unsigned n) {
 uint32_t v=0;for(unsigned b=0;b<n;b++)v|=((w[(off+b)/32]>>((off+b)%32))&1u)<<b;return v;
}
}
struct L20IndexWriter::Impl:std::enable_shared_from_this<Impl> {
 DsromS81MinimumRuntime& runtime;uint64_t identity;
 DsromS81NativeSuPorts& hooks;std::shared_ptr<NativeIndexHbm> backend;
 DsromS81PrefixOperation source;VDsromS81IndexWriter leaf;
 bool old_accept=false,accepted=false,stopped=false,observed_kv=false,origin_idle_seen=false;
 uint32_t position=0;long prepared=-1;
 std::bitset<128> captured;
 Impl(DsromS81MinimumRuntime&r,uint64_t id,DsromS81NativeSuPorts&h,
      std::shared_ptr<NativeIndexHbm>b,const DsromS81PrefixOperation&o)
 :runtime(r),identity(id),hooks(h),backend(std::move(b)),source(o),
  leaf(r.context,("native_L20_I36_index_writer_r"+std::to_string(r.rank)).c_str()) {
  need(r.context&&r.cycle&&id<(1ull<<47)&&r.rank==3&&backend&&
       backend->initialized()&&backend->capacity_words()==139520,
       "I36 writer requires actual shared runtime and selected ring history backend");
  need(source.index==I36_PRODUCER&&source.unit==2&&source.template_sha256&&
       !std::strcmp(source.template_sha256,I36_SHA),"I36 writer requires pinned actual SU literal");
  source.template_sha256=I36_SHA;
  need(h.native&&h.held_operation&&h.accepts_on_current_shared_edge&&h.actual_dynamic,
       "I36 writer requires borrowed actual SUN/held/OLD-accept/DY hooks");
  need(h.native().contextp()==r.context,"I36 writer cannot borrow another SU clock context");
  leaf.clk=0;leaf.rst_n=0;leaf.su_go=0;leaf.kv_we={};leaf.kv_waddr={};leaf.kv_wdata={};leaf.w_rdy=0;
  leaf.cfg_ik_base=I36_IK_BASE;leaf.i_user_base_sec=0;leaf.eval();
 }
 bool same(const DsromS81PrefixOperation&o)const {
  return o.index==source.index&&o.unit==source.unit&&o.instruction==source.instruction&&
   o.template_sha256&&!std::strcmp(o.template_sha256,I36_SHA);
 }
 bool fault()const{return stopped||leaf.fault||hooks.native().fault;}
 bool visible()const {
  return !fault()&&accepted&&observed_kv&&captured.all()&&leaf.dbg_keys==1&&!leaf.w_v&&
   backend->current_committed(position-3u*262144u);
 }
 bool idle()const{return visible()&&origin_idle_seen;}
 void context()const {
  need(runtime.identity&&*runtime.identity==identity,"I36 native writer lost held ID47 context");
 }
 void bind_sink() {
  auto self=shared_from_this();
  auto previous_write=hooks.kv_write;auto previous_visible=hooks.kv_writes_visible;
  hooks.kv_write=[self,previous_write](const auto&su,const auto&o) {
   if(o.index!=self->source.index){need(bool(previous_write),"unowned non-I36 native KV strobe");previous_write(su,o);return;}
   try {
    self->context();need(self->same(o)&&!su.fault&&(self->accepted||self->old_accept),
                         "I36 KV observation without actual accepted held SU owner");
    // Observation only. OLD registered ports are copied in prepare() and
    // consumed by the retained RTL on its next actual shared rising edge.
    self->observed_kv=true;
   }catch(...){self->stopped=true;throw;}
  };
  hooks.kv_writes_visible=[self,previous_visible]() {
   auto o=self->hooks.held_operation();
   if(o.index!=self->source.index){need(bool(previous_visible),"unowned non-I36 KV completion");return previous_visible();}
   self->context();need(self->same(o),"I36 completion changed held literal");
   return self->visible(); // never record READY or SU output observation alone
  };
 }
 void prepare() {
  try {
   need(!fault()&&prepared!=runtime.cycle(),"I36 writer fault/duplicate prepare");
   prepared=runtime.cycle();leaf.clk=0;leaf.su_go=0;leaf.kv_we={};old_accept=false;
   const auto&su=hooks.native();
   // Retain the actual I36 idle observation through unrelated later SU work.
   if(accepted&&visible()&&su.idle)origin_idle_seen=true;
   if(hooks.accepts_on_current_shared_edge()) {
    auto o=hooks.held_operation();
    if(o.index==source.index) {
     context();need(same(o)&&!accepted&&su.go&&su.ready,"I36 duplicate/non-native SU acceptance");
     auto dy=hooks.actual_dynamic(4);
     need(dy&&*dy==su.i_orow&&su.i_orow==1048575&&su.i_dst==3&&
          su.i_asrc==0&&su.i_abase==94496&&su.i_asi==1&&su.i_nin==128&&su.i_nout==1&&
          su.i_obase==0,"I36 actual source input/position/IK namespace mismatch");
     position=su.i_orow;old_accept=true;leaf.su_go=1;
     leaf.i_dst=su.i_dst;leaf.i_obase=su.i_obase;leaf.i_orow=su.i_orow;
     leaf.i_nout=su.i_nout;leaf.i_kdim=su.i_nin;
    }
   }
   if(accepted&&!visible()) {
    context();need(same(hooks.held_operation()),"I36 lost source owner before native write ACK");
    leaf.kv_we=su.kv_we;leaf.kv_waddr=su.kv_waddr;leaf.kv_wdata=su.kv_wdata;
   }
   leaf.eval();
  }catch(...){stopped=true;throw;}
 }
 void rising(bool released) {
  try {
   need(prepared==runtime.cycle(),"I36 missing shared pre-edge prepare");
   need(released||!accepted,"reset loses accepted I36 current-key publication");
   if(released) {
    if(old_accept)accepted=true;
    if(accepted) {
     const uint64_t base=uint64_t(leaf.i_obase)+uint64_t(position>>4)*128*16+(position&15);
     for(unsigned q=0;q<256;q++)if(bits(leaf.kv_we,q,1)) {
      const uint64_t address=bits(leaf.kv_waddr,q*30,30);
      need(address>=base&&address<base+128*16&&(address-base)%16==0,
           "I36 native KV strobe outside accepted key row");
      const unsigned element=(address-base)/16;
      need(!captured.test(element),"I36 duplicate native KV element");captured.set(element);
     }
    }
   }
   leaf.rst_n=released;leaf.clk=1;leaf.eval();need(!leaf.fault,"native I36 enc32 writer fault");
  }catch(...){stopped=true;throw;}
 }
 void join(VDsromS81IndexHbm&m) {
  need(m.contextp()==runtime.context,"I36 writer/backend context mismatch");
  // Literal SU/encoder coordinates remain GLOBAL POS. Only the released
  // rank3 backend record coordinate is translated to its contiguous quarter.
  // Codes/scales/address strobes are never re-encoded or renumbered here.
  if(leaf.w_v)need(leaf.w_csec==position&&position==1048575,
                   "current record lost canonical global position");
  m.w_v=leaf.w_v;m.w_csec=leaf.w_v?leaf.w_csec-3u*262144u:0;m.w_ssec=leaf.w_ssec;
  m.w_codes=leaf.w_codes;m.w_scales=leaf.w_scales;m.w_sslot=leaf.w_sslot;
  m.eval();leaf.w_rdy=m.w_rdy;leaf.eval();
 }
};
L20IndexWriter::L20IndexWriter(DsromS81MinimumRuntime&r,uint64_t id,DsromS81NativeSuPorts&h,
 std::shared_ptr<NativeIndexHbm>b,const DsromS81PrefixOperation&o)
 :impl(std::make_shared<Impl>(r,id,h,std::move(b),o)){impl->bind_sink();}
VDsromS81IndexWriter& L20IndexWriter::native()const{return impl->leaf;}
void L20IndexWriter::join_backend(VDsromS81IndexHbm&m)const{impl->join(m);}
bool L20IndexWriter::source_idle()const{return impl->idle();}
bool L20IndexWriter::fault()const{return impl->fault();}
DsromS81MinimumParticipant L20IndexWriter::participant()const {
 auto p=impl;return {"native-L20-I36-SU-index-encoder",
 [p](const auto&){p->prepare();},[p](bool r){p->rising(r);},
 [p](bool r){p->leaf.rst_n=r;p->leaf.clk=0;p->leaf.eval();},[p]{return p->fault();}};
}
}
