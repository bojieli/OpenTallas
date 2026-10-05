#pragma once
#include "s81_minimum_source_bindings.hpp"
#include "s81_minimum_source_tags_component.hpp"

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
    DsromS81MinimumRuntime& runtime,
    dsrom_s81_minimum::PrefixPublication& publication,
    unsigned producer,
    const S81EmbeddingOutput& native_output,unsigned lane,bool actual_write) {
    if(!actual_write||!native_output.vm_valid||native_output.fault||lane>=16||
       native_output.vm_identity>=(1ull<<47)||
       uint64_t(native_output.vm_address)+lane>=(1u<<19)||producer>=(1u<<14)||
       !runtime.identity||*runtime.identity!=native_output.vm_identity)
        throw std::runtime_error("prefix capture lacks actual native scalar and source tag reservation");
    const uint32_t address=native_output.vm_address+lane;
    // Hubble's SAME runtime-registered reservation provider, versioned by the
    // admitted literal producer. ID/address/bits alone is NOT a write version:
    // I2 and I3 can write identical bits to the same T address.
    auto command=dsrom_s81_reserve_native_scalar_tag(
        runtime,native_output.vm_identity,producer,address,native_output.vm_data[lane]);
    if(command.source.identity!=native_output.vm_identity||
       command.source.element_address!=address||command.word.address!=(address>>4)||
       command.word.mask!=(uint16_t(1)<<(address&15))||
       command.word.data[address&15]!=native_output.vm_data[lane])
        throw std::runtime_error("source reservation changed actual native prefix payload/address");
    publication.native_scalar(producer,command,true); // immutable command witness
    return command;
}
