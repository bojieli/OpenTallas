#pragma once
#include "s81_minimum_source_bindings.hpp"

// Required real provider exports. No weak symbols, registration singleton,
// optional dlopen, fallback engine or second runtime/VM ABI.
// Providers COPY SourceIo/Tags or retain them through their returned closures;
// this composition also retains the dependency objects for callback lifetime.
DsromS81PrefixNativeEngine dsrom_s81_bind_minimum_su256(
    DsromS81MinimumRuntime&,uint64_t,
    dsrom_s81_minimum::PrefixPublication&,const DsromS81MinimumSourceIo&,
    const DsromS81MinimumSourceTags&);

struct DsromS81MinimumHeBootstrapProvider {
    DsromS81PrefixNativeEngine he;
    DsromS81MinimumParticipant bootstrap;
    std::function<void()> start_bootstrap;
};
DsromS81MinimumHeBootstrapProvider dsrom_s81_bind_minimum_he_bootstrap(
    DsromS81MinimumRuntime&,uint64_t,
    dsrom_s81_minimum::PrefixPublication&,const DsromS81MinimumSourceIo&,
    const DsromS81MinimumSourceTags&);

// Use on an actual sampled native output, exactly ONCE per scalar, before
// offering the held batch. Retrying offer/visible MUST NOT reserve again.
// The single caller-owned reservation namespace also serves H and root writes.
inline dsrom_s81_minimum::MacroWrite dsrom_s81_capture_minimum_prefix_scalar(
    dsrom_s81_minimum::PrefixPublication& publication,
    const DsromS81MinimumSourceTags& tags,unsigned producer,
    const S81EmbeddingOutput& native_output,unsigned lane,bool actual_write) {
    if(!actual_write||!native_output.vm_valid||native_output.fault||lane>=16||
       native_output.vm_identity>=(1ull<<47)||
       uint64_t(native_output.vm_address)+lane>=(1u<<19)||!tags.record)
        throw std::runtime_error("prefix capture lacks actual native scalar and source tag reservation");
    auto command=tags.record(native_output,lane); // actual reservation FIRST
    const uint32_t address=native_output.vm_address+lane;
    if(command.source.identity!=native_output.vm_identity||
       command.source.element_address!=address||command.word.address!=(address>>4)||
       command.word.mask!=(uint16_t(1)<<(address&15))||
       command.word.data[address&15]!=native_output.vm_data[lane])
        throw std::runtime_error("source reservation changed actual native prefix payload/address");
    publication.native_scalar(producer,command,true); // immutable command witness
    return command;
}
