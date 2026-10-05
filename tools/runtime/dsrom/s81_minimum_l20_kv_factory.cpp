#include "s81_minimum_l20_kv_factory.hpp"
#include "s81_minimum_kv.hpp"
#include "s81_minimum_hbm.hpp"
#include "s81_native_kv_phase.hpp"
#include "s81_minimum_attention_cut.hpp"
#include "s81_minimum_me_attention.hpp"
#include "s81_minimum_l20_bank.hpp"
#include "s81_minimum_source_tags_component.hpp"
#include "VDsromAttention.h"
#ifndef DSROM_S81_SIM_ONLY_ATT_ENDPOINT
#include "VDsromAttEngine.h"
#endif
#include "VDsromWindowBlocks.h"
#ifdef DSROM_S81_NATIVE_WINDOW_LA
#include "VDsromS81WindowLa.h"
#else
#include "VDsromPackedWindow.h"
#endif
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
using Cut=DsromS81MinimumAttentionCut<VDsromAttention,DsromS81AttentionEndpoint>;
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
#ifdef DSROM_S81_NATIVE_WINDOW_LA
            r.hbm->bind_window_la(*r.window);
#endif
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
            // The actual current QDQ4E producer is rank3 only. Every native
            // CKV service needs that same row to complete its selection/fetch
            // lifecycle; WINDOW mode1 remains bound to each rank's own QE.
            if(i!=3) {
                auto& current=*ranks[3].b.quantizer;
                if(current.native&&current.held_mode&&
                   (current.native().w_we&1u)&&current.held_mode()==3)
                    r.provider->wire_quantizer(current,*c);
            }
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
            // Backend eval settles routed responses in the mux. Refresh the
            // service pins before its OLD-edge snapshot; retaining the prior
            // mux response would repeat/drop tagged DMA sectors.
            r.provider->wire_selected_backend(*c,*r.mux);
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
                r.service={"l20-native-ckv-rank"+std::to_string(i),
                    [weak,i,native](const auto& result){auto self=weak.lock();need(bool(self),"CKV owner expired");
                        // This follows HBM.prepare in the participant order:
                        // freeze the same settled response/ready pins HBM used.
                        self->join_rank(i);native.prepare(result);},
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
namespace {
constexpr uint64_t L20_ID=uint64_t(1)<<31;
// Literal controls below are emitted verbatim from the existing canonical
// demand-r5 source, preserving its producer order and template SHA256.
const std::array<DsromS81PrefixOperation,5> l20_ops={{
{2491,3,"bf3065af3fa190fadf83e669f83d0f6fa682ba625a61642a1754d5f2a45a1b7b",{0x13u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x20000000u,0xd5c0u,0x4u,0x0u,0x0u,0x0u,0x6be0000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}},
{2492,2,"579a8e3fe686578968782d697bc50884d91cb0adbd3e70c374c39def5f7fe193",{0x22u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x4u,0x1u,0x35fu,0x400000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0xc000000u,0x0u,0x0u,0xc400000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x80000000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}},
{2509,3,"c7cb3b2c8ca7cd305f73719bcb514c513d08e0c177c15b47d01d4fd6088be0f4",{0x13u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x60000000u,0x16e20u,0x4u,0x0u,0x0u,0x0u,0x0u,0x2000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}},
{2524,2,"3c6c724aa878711f9d8d8057b931deb554e8e1fad2d6e406ae4ec785fb6141a1",{0x2u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x1f001u,0x0u,0x400002u,0x8000000u,0x6d38u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0xc000000u,0x0u,0x0u,0x7000000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x80000000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}},
{2526,1,"00bb7b6a8b1a67526169d39c1f5b0954d2dbc600f330a42af48d1c0d7c46bc65",{0x11u,0x40000000u,0x400u,0x40000u,0x80u,0x0u,0x6ce00u,0x3e72u,0xbe200001u,0x40u,0x2000u,0x2cu,0x140u,0x10002u,0x1404u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}}
}};
// Native attention continuation: unchanged canonical I61/I62/I63 words.
const std::array<DsromS81PrefixOperation,3> l20_pv_ops={{
{2532,2,"c32a2c493d38f4812518e59d75768ba2c7df6675ba68af2dcdfc60245042b816",{0xau,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x40u,0x880000u,0x800003e7u,0x400002u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x40000c0u,0xf9cu,0x100000au,0x20000000u,0x80024380u,0x60000000u,0x7a6a09eu,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x1u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}},
{2533,2,"fd6862b6c54c37a1e98e2c34589eb59367ddca17dd5c94605f80670f97ae7f33",{0x12u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x40u,0x880000u,0x800003e7u,0x400002u,0x0u,0x0u,0x400121cu,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x402c000u,0xf9cu,0x100000au,0x10000000u,0x800243c0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x1u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}},
{2534,1,"6124df21d8de509ccbb8e0f114d2ed9776a4316dd810e92c35c0a07acfb9083a",{0x100011u,0x10u,0x400u,0x200u,0x1000u,0x0u,0x7ce00u,0x488au,0x1u,0x62u,0x2800u,0x2cu,0x100u,0x14002u,0x1004u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}}
}};
// Bounded native HC-post SU suffix: producer IDs come from
// CanonicalS81Execution.target_native_operation(), including non-PC nodes.
// Every input lease must come from its real preceding stage publication.
const std::array<DsromS81PrefixOperation,4> l20_h_attn_ops={{
{2544,2,"0340540b59791ac6d7d7b82923baf3ed9e435d7bb73b904e3422554ed6e84e5f",{0x2u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x10u,0xau,0x0u,0x400000u,0x0u,0x0u,0x4000a0au,0x0u,0x0u,0xa00u,0x8000000u,0x0u,0x28290u,0x1u,0x0u,0x4004840u,0x500u,0x1000050u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x80000000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}},
{2545,2,"6221c07f4f6e43f73ad3d59203b695439613fc16a77fe94642fa4806af78b4e0",{0x12u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x10u,0xau,0xa0u,0x400000u,0x0u,0x80000000u,0x4000a0au,0x0u,0x0u,0x2800u,0x8000280u,0x0u,0x0u,0x0u,0x0u,0x4008040u,0x500u,0x1000050u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x80000000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}},
{2546,2,"fab801f2bcbcd4cdff06867c95bb963c9d1dd59a7416dd7a5460a4ad3322804d",{0x2u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x10u,0xau,0xf0u,0x400000u,0x0u,0xc0000000u,0x4000a0au,0x0u,0x0u,0x2800u,0x8000280u,0x0u,0x0u,0x0u,0x0u,0x4008040u,0x500u,0x1000050u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x80000000u,0x2800u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}},
{2547,2,"b697342bd2e9299a0cc2a141a25b26c011f4830af680c74cd7ec21357c5fd820",{0x2u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x10u,0x8000000au,0x528u,0x400000u,0x0u,0x0u,0x4000a08u,0x0u,0x0u,0x2800u,0x8000280u,0x0u,0x0u,0x0u,0x0u,0x6008040u,0x0u,0x1000050u,0x50000000u,0x14000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0xa03u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}},
}};
const std::array<DsromS81PrefixOperation,4> l20_h_ffn_ops={{
{2610,2,"d91ce407da76d3fbd7607f4e02e446e63f8b05821a30bb9f456dfbd476ba53e9",{0x2u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x10u,0xau,0x0u,0x400000u,0x0u,0x0u,0x4000a10u,0x0u,0x0u,0xa00u,0x8000000u,0x0u,0x28410u,0x1u,0x0u,0x4004840u,0x500u,0x1000050u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x80000000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}},
{2611,2,"1565e904b8ca8bdbd1c1118046fdb649d6a0bf9d1b629b5ec032decc6a0542a0",{0x12u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x10u,0xau,0xa0u,0x400000u,0x0u,0x80000000u,0x4000a10u,0x0u,0x0u,0x2800u,0x8000280u,0x0u,0x0u,0x0u,0x0u,0x4008040u,0x500u,0x1000050u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x80000000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}},
{2612,2,"c60f0f4efd0f3401b2ecb779c588bc675143deb557a953395563fa563c3c05e5",{0x2u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x10u,0xau,0xf0u,0x400000u,0x0u,0xc0000000u,0x4000a10u,0x0u,0x0u,0x2800u,0x8000280u,0x0u,0x0u,0x0u,0x0u,0x4008040u,0x500u,0x1000050u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x80000000u,0x2800u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}},
{2613,2,"8aa055e9953fb574d1c9505c6c0d3283c4db8e96c4d2f3d38ca9a778a7411c63",{0x2u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x10u,0x8000000au,0x19f7u,0x400000u,0x0u,0x0u,0x4000a0eu,0x0u,0x0u,0x2800u,0x8000280u,0x0u,0x0u,0x0u,0x0u,0x6008040u,0x0u,0x1000050u,0x50000000u,0x14000u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0xa03u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u,0x0u}},
}};
uint32_t op_bits(const DsromS81PrefixOperation& op,unsigned off,unsigned n){
    uint32_t v=0;for(unsigned j=0;j<n;j++)v|=((op.instruction[(off+j)/32]>>((off+j)%32))&1u)<<j;return v;
}
uint32_t l20_dynamic(unsigned d){
    // Captured L20 target calendar: POS=1048575, WINDOW128, selected512.
    switch(d){case 0:return 0;case 16:return 1048575u<<9;
        case 28:return 128;case 31:return 512;case 34:return 640;
        case 47:return 20;case 49:return 127;
        default:throw std::runtime_error("I55 caller requested unbound source DYN");}
}
struct L20AttentionRun : std::enable_shared_from_this<L20AttentionRun> {
    struct Input {unsigned producer;uint32_t base;std::vector<uint32_t> data;};
    struct Rank {
        DsromS81MinimumRuntime runtime{};
        std::unique_ptr<DsromS81MinimumL20Bank> bank;
        std::shared_ptr<VDsromAttention> adapter;
        std::shared_ptr<DsromS81AttentionEndpoint> endpoint;
        std::shared_ptr<VDsromSu256> command;
        DsromS81NativeSuPorts su_ports;
        DsromS81NativeQeQuantizerPorts qe_ports;
        DsromS81PrefixNativeEngine qe,su,me,softmax;
        DsromS81NativeSuPorts softmax_ports;
        std::optional<DsromS81PrefixOperation> su_op;
        bool su_go=false,su_accepted=false;
        std::vector<Input> inputs;size_t input=0,offset=0;
        bool input_held=false,input_offered=false,h_offered=false,h_visible=false;
        S81EmbeddingOutput out{},h{};unsigned count=0;
        bool accepted=false,go=false;
    };
    DsromS81MinimumRuntime& host;
    std::array<Rank,4> ranks;
    std::shared_ptr<L20KvFactory> factory;
    unsigned phase=0;
    bool finished=false,pv=false;
    unsigned h_pc=0; // optional native HC-post suffix; 0 preserves I55/PV
    bool pre_i75_boundary=false; // explicit combined native-PV-based SIM_ONLY boundary
    long first_h=-1;
    long first_qk=-1,last=-1,first_pv=-1;
    static std::vector<uint32_t> load(const std::string& file,size_t count){
        std::ifstream f(file,std::ios::binary);need(bool(f),"actual produced ATT input missing");
        std::vector<unsigned char> b(count*4);f.read(reinterpret_cast<char*>(b.data()),b.size());
        need(size_t(f.gcount())==b.size()&&f.peek()==std::char_traits<char>::eof(),"ATT input extent mismatch");
        std::vector<uint32_t> v(count);for(size_t i=0;i<count;i++)v[i]=uint32_t(b[4*i])|
            uint32_t(b[4*i+1])<<8|uint32_t(b[4*i+2])<<16|uint32_t(b[4*i+3])<<24;return v;
    }
    explicit L20AttentionRun(DsromS81MinimumRuntime& runtime):host(runtime){
        need(host.stage==37&&host.rank==0&&host.bf16&&host.context&&!host.identity&&host.cycle()==0,
             "I55 requires cold actual stage37 rank0 BF caller");
        const char* dir=std::getenv("DSROM_S81_NATIVE_L20_ATT_INPUT");
        const char* history=std::getenv("DSROM_S81_NATIVE_L20_ATT_HISTORY");
        // Native I19/I23 outputs are fresh input data, not carried VM leases.
        // Both are required together; historical SIM_ONLY boundary stays opt-out.
        const char* q_rope=std::getenv("DSROM_S81_NATIVE_L20_Q_ROPE_INPUT");
        const char* k_rope=std::getenv("DSROM_S81_NATIVE_L20_K_ROPE_INPUT");
        const bool native_rope=q_rope&&*q_rope;
        need(native_rope==bool(k_rope&&*k_rope),
             "ATT native RoPE carry requires both actual I19 KVN and I23 Q directories");
        const char* sim=std::getenv("DSROM_S81_SIM_ONLY_KV_SOURCE");
        need(dir&&*dir&&history&&*history&&sim&&std::string(sim)=="1",
             "I55 needs actual operand/history directories and explicit SIM_ONLY source boundary");
        const char* continuation=std::getenv("DSROM_S81_NATIVE_L20_ATT_PV");
        need(!continuation||std::string(continuation)=="0"||std::string(continuation)=="1",
             "ATT_PV selector must be explicit 0 or 1");
        pv=continuation&&std::string(continuation)=="1";
        const char* h=std::getenv("DSROM_S81_NATIVE_L20_ATT_SU_PC");
        need(!h||std::string(h)=="0"||std::string(h)=="76"||std::string(h)=="142",
             "ATT SU suffix must be 0, 76 or 142");
        if(h&&std::string(h)!="0")h_pc=std::string(h)=="76"?76:142;
        need(!h_pc||pv,"native HC-post suffix requires actual QK/SU/PV path");
        // Requires Arch's combined export derived from actual native PV. The
        // standalone minimum export is not an implicit combined-stage input.
        const char* pre_i75=std::getenv("DSROM_S81_NATIVE_L20_ATT_PRE_I75_INPUT");
        pre_i75_boundary=pre_i75&&*pre_i75;
        need(!pre_i75_boundary||(pv&&h_pc==76),
             "combined pre-I75 boundary requires native PV and PC76");
        std::array<L20KvRankBinding,4> bindings;
        for(unsigned i=0;i<4;i++){
            auto& r=ranks[i];r.runtime=host;r.runtime.rank=i;r.runtime.participants.clear();
            auto vm=std::make_shared<Vnative_vm>(host.context,("I55_vm_rank"+std::to_string(i)).c_str());
            r.bank=std::make_unique<DsromS81MinimumL20Bank>(r.runtime,L20_ID,vm,
                dsrom_s81_bind_minimum_source_tags(r.runtime,L20_ID),h_pc!=0);
            auto name=std::to_string(i);
            r.inputs={{2490,54720,load(native_rope?
                          std::string(k_rope)+"/native_L20_I19_rank"+name+".u32":
                          std::string(dir)+"/I20.KVN_rank"+name+".u32",512)},
                      {2508,93728,load(std::string(dir)+"/I38.LAT_rank"+name+".u32",512)},
                      {2518,447360,load(std::string(dir)+"/I47.SELG_rank"+name+".u32",512)},
                      // Canonical Q's last writer is I23, not I54/KR. Preserve
                      // the old boundary namespace only for frozen old callers.
                      {native_rope?2494u:2525u,55744,load(native_rope?
                          std::string(q_rope)+"/native_L20_I23_rank"+name+".u32":
                          std::string(dir)+"/I55.Q_rank"+name+".u32",8192)}};
            if(native_rope)fprintf(stderr,
                "ATT_ROPE_CARRY rank=%u KVN=I19:2490 Q=I23:2494 fresh_VM_ACK_required=1 "
                "I18_coefficients=SIM_ONLY LAT_SELG=SIM_ONLY_boundary native_prefetch_timing=0\n",i);
            for(const auto& in:r.inputs)r.bank->publication().enroll_literal(in.producer,{{in.base,uint32_t(in.data.size())}});
            if(pre_i75_boundary)r.bank->entry().install_sim_only_pre_i75(pre_i75);
            // The boundary owns the actual I74 T publication. Do not enroll
            // or execute I73/I74 again; I75 still computes its native rewrite.
            if(h_pc)for(unsigned k=pre_i75_boundary?2:0;k<3;++k)
                r.bank->publication().enroll_literal(h_operations()[k].index,{{20480,20480}});
            r.bank->publication().enroll_literal(l20_ops[0].index,{{55232,512}});
            r.bank->publication().enroll_literal(l20_ops[1].index,{});
            r.bank->publication().enroll_literal(l20_ops[2].index,{});
            r.bank->publication().enroll_literal(l20_ops[3].index,{});
            r.bank->publication().enroll_literal(l20_ops[4].index,{{63936,10240}});
            if(pv){
                r.bank->publication().enroll_literal(l20_pv_ops[0].index,{{63936,10240},{74176,16}});
                r.bank->publication().enroll_literal(l20_pv_ops[1].index,{{63936,10240},{74208,16}});
                r.bank->publication().enroll_literal(l20_pv_ops[2].index,{{74272,8192}});
                r.softmax=dsrom_s81_bind_minimum_su256(r.runtime,L20_ID,r.bank->publication(),
                    r.bank->io(),r.bank->tags(),r.softmax_ports);
                r.softmax_ports.actual_dynamic=[](unsigned d)->std::optional<uint32_t>{return l20_dynamic(d);};
            }
            // Native vec requests all four ports even for a copy. Initial H16
            // is the existing released seeded entry, published through real ACK.
            const auto h=load("/home/ubuntu/w17work/isa/scratch_s20260930/images/ctx1048576_L20_r0/io.h_in.bin",20480);
            r.h.vm_valid=1;r.h.vm_identity=L20_ID;r.h.vm_address=0;
            std::copy_n(h.begin(),16,r.h.vm_data);
            r.command=std::make_shared<VDsromSu256>(host.context,("SIM_ONLY_source_KVT_command_rank"+name).c_str());
            r.su_ports.native=[&r]()->const VDsromSu256&{return *r.command;};
            r.su_ports.held_operation=[&r](){need(bool(r.su_op),"KVT command lacks actual literal");return *r.su_op;};
            r.su_ports.accepts_on_current_shared_edge=[&r](){return r.su_go&&!r.su_accepted;};
            r.qe=dsrom_s81_bind_minimum_qe_quantizer(r.runtime,L20_ID,r.bank->publication(),r.bank->io(),r.qe_ports);
            r.qe_ports.actual_dynamic=[](unsigned d)->std::optional<uint32_t>{return l20_dynamic(d);};
            r.adapter=dsrom_s81_create_minimum_me_attention(r.runtime);
            r.endpoint=std::make_shared<DsromS81AttentionEndpoint>(host.context,("I55_endpoint_rank"+name).c_str());
            auto& b=bindings[i];b.runtime=&r.runtime;b.identity=L20_ID;b.publication=&r.bank->publication();
            b.io=r.bank->io();b.tags=r.bank->tags();b.su=&r.su_ports;b.quantizer=&r.qe_ports;
            b.adapter=r.adapter;b.endpoint=r.endpoint;b.source_dynamic=l20_dynamic;
            b.selected_ids_published=[&r](){return r.bank->publication().complete(L20_ID,2518)&&r.bank->io().span_lease(L20_ID,447360,512);};
            b.prior_hbm_directory=std::string(history)+"/r"+name;b.prior_ckv_directory=b.prior_hbm_directory;
        }
        factory=std::make_shared<L20KvFactory>(std::move(bindings),std::function<void(const std::array<L20NativeCkv,4>&)>{},true);
    }
    void finish_bindings(){
        auto weak=weak_from_this();
        for(unsigned i=0;i<4;i++){
            auto& r=ranks[i];
            // I21/I53 scalar paths are suppressed in the original packed core.
            // This explicit SIM_ONLY command boundary issues the SAME literal
            // controls; actual WINDOW/CKV models do every data move/commit.
            DsromS81PrefixNativeEngine command={{"SIM_ONLY-source-KVT-command-rank"+std::to_string(i),
                [](const auto&){},[weak,i](bool released){auto s=weak.lock();need(bool(s),"I55 caller expired");
                    auto& r=s->ranks[i];if(released&&r.su_go){r.su_accepted=true;r.su_go=false;}},
                [](bool){},[weak](){return weak.expired();}},
                [&r](){return r.su_op&&!r.su_accepted;},
                [&r](){return !r.su_op||(r.su_accepted&&r.su_ports.kv_writes_visible());},
                [&r](const auto& op){
                    need(op.index==l20_ops[1].index||op.index==l20_ops[3].index,"I55 SIM_ONLY command requires I21/I53");
                    if(r.su_op&&r.su_op->index!=op.index){need(r.su_accepted&&r.su_ports.kv_writes_visible(),"KVT rebind loses native debt");r.su_accepted=false;}
                    r.su_op=op;auto& c=*r.command;
                    c.i_dst=op_bits(op,986,2);c.i_asrc=op_bits(op,536,2);
                    c.i_abase=op_bits(op,538,30);c.i_obase=op_bits(op,988,30);
                    c.i_nin=op_bits(op,503,21);c.i_nout=op_bits(op,482,21)+l20_dynamic(op_bits(op,524,6));
                    c.i_aind=op_bits(op,634,2);c.i_aibase=op_bits(op,636,30);c.i_aso=op_bits(op,568,30);
                    c.i_orow=l20_dynamic(op_bits(op,1078,6));
                    return !r.su_accepted;
                },[&r](const auto& op,bool go){if(go)need(r.su_op&&r.su_op->instruction==op.instruction&&!r.su_accepted,"KVT GO lacks held source");r.su_go=go;}};
            r.su=factory->bind_su(i,std::move(command));r.me=factory->attention(i);
            host.participants.push_back(r.bank->bank_participant());
            if(h_pc)host.participants.push_back(r.bank->entry_participant());
        }
        host.participants.push_back({"I55-four-rank-source-control",
            [weak](const auto&){auto s=weak.lock();need(bool(s),"I55 source expired");s->prepare_controls();},
            [weak](bool released){auto s=weak.lock();need(bool(s),"I55 source expired");if(released)s->accepted_controls();},
            [](bool){},[weak](){return weak.expired();}});
        // All OLD inputs are sampled before any rising; command acceptance is
        // frozen by provider before SIM_ONLY command participant retires GO.
        for(auto& r:ranks){host.participants.push_back(r.me.participant);host.participants.push_back(r.qe.participant);host.participants.push_back(r.su.participant);
            if(pv)host.participants.push_back(r.softmax.participant);}
        for(auto p:factory->participants())host.participants.push_back(std::move(p));
        host.publication_ready=[weak](uint64_t id){auto s=weak.lock();if(!s||id!=L20_ID)return false;for(auto& r:s->ranks)if(r.bank->fault())return false;return true;};
        host.publication_drained=[weak](uint64_t id){auto s=weak.lock();return s&&id==L20_ID&&s->finished&&s->factory->drained();};
    }
    DsromS81PrefixNativeEngine& active(unsigned i){
        if(phase==6||phase==7||phase>=9)return ranks[i].softmax;
        return phase==1||phase==3?ranks[i].qe:phase==2||phase==4?ranks[i].su:ranks[i].me;
    }
    const std::array<DsromS81PrefixOperation,4>& h_operations()const {
        need(h_pc==76||h_pc==142,"native HC-post source selection absent");
        return h_pc==76?l20_h_attn_ops:l20_h_ffn_ops;
    }
    unsigned terminal_phase()const{return h_pc?12:pv?8:5;}
    const DsromS81PrefixOperation& operation()const{
        if(phase>=9)return h_operations().at(phase-9);
        return phase<=5?l20_ops.at(phase-1):l20_pv_ops.at(phase-6);
    }
    bool continuation_visible()const{
        for(const auto& r:ranks)if(!r.bank->publication().complete(L20_ID,operation().index))return false;
        return true;
    }
    void prepare_controls(){
        if(phase==0||phase>terminal_phase())return;
        for(unsigned i=0;i<4;i++){
            auto& r=ranks[i];r.go=false;if(phase==3&&i!=3)continue;
            auto& e=active(i);const auto& op=operation();
            if(!r.accepted) {
                // I139 consumes the H version actually produced by I76, not
                // the cold initial image. Never infer it from elapsed phases.
                if(phase==9&&h_pc==142&&
                   (!r.bank->publication().complete(L20_ID,l20_h_attn_ops.back().index)||
                    !r.bank->io().span_lease(L20_ID,0,20480)))continue;
                r.go=e.inputs_ready(op)&&e.ready();
                if(phase==12)r.go=r.go&&e.idle()&&r.bank->native_target().mutable_write_drained();
            }
            e.drive(op,r.go);
        }
    }
    void accepted_controls(){
        if(phase==0||phase>terminal_phase())return;
        for(auto& r:ranks)if(r.go){
            if(phase==12)r.bank->admit_mutable_h_writer(operation().index,{{0,20480},{40960,1}},
                r.go&&active(r.runtime.rank).ready(),
                active(r.runtime.rank).idle()&&r.bank->native_target().mutable_write_drained());
            else r.bank->publication().begin(L20_ID,operation().index);
            r.accepted=true;
        }
        if(phase==5&&first_qk<0)for(auto& r:ranks)if(r.go){first_qk=host.cycle();break;}
        if(phase==8&&first_pv<0)for(auto& r:ranks)if(r.go){first_pv=host.cycle();break;}
        if(phase==12&&first_h<0)for(auto& r:ranks)if(r.go){first_h=host.cycle();break;}
    }
    void advance_inputs(){
        for(auto& r:ranks){
            if(!r.h_visible){
                if(h_pc)r.h_visible=r.bank->inputs_visible(); // existing native TargetEntry ACKs
                else {
                    if(!r.h_offered)r.h_offered=r.bank->embedding_sink().offer(r.h);
                    if(r.h_offered&&r.bank->embedding_sink().visible(r.h))r.h_visible=true;
                }
                continue;
            }
            if(r.input==r.inputs.size())continue;
            const auto& in=r.inputs[r.input];
            if(!r.input_held){if(!r.offset)r.bank->publication().begin(L20_ID,in.producer);
                r.count=std::min<size_t>(16,in.data.size()-r.offset);r.out={};r.out.vm_valid=1;r.out.vm_identity=L20_ID;r.out.vm_address=in.base+r.offset;
                for(unsigned j=0;j<r.count;j++){r.out.vm_data[j]=in.data[r.offset+j];
                    auto c=dsrom_s81_reserve_native_scalar_tag(r.runtime,L20_ID,in.producer,r.out.vm_address+j,r.out.vm_data[j]);
                    r.bank->publication().native_scalar(in.producer,c,true);}
                r.input_held=true;r.input_offered=false;
            }
            if(!r.input_offered){r.input_offered=r.bank->io().offer(r.out,r.count);continue;}
            if(!r.bank->io().visible(r.out,r.count))continue;
            r.offset+=r.count;r.input_held=false;r.input_offered=false;
            if(r.offset==in.data.size()){need(r.bank->publication().complete(L20_ID,in.producer),"I55 operand lacks native ACK");r.offset=0;++r.input;}
        }
    }
    void advance(){
        if(phase==0){advance_inputs();for(auto& r:ranks)if(r.input!=r.inputs.size()||!r.h_visible)return;phase=1;}
        else {
            bool complete=true;for(unsigned i=0;i<4;i++)if(!(phase==3&&i!=3))complete=complete&&ranks[i].accepted&&active(i).idle();
            // QDQ mode3 ownership intentionally spans the subsequent selected
            // gather; waiting its own_visible before I53 would deadlock.
            if(phase==3)complete=ranks[3].accepted;
            if(!complete)return;
            for(unsigned i=0;i<4;i++)if(!(phase==3&&i!=3))active(i).drive(operation(),false);
            if(phase==4&&!ranks[3].qe.idle())return;
            if(phase==5){
                if(!factory->drained())return;
                if(!pv){finished=true;last=host.cycle();return;}
                // Scale/MAX may overwrite S only after every actual QK write
                // is positively visible and the full provider debt is drained.
                if(!continuation_visible())return;
                for(auto& r:ranks)need(r.bank->io().span_lease(L20_ID,63936,10240),
                    "native softmax lacks actual published QK score lease");
            }
            if(phase>=6&&!continuation_visible())return;
            if(phase==7)for(auto& r:ranks)
                need(r.bank->io().span_lease(L20_ID,63936,10240)&&
                     r.bank->io().span_lease(L20_ID,74208,16),
                     "PV requires native exponent outputs and sum publication");
            if(phase==8){
                if(!factory->drained())return;
                if(!h_pc){finished=true;last=host.cycle();return;}
            }
            if(phase==12){
                if(!factory->drained())return;
                for(const auto& r:ranks)if(!r.bank->native_target().mutable_write_drained()||
                    !r.bank->io().span_lease(L20_ID,0,20480))return;
                finished=true;last=host.cycle();return;
            }
            phase=(phase==8&&pre_i75_boundary)?11:phase+1;
        }
        for(auto& r:ranks){r.accepted=false;r.go=false;}
        fprintf(stderr,"I55_NATIVE_SOURCE_PHASE %u cycle=%ld\n",phase,host.cycle());
    }
};
} // namespace
int run_minimum_l20_kv(DsromS81MinimumRuntime& runtime,const char* output){
    auto source=std::make_shared<L20AttentionRun>(runtime);source->finish_bindings();
    // Retain the native owners through the host's post-return drain check.
    runtime.publication_drained=[source](uint64_t id){return id==L20_ID&&source->finished&&source->factory->drained();};
    runtime.cold_start();runtime.bind_context(L20_ID);
    for(auto& r:source->ranks){r.runtime.identity=L20_ID;
        if(source->h_pc)r.bank->initialize();} // same shared cold reset/initial-input owner
    while(!source->finished){source->advance();runtime.tick();}
    const unsigned result_base=source->h_pc?0:source->pv?74272:63936,
                   result_count=source->h_pc?20480:source->pv?8192:10240;
    const std::string result_name=source->h_pc?"native_L20_I"+std::to_string(source->h_pc)+"_rank":
                                  source->pv?"native_L20_I63_rank":"native_L20_I55_rank";
    for(unsigned i=0;i<4;i++){
        auto& r=source->ranks[i];
        if(source->pv)need(r.bank->publication().complete(L20_ID,source->h_pc?
             source->h_operations().back().index:l20_pv_ops[2].index)&&
             r.bank->io().span_lease(L20_ID,result_base,result_count),"PV export requires actual native publication/lease");
        std::ofstream f(std::string(output)+"/"+result_name+std::to_string(i)+".u32",std::ios::binary|std::ios::out);
        need(bool(f),source->pv?"I63 native PV output unavailable":"I55 score output unavailable");
        for(unsigned j=0;j<result_count;j++){std::optional<uint32_t> v;
            while(!(v=r.bank->io().read_word(L20_ID,result_base+j)))runtime.tick();
            const auto x=*v;unsigned char bytes[4]={uint8_t(x),uint8_t(x>>8),uint8_t(x>>16),uint8_t(x>>24)};
            f.write(reinterpret_cast<const char*>(bytes),4);
        }
        need(bool(f),source->pv?"I63 native PV output write failed":"I55 score output write failed");
    }
    std::ofstream f(std::string(output)+"/native_L20_ATT.tsv");
#ifdef DSROM_S81_SIM_ONLY_ATT_ENDPOINT
    const char* endpoint_math="SIM_ONLY-att-endpoint";
    const char* qk_scope="I55.SIM_ONLY-att-endpoint-QK-KV";
#else
    const char* endpoint_math="native";
    const char* qk_scope="I55.native-QK-KV";
#endif
    if(source->h_pc)
        f<<"scope\tposition\tranks\tqk_accept\tpv_accept\th_accept\tterminal\n"
         <<"QK.SU.PV."<<endpoint_math<<"-HC-post-I"<<source->h_pc<<".SIM_ONLY-source-KVT-descriptor-TP4\t1048575\t4\t"
         <<source->first_qk<<'\t'<<source->first_pv<<'\t'<<source->first_h<<'\t'<<source->last<<'\n';
    else if(source->pv)
        f<<"scope\tposition\tranks\tqk_accept\tpv_accept\tterminal\nQK.I61.I62.PV."<<endpoint_math<<".SIM_ONLY-source-KVT-descriptor-TP4\t1048575\t4\t"
         <<source->first_qk<<'\t'<<source->first_pv<<'\t'<<source->last<<'\n';
    else
    f<<"scope\tposition\tranks\tqk_accept\tterminal\n"<<qk_scope<<".SIM_ONLY-source-KVT-descriptor-TP4\t1048575\t4\t"<<source->first_qk<<'\t'<<source->last<<'\n';
    need(bool(f),"I55 terminal output unavailable");return 0;
}

} // namespace dsrom_s81_minimum
