#include "s81_minimum_l20_kv_factory.hpp"
#include "s81_minimum_kv.hpp"
#include "s81_minimum_hbm.hpp"
#include "s81_native_kv_phase.hpp"
#include "s81_minimum_attention_cut.hpp"
#include "s81_minimum_me_attention.hpp"
#include "VDsromAttention.h"
#include "VDsromAttEngine.h"
#include "VDsromWindowBlocks.h"
#include "VDsromPackedWindow.h"
#include "VDsromKvRopeMux.h"
#include "VDsromS81NativeKvPhase.h"
#include "VDsromS81CkvRank0.h"
#include "VDsromS81CkvRank1.h"
#include "VDsromS81CkvRank2.h"
#include "VDsromS81CkvRank3.h"
#include <algorithm>
namespace dsrom_s81_minimum {
namespace {
void need(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
using Provider=PackedKvProvider<VDsromWindowBlocks,VDsromPackedWindow>;
using Cut=DsromS81MinimumAttentionCut<VDsromAttention,VDsromAttEngine>;
bool selected_su(const VDsromSu256& su){
    return su.i_aind==2&&su.i_dst==3&&su.i_asrc==0&&su.i_aso==512;
}
}
struct L20KvFactory::Impl : std::enable_shared_from_this<Impl> {
    struct Rank {
        L20KvRankBinding b;
        std::shared_ptr<VDsromWindowBlocks> blocks;
        std::shared_ptr<VDsromPackedWindow> window;
        std::shared_ptr<VDsromKvRopeMux> mux;
        std::shared_ptr<VDsromS81NativeKvPhase> phase;
        std::shared_ptr<NativeHbm> hbm;
        std::shared_ptr<Provider> provider;
        std::shared_ptr<Cut> cut;
        DsromS81PrefixNativeEngine kv,me;
        DsromS81MinimumParticipant service;
        std::array<uint32_t,512> ids{};
        unsigned fetched=0;
        std::array<uint32_t,16> read_response{};
        bool response_pending=false;
        std::optional<DsromS81PrefixOperation> selected_op;
    };
    std::array<Rank,4> ranks;
    std::array<L20NativeCkv,4> ckv;
    std::function<void(const std::array<L20NativeCkv,4>&)> tp4;
    bool joining=false,stopped=false;
    explicit Impl(std::array<L20KvRankBinding,4> b,
        std::function<void(const std::array<L20NativeCkv,4>&)> transport):tp4(std::move(transport)) {
        need(bool(tp4),"L20 KV requires actual native TP4 transport");
        for(unsigned i=0;i<4;i++){
            auto& r=ranks[i];r.b=std::move(b[i]);auto& v=r.b;
            need(v.runtime&&v.runtime->context&&v.runtime->cycle&&!v.runtime->identity&&
                 v.runtime->rank==int(i)&&v.runtime->stage==37&&v.identity<(1ull<<47)&&
                 v.publication&&v.io.read_word&&v.io.span_lease&&v.io.offer&&v.io.visible&&
                 v.su&&v.quantizer&&v.adapter&&v.endpoint&&v.native_generation&&
                 v.join_window_owner&&v.selected_ids_published&&v.source_dynamic&&
                 !v.prior_hbm_directory.empty()&&!v.prior_ckv_directory.empty(),
                 "L20 KV missing cold actual rank/source/descriptor/history binding");
            need(v.adapter->contextp()==v.runtime->context&&v.endpoint->contextp()==v.runtime->context,
                 "L20 KV adapter/endpoint context mismatch");
            if(i)need(v.runtime!=ranks[0].b.runtime&&v.publication!=ranks[0].b.publication&&
                      v.runtime->context==ranks[0].b.runtime->context,
                      "L20 KV requires distinct rank owners sharing canonical context");
            const auto name="l20_kv_rank"+std::to_string(i);
            r.blocks=std::make_shared<VDsromWindowBlocks>(v.runtime->context,(name+"_blocks").c_str());
            r.window=std::make_shared<VDsromPackedWindow>(v.runtime->context,(name+"_window").c_str());
            r.mux=std::make_shared<VDsromKvRopeMux>(v.runtime->context,(name+"_mux").c_str());
            r.phase=std::make_shared<VDsromS81NativeKvPhase>(v.runtime->context,(name+"_phase").c_str());
            r.blocks->clk=0;r.window->clk=0;r.mux->clk=0;r.phase->clk=0;
            r.hbm=std::make_shared<NativeHbm>(*v.runtime,name+"_hbm");
            r.hbm->preload(v.prior_hbm_directory);r.hbm->preload_ckv(v.prior_ckv_directory);
            need(r.hbm->capacity_words()>=0x490000,"CKV source does not fit actual backend capacity");
            r.hbm->bind(*r.mux);
        }
        auto ctx=ranks[0].b.runtime->context;
        ckv[0]=std::make_shared<VDsromS81CkvRank0>(ctx,"l20_ckv_rank0");
        ckv[1]=std::make_shared<VDsromS81CkvRank1>(ctx,"l20_ckv_rank1");
        ckv[2]=std::make_shared<VDsromS81CkvRank2>(ctx,"l20_ckv_rank2");
        ckv[3]=std::make_shared<VDsromS81CkvRank3>(ctx,"l20_ckv_rank3");
        for(auto& v:ckv)std::visit([](auto& c){c->clk=0;},v);
    }
    bool poll_ids(unsigned i){
        auto& r=ranks[i];const auto& b=r.b;
        if(!b.selected_ids_published())return false;
        if(!b.io.span_lease(b.identity,447360,512))return false;
        if(r.fetched<512){auto v=b.io.read_word(b.identity,447360+r.fetched);
            if(!v)return false;
            need(b.io.span_lease(b.identity,447360,512),"native512 source lease lost at actual response");
            r.ids[r.fetched++]=*v;
        }
        return r.fetched==512;
    }
    void join_rank(unsigned i){
        auto& r=ranks[i];auto& b=r.b;
        need(!b.runtime->identity||*b.runtime->identity==b.identity,"L20 KV context changed");
        b.join_window_owner(*r.window,*r.blocks);
        r.provider->wire_su(*b.su,1048575);
        std::visit([&](auto& c){
            r.provider->wire_quantizer(*b.quantizer,*c);
            c->sel_v=0;
            if(b.su->accepts_on_current_shared_edge()&&selected_su(b.su->native())){
                const auto& su=b.su->native();
                need(su.i_aibase==447360&&r.fetched==512&&b.selected_ids_published()&&
                     b.io.span_lease(b.identity,447360,512),"CKV gather lacks actual global512 VM publication");
                c->sel_v=1;c->sel_vmword=447360>>4;
                r.selected_op=b.su->held_operation();
            }
            r.provider->wire_backend(*r.mux);
            r.provider->wire_selected_backend(*c,*r.mux);
            r.hbm->wire(*r.mux);
            r.provider->wire_selected_attention(*b.adapter,*r.phase,*c);
        },ckv[i]);
        r.cut->join(); // LAST: no WINDOW-only port overwrite after ATT settle.
    }
    void join(){
        need(!stopped&&!joining,"L20 KV recursive/faulted join");joining=true;
        try{tp4(ckv);for(unsigned i=0;i<4;i++)join_rank(i);joining=false;}
        catch(...){joining=false;stopped=true;throw;}
    }
    void finish(){
        auto weak=weak_from_this();
        for(unsigned i=0;i<4;i++){
            auto& r=ranks[i];
            r.provider=std::make_shared<Provider>(*r.b.runtime,*r.blocks,*r.window,r.b.native_generation,
                [weak,i](){auto self=weak.lock();need(bool(self),"L20 KV factory lifetime ended");
                    self->tp4(self->ckv);self->join_rank(i);});
            r.cut=std::make_shared<Cut>(*r.b.runtime,*r.b.adapter,*r.b.endpoint);
            r.provider->bind_su_sink(*r.b.su);
            auto window_write=r.b.su->kv_write;auto window_visible=r.b.su->kv_writes_visible;
            r.b.su->kv_write=[weak,i,window_write](const auto& leaf,const auto& op){
                auto self=weak.lock();need(bool(self),"selected KV sink owner expired");
                const auto& selected=self->ranks[i].selected_op;
                if(selected&&selected->index==op.index){
                    need(selected->instruction==op.instruction&&!leaf.fault,
                         "selected native KV writer changed literal");
                    // Existing ckv_scalar_suppress: native CKV fetch/encoder/
                    // merger owns selected rows, never reconstructed SU bits.
                }else window_write(leaf,op);
            };
            r.b.su->kv_writes_visible=[weak,i,window_visible](){
                auto self=weak.lock();need(bool(self),"selected KV sink owner expired");
                auto& rr=self->ranks[i];auto op=rr.b.su->held_operation();
                if(rr.selected_op&&rr.selected_op->index==op.index){
                    need(rr.selected_op->instruction==op.instruction&&
                         rr.b.selected_ids_published()&&rr.b.io.span_lease(rr.b.identity,447360,512),
                         "selected CKV publication lost held literal/VM lease");
                    return std::visit([](auto& c){return !c->fault&&c->rows_ready&&!c->own_pending;},self->ckv[i]);
                }
                return window_visible();
            };
            auto& owner=*std::get<3>(ckv[3]);r.provider->bind_quantizer_sink(*r.b.quantizer,owner);
            r.kv=r.provider->engine(std::move(r.b.descriptor));
            r.me=dsrom_s81_bind_minimum_me_attention(*r.b.runtime,r.b.identity,*r.b.publication,
                r.b.io,r.b.tags,r.b.adapter,r.kv,r.b.source_dynamic);
            std::visit([&](auto& c){
                auto native=r.provider->selected_participant(*c);
                // Native one-edge VM read timing, using only the positively
                // published, leased actual VM response bits staged above.
                r.service={"l20-native-ckv-rank"+std::to_string(i),native.prepare,
                    [weak,i,native](bool released){auto self=weak.lock();need(bool(self),"CKV owner expired");
                        auto& rr=self->ranks[i];std::visit([&](auto& svc){
                            rr.response_pending=released&&svc->vm_re;
                            if(rr.response_pending){
                                need(rr.fetched==512&&rr.b.io.span_lease(rr.b.identity,447360,512),"CKV native VM read lost source lease");
                                unsigned a=unsigned(svc->vm_raddr)*16;
                                need(a>=447360&&a+16<=447872,"native CKV VM read outside held global512");
                                std::copy_n(rr.ids.begin()+a-447360,16,rr.read_response.begin());
                            }
                        },self->ckv[i]);native.rising(released);},
                    [weak,i,native](bool released){native.falling(released);auto self=weak.lock();
                        need(bool(self),"CKV owner expired");auto& rr=self->ranks[i];
                        if(rr.response_pending)std::visit([&](auto& svc){
                            std::copy(rr.read_response.begin(),rr.read_response.end(),svc->vm_rq.data());
                        },self->ckv[i]);},native.fault};
            },ckv[i]);
        }
    }
};
L20KvFactory::L20KvFactory(std::array<L20KvRankBinding,4> b,
    std::function<void(const std::array<L20NativeCkv,4>&)> tp4,bool enable){
    need(enable,"L20 native KV factory is default off; explicit source enrollment required");
    impl=std::make_shared<Impl>(std::move(b),std::move(tp4));impl->finish();
}
DsromS81PrefixNativeEngine L20KvFactory::real_kv(unsigned r)const{return impl->ranks.at(r).kv;}
DsromS81PrefixNativeEngine L20KvFactory::attention(unsigned r)const{return impl->ranks.at(r).me;}
DsromS81PrefixNativeEngine L20KvFactory::bind_su(unsigned i,DsromS81PrefixNativeEngine su)const{
    auto& r=impl->ranks.at(i);auto engine=r.provider->su_engine(std::move(su),*r.b.su);
    auto self=impl;auto ready=engine.ready;auto inputs=engine.inputs_ready;auto drive=engine.drive;
    auto admitted=[self,i](){const auto& rr=self->ranks[i];const auto& native=rr.b.su->native();
        return !selected_su(native)||(rr.fetched==512&&rr.b.selected_ids_published()&&
            rr.b.io.span_lease(rr.b.identity,447360,512)&&native.i_aibase==447360);};
    engine.inputs_ready=[self,i,inputs,admitted](const auto& op){
        if(!inputs(op))return false;
        if(selected_su(self->ranks[i].b.su->native())&&!self->poll_ids(i))return false;
        return admitted();};
    engine.ready=[ready,admitted](){return ready()&&admitted();};
    engine.drive=[drive,admitted](const auto& op,bool go){if(go)need(admitted(),"CKV SU GO before native512 visibility");drive(op,go);};
    return engine;
}
std::vector<DsromS81MinimumParticipant> L20KvFactory::participants()const{
    std::vector<DsromS81MinimumParticipant> out;
    for(auto& r:impl->ranks){out.push_back(r.provider->mux_participant(*r.mux,*r.hbm));
        out.push_back(r.hbm->participant());out.push_back(r.service);
        out.push_back(r.cut->participant());
        out.push_back(dsrom_s81_native_kv_phase_participant(*r.b.runtime,*r.phase));}
    return out; // ONE retrieval/enrollment; ME nests WINDOW and descriptor.
}
void L20KvFactory::join(){impl->join();}
bool L20KvFactory::drained()const{
    if(impl->stopped)return false;
    for(const auto& r:impl->ranks)if(!r.hbm->drained()||!r.kv.idle()||!r.me.idle())return false;
    return true;
}
const std::array<L20NativeCkv,4>& L20KvFactory::services()const{return impl->ckv;}
} // namespace dsrom_s81_minimum
