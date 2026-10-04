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
#include <cstdlib>
#include <deque>
#include <fstream>
#include <map>
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
        // Explicit SIM_ONLY source-calendar fallback, not native lifecycle RTL.
        std::optional<DsromS81PrefixOperation> source_op;
        std::vector<uint32_t> prime_rows;
        unsigned prime_cursor=0,user=0;
        uint32_t region_base=0,region_count=0;
        uint16_t source_tag=0;
        bool start_accepted=false,source_go=false,window_finished=false;
        bool old_prime=false,old_start=false,old_window_done=false,old_source_done=false;
        bool sim_descriptor=false;

    };
    std::array<Rank,4> ranks;
    std::array<L20NativeCkv,4> ckv;
    std::function<void(const std::array<L20NativeCkv,4>&)> tp4;
    struct Row {long due=0;uint32_t rank=0,gid=0;std::array<uint32_t,72> words{};};
    std::array<std::array<std::deque<Row>,4>,4> rows;
    std::array<Row,4> tx_rows{};
    std::array<bool,4> tx_accept{};
    std::array<std::array<bool,4>,4> rx_accept{};
    DsromS81MinimumParticipant sim_transport;
    bool joining=false,stopped=false;
    bool sim_only=false;
    bool services_quiet(unsigned i)const {
        const auto& r=ranks[i];
        return !r.phase->ckv_ph&&!r.phase->ckv_job_pend&&
            std::visit([](const auto& c){return !c->own_pending&&c->reuse_ready&&
                !c->vm_busy&&!c->kv_v&&!c->job_v&&!c->fault;},ckv[i]);
    }
    void load_prime(Rank& r) {
        std::ifstream cfg(r.b.prior_hbm_directory+"/cfg.txt");
        std::map<std::string,uint32_t> values;std::string key,value;
        while(cfg>>key>>value)values[key]=uint32_t(std::stoul(value,nullptr,0));
        need(cfg.eof()&&values.at("pos")==1048575&&values.at("window_region_valid")==1,
             "SIM_ONLY KV needs actual target source configuration");
        r.user=values.at("window_prime_user");
        need(r.user==values.at("user")&&r.user<1024,"KV source user mismatch");
        r.region_base=values.at("window_region_base");r.region_count=values.at("window_region_count");
        need(r.region_base==0x40000&&r.region_count==2176,"KV history source region mismatch");
        std::ifstream prime(r.b.prior_hbm_directory+"/prime.txt");uint32_t row;
        while(prime>>row)r.prime_rows.push_back(row);
        need(prime.eof()&&r.prime_rows.size()==127,"KV requires 127 actual prior prime rows");
        for(unsigned j=0;j<127;j++)need(r.prime_rows[j]==1048448+j,"KV prime must exclude current row");
    }
    void source_join(unsigned i) {
        auto& r=ranks[i];auto& w=*r.window;
        w.region_base_sector=r.region_base;w.region_sector_count=r.region_count;
        w.prime_user=r.user;w.blk_user=r.user;w.start_user=r.user;
        const bool admitted=r.b.runtime->identity&&*r.b.runtime->identity==r.b.identity;
        w.prime_v=admitted&&r.prime_cursor<r.prime_rows.size();
        if(w.prime_v)w.prime_row=r.prime_rows[r.prime_cursor];
        w.start_first=1048448;w.start_count=128;
        w.start_v=admitted&&r.source_op&&r.prime_cursor==127&&!r.start_accepted;
        // Actual source producer index is only a SIM_ONLY captured tag. No
        // claim that this is the unexported native desc_gen signal.
        w.retain_generation=r.source_tag;
        w.retain_qk=0;w.retain_pv=0;w.retain_complete=0;w.retain_invalidate=0;
    }
    void transport_join() {
        const long cycle=ranks[0].b.runtime->cycle();
        for(const auto& r:ranks)need(r.b.runtime->cycle()==cycle,"TP4 ranks must share one host edge");
        for(unsigned s=0;s<4;s++)std::visit([&](auto& c){
            bool capacity=true;
            for(unsigned d=0;d<4;d++)if(d!=s)capacity=capacity&&rows[d][s].size()<512;
            c->ag_tx_ready=capacity;
        },ckv[s]);
        for(unsigned d=0;d<4;d++)std::visit([&](auto& c){
            c->ag_rx_valid=0;c->ag_rx_rank=0;c->ag_rx_gid=0;
            unsigned slot=0;
            for(unsigned s=0;s<4;s++)if(s!=d){
                const auto& q=rows[d][s];
                if(!q.empty()&&q.front().due<=cycle){const auto& row=q.front();
                    c->ag_rx_valid|=1u<<slot;c->ag_rx_rank|=row.rank<<(10*slot);
                    c->ag_rx_gid|=uint64_t(row.gid)<<(21*slot);
                    std::copy(row.words.begin(),row.words.end(),c->ag_rx_row.data()+72*slot);
                }
                ++slot;
            }
        },ckv[d]);
    }

    explicit Impl(std::array<L20KvRankBinding,4> b,
        std::function<void(const std::array<L20NativeCkv,4>&)> transport):tp4(std::move(transport)) {
        const char* opt=std::getenv("DSROM_S81_SIM_ONLY_KV_SOURCE");
        sim_only=opt&&std::string(opt)=="1";
        need(bool(tp4)||sim_only,"L20 KV requires actual TP4 transport or explicit SIM_ONLY source fallback");
        for(unsigned i=0;i<4;i++){
            auto& r=ranks[i];r.b=std::move(b[i]);auto& v=r.b;
            need(v.runtime&&v.runtime->context&&v.runtime->cycle&&!v.runtime->identity&&
                 v.runtime->rank==int(i)&&v.runtime->stage==37&&v.identity<(1ull<<47)&&
                 v.publication&&v.io.read_word&&v.io.span_lease&&v.io.offer&&v.io.visible&&
                 v.su&&v.quantizer&&v.adapter&&v.endpoint&&
                 ((v.native_generation&&v.join_window_owner)||sim_only)&&v.selected_ids_published&&v.source_dynamic&&
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
            if(sim_only&&v.descriptor.participant.name.empty()){
                need(!v.native_generation&&!v.join_window_owner,
                     "SIM_ONLY fallback cannot overwrite partial actual descriptor binding");
                r.sim_descriptor=true;load_prime(r);
            }
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
            // The cut feeds native endpoint credit back into the adapter.
            // Settle that feedback with the phase before provider.prepare
            // captures OLD accept; no clock edge or credit is generated here.
            for(unsigned settle=0;settle<64;settle++){
                r.provider->wire_selected_attention(*b.adapter,*r.phase,*c);
                const bool ready=b.adapter->packed_kv_ready;
                r.cut->join(); // LAST in each low-edge source/cut join.
                if(bool(b.adapter->packed_kv_ready)==ready)return;
            }
            throw std::runtime_error("native packed phase/ATT ready feedback did not settle");
        },ckv[i]);
    }
    void join(){
        need(!stopped&&!joining,"L20 KV recursive/faulted join");joining=true;
        try{tp4(ckv);for(unsigned i=0;i<4;i++)join_rank(i);joining=false;}
        catch(...){joining=false;stopped=true;throw;}
    }
    void finish(){
        auto weak=weak_from_this();
        if(!tp4){
            tp4=[weak](const auto&){auto self=weak.lock();need(bool(self),"KV transport expired");self->transport_join();};
            sim_transport={"SIM_ONLY-existing-CKV-TP4-11-142-II2",
                [weak](const auto&){auto self=weak.lock();need(bool(self),"KV transport expired");
                    self->transport_join();
                    for(unsigned s=0;s<4;s++)std::visit([&](auto& c){
                        self->tx_accept[s]=c->ag_tx_valid&&c->ag_tx_ready;
                        if(self->tx_accept[s]){
                            Row row;row.rank=c->ag_tx_rank;row.gid=c->ag_tx_gid;
                            std::copy_n(c->ag_tx_row.data(),72,row.words.begin());
                            need(row.rank<512&&row.gid<=1048575,"actual CKV transport row bounds");
                            self->tx_rows[s]=row;
                        }
                    },self->ckv[s]);
                    for(unsigned d=0;d<4;d++)for(unsigned s=0;s<4;s++)if(d!=s){
                        const auto& q=self->rows[d][s];self->rx_accept[d][s]=!q.empty()&&q.front().due<=self->ranks[0].b.runtime->cycle();
                    }
                },
                [weak](bool released){auto self=weak.lock();need(bool(self),"KV transport expired");
                    if(!released){for(const auto& dst:self->rows)for(const auto& q:dst)need(q.empty(),"reset erases CKV transport debt");return;}
                    const long cycle=self->ranks[0].b.runtime->cycle();
                    for(unsigned d=0;d<4;d++)for(unsigned s=0;s<4;s++)if(d!=s){auto& q=self->rows[d][s];
                        if(self->rx_accept[d][s])q.pop_front();
                        if(self->tx_accept[s]){Row row=self->tx_rows[s];const bool pkg=(d^1)==s;
                            row.due=cycle+(pkg?11:142);
                            if(!pkg&&!q.empty())row.due=std::max(row.due,q.back().due+2);
                            need(q.size()<512,"CKV transport finite capacity exceeded");q.push_back(row);
                        }
                    }
                },[](bool){},[weak](){auto self=weak.lock();return !self||self->stopped;}};
        }
        for(unsigned i=0;i<4;i++){
            auto& source=ranks[i];
            if(source.sim_descriptor){
                source.b.native_generation=[weak,i](){auto self=weak.lock();need(bool(self),"KV source expired");return self->ranks[i].source_tag;};
                source.b.join_window_owner=[weak,i](auto&,auto&){auto self=weak.lock();need(bool(self),"KV source expired");self->source_join(i);};
                source.b.descriptor={{"SIM_ONLY-held-source-descriptor-rank"+std::to_string(i),
                    [weak,i](const auto&){auto self=weak.lock();need(bool(self),"KV source expired");auto& r=self->ranks[i];
                        self->source_join(i);r.window->eval();
                        r.old_prime=r.window->prime_v&&r.window->prime_ready;
                        r.old_start=r.window->start_v&&r.window->start_ready;
                        r.old_window_done=r.source_go&&r.window->done;
                        r.old_source_done=r.source_go&&r.window_finished&&!r.window->busy&&self->services_quiet(i)&&r.b.adapter->idle;
                    },
                    [weak,i](bool released){auto self=weak.lock();need(bool(self),"KV source expired");auto& r=self->ranks[i];
                        if(!released){need(!r.source_op,"reset erases held KV descriptor");return;}
                        if(r.old_prime)++r.prime_cursor;
                        if(r.old_start)r.start_accepted=true;
                        if(r.old_window_done)r.window_finished=true;
                        if(r.old_source_done){r.source_op.reset();r.source_go=false;r.start_accepted=false;r.window_finished=false;}
                    },[](bool){},[weak](){auto self=weak.lock();return !self||self->stopped;}},
                    [weak,i](){auto self=weak.lock();return self&&self->ranks[i].source_op&&self->ranks[i].start_accepted&&!self->stopped;},
                    [weak,i](){auto self=weak.lock();return self&&!self->ranks[i].source_op&&self->services_quiet(i)&&!self->ranks[i].window->busy;},
                    [weak,i](const auto& op){auto self=weak.lock();need(bool(self),"KV source expired");auto& r=self->ranks[i];
                        need(r.b.runtime->identity&&*r.b.runtime->identity==r.b.identity,
                             "KV source lacks actual admitted context");
                        need(op.unit==1&&op.template_sha256,"KV source needs actual QK/PV literal");
                        const std::string sha=op.template_sha256;
                        need(sha=="00bb7b6a8b1a67526169d39c1f5b0954d2dbc600f330a42af48d1c0d7c46bc65"||
                             sha=="6124df21d8de509ccbb8e0f114d2ed9776a4316dd810e92c35c0a07acfb9083a","KV source literal is not L20 QK/PV");
                        if(r.source_op)need(r.source_op->index==op.index&&r.source_op->instruction==op.instruction,"held source descriptor changed");
                        else{need(op.index<=65535,"SIM_ONLY source tag overflow");r.source_op=op;r.source_tag=uint16_t(op.index);r.window_finished=false;}
                        return r.start_accepted&&!r.source_go;
                    },
                    [weak,i](const auto& op,bool go){auto self=weak.lock();need(bool(self),"KV source expired");auto& r=self->ranks[i];
                        if(go){need(r.source_op&&r.source_op->index==op.index&&r.source_op->instruction==op.instruction&&r.start_accepted&&!r.source_go,"KV GO lacks actual held source");r.source_go=true;}
                    }};
            }

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
    if(!impl->sim_transport.name.empty())out.push_back(impl->sim_transport);
    for(auto& r:impl->ranks){out.push_back(r.provider->mux_participant(*r.mux,*r.hbm));
        out.push_back(r.hbm->participant());out.push_back(r.service);
        out.push_back(r.cut->participant());
        out.push_back(dsrom_s81_native_kv_phase_participant(*r.b.runtime,*r.phase));}
    return out; // ONE retrieval/enrollment; ME nests WINDOW and descriptor.
}
void L20KvFactory::join(){impl->join();}
bool L20KvFactory::drained()const{
    if(impl->stopped)return false;
    for(const auto& dst:impl->rows)for(const auto& q:dst)if(!q.empty())return false;
    for(const auto& r:impl->ranks)if(!r.hbm->drained()||!r.kv.idle()||!r.me.idle())return false;
    return true;
}
const std::array<L20NativeCkv,4>& L20KvFactory::services()const{return impl->ckv;}
} // namespace dsrom_s81_minimum
