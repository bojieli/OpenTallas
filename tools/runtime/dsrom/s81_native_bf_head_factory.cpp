#include "s81_native_bf_head_factory.hpp"
std::unique_ptr<DsromS81NativeHeadBinding> dsrom_s81_bind_native_bf_head_producer(
    DsromS81MinimumRuntime& runtime,Vcut& actual_shared_cut,const DsromS81MinimumSourceIo& io,
    DsromS81NativeHeadByteRead released,DsromS81NativeHeadSink native_sink,bool install_source) {
    if(!io.read_word||!io.span_lease)throw std::runtime_error("actual normalized head XN SourceIo required");
    return std::make_unique<DsromS81NativeHeadBinding>(runtime,actual_shared_cut,io,std::move(released),std::move(native_sink),install_source);
}

std::unique_ptr<DsromS81NativeHeadBinding> dsrom_s81_bind_native_bf_head_producer(
    DsromS81MinimumRuntime& runtime,Vcut& actual_shared_cut,const std::array<DsromS81MinimumSourceIo,4>& rank_inputs,
    DsromS81NativeHeadByteRead released,DsromS81NativeHeadSink native_sink,bool install_source) {
    return std::make_unique<DsromS81NativeHeadBinding>(runtime,actual_shared_cut,rank_inputs,std::move(released),std::move(native_sink),install_source);
}
