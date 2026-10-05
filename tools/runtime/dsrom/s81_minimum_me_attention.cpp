#include "s81_minimum_me_attention.hpp"
#include "VDsromAttention.h"
#include "verilated.h"

// The caller borrows this SAME leaf for PackedKvProvider::wire_attention and
// the selected ATT cut before binding the existing engine. No constructor KV
// contents, descriptor, readiness, history, or alternate clock is supplied.
std::shared_ptr<VDsromAttention> dsrom_s81_create_minimum_me_attention(
    DsromS81MinimumRuntime& runtime) {
    if(!runtime.context)
        throw std::runtime_error("native ME requires the shared VerilatedContext");
    return std::make_shared<VDsromAttention>(runtime.context,"minimum_native_me_attention");
}

DsromS81PrefixNativeEngine dsrom_s81_bind_minimum_me_attention(
    DsromS81MinimumRuntime& runtime,uint64_t identity,
    dsrom_s81_minimum::PrefixPublication& publication,
    const DsromS81MinimumSourceIo& io,const DsromS81MinimumSourceTags& tags,
    std::shared_ptr<VDsromAttention> native,
    DsromS81PrefixNativeEngine real_kv,
    std::function<uint32_t(unsigned)> source_dynamic) {
    if(!native||native->contextp()!=runtime.context)
        throw std::runtime_error("ME and actual packed KV must share the canonical context");
    return dsrom_s81_bind_minimum_me_attention<VDsromAttention>(
        runtime,identity,publication,io,tags,std::move(native),
        std::move(real_kv),std::move(source_dynamic));
}
