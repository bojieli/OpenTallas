#include "s81_minimum_prefix_providers.hpp"
#include <memory>

namespace {
struct Dependencies {
    DsromS81MinimumSourceIo io;
    DsromS81MinimumSourceTags tags;
};
void require(bool ok,const char* reason) {
    if(!ok)throw std::runtime_error(reason);
}
void check(const DsromS81MinimumParticipant& p) {
    require(!p.name.empty()&&p.prepare&&p.rising&&p.falling&&p.fault,
            "real native prefix participant required; absent provider cannot run");
}
void check(const DsromS81PrefixNativeEngine& e) {
    check(e.participant);
    require(e.ready&&e.idle&&e.inputs_ready&&e.drive,
            "actual prefix native ready/idle/operand-prefetch/GO hooks required");
}
// Keep exact input/tag closures alive even if a provider retained references
// to its supplied dependency objects. Provider model lifetime is separately
// retained by that provider's returned callbacks, never a stack-local model.
DsromS81MinimumParticipant retain(DsromS81MinimumParticipant p,
                                 std::shared_ptr<Dependencies> deps) {
    return {p.name,
        [deps,f=p.prepare](const auto& r){f(r);},
        [deps,f=p.rising](bool released){f(released);},
        [deps,f=p.falling](bool released){f(released);},
        [deps,f=p.fault](){return f();}};
}
DsromS81PrefixNativeEngine retain(DsromS81PrefixNativeEngine e,
                                 std::shared_ptr<Dependencies> deps) {
    e.participant=retain(std::move(e.participant),deps);
    e.ready=[deps,f=e.ready](){return f();};
    e.idle=[deps,f=e.idle](){return f();};
    e.inputs_ready=[deps,f=e.inputs_ready](const auto& op){return f(op);};
    e.drive=[deps,f=e.drive](const auto& op,bool go){f(op,go);};
    return e;
}
}

DsromS81MinimumPrefixBinding dsrom_s81_bind_minimum_prefix_engines(
    DsromS81MinimumRuntime& runtime,uint64_t identity,
    dsrom_s81_minimum::PrefixPublication& publication,
    const DsromS81MinimumSourceIo& io,const DsromS81MinimumSourceTags& tags) {
    require(runtime.stage==0&&identity<(1ull<<47)&&runtime.tick&&runtime.cold_start&&
            io.read_word&&io.span_lease&&io.offer&&io.visible&&tags.record&&
            tags.read_owner&&tags.root_owner&&tags.scalar_accept&&tags.read_accept,
            "canonical prefix requires actual runtime, same-VM SourceIo and one SourceTags namespace");
    require(!publication.fault(),"cannot compose quarantined prefix publication");
    auto deps=std::make_shared<Dependencies>(Dependencies{io,tags});
    const auto before=runtime.participants.size();
    // Both calls are mandatory link dependencies implemented by the assigned
    // owners. No missing-symbol substitute or second native bank is created.
    auto su=dsrom_s81_bind_minimum_su256(
        runtime,identity,publication,deps->io,deps->tags);
    auto he=dsrom_s81_bind_minimum_he_bootstrap(
        runtime,identity,publication,deps->io,deps->tags);
    require(runtime.participants.size()==before,
            "leaf factories must return participants, not separately register clocks");
    check(su);check(he.he);check(he.bootstrap);
    require(bool(he.start_bootstrap),"actual explicit native bootstrap start required");
    require(su.participant.name!=he.he.participant.name&&
            su.participant.name!=he.bootstrap.name&&
            he.he.participant.name!=he.bootstrap.name,
            "native SU/HE/bootstrap participants must have distinct owners");
    for(const auto& p:runtime.participants)
        require(p.name!=su.participant.name&&p.name!=he.he.participant.name&&
                p.name!=he.bootstrap.name,
                "native prefix provider already registered; duplicate shared edge forbidden");
    DsromS81MinimumPrefixBinding result;
    result.su=retain(std::move(su),deps);
    result.he=retain(std::move(he.he),deps);
    result.bootstrap=retain(std::move(he.bootstrap),deps);
    auto start_attempted=std::make_shared<bool>(false);
    result.start_bootstrap=[deps,&runtime,identity,start_attempted,
                            start=std::move(he.start_bootstrap)](){
        require(!*start_attempted&&runtime.identity&&*runtime.identity==identity,
                "native bootstrap arm requires exact admitted context and one start");
        // Never retry a provider that threw after accepting native work.
        // The provider itself checks shared cold reset before actual arming.
        *start_attempted=true;
        start();
    };
    return result;
}
