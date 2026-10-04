#include "s81_wavefront_native_result_read.hpp"
#include <cassert>

// Native port/ReadResult boundary fixture; no controller or numerical model.
struct Ports {
    bool rst_n=true,native_result_selected=true,native_result_active=true;
    bool native_result_producer_take=false,native_result_am_any=false;
    bool native_result_end_take=false,native_result_done=false,c8_retire_v=false;
    uint32_t native_result_entry=4,native_result_pc=4,native_result_token=0,native_result_value=0;
    uint64_t native_result_identity=0,c8_retire_identity=0;
    uint32_t fault=0,c8_stage_quarantine=0,c8_write_quarantine=0,c8_write_fault=0;
};
struct NativeDie {std::unique_ptr<Ports> d=std::make_unique<Ports>();};
static bool refuses(const std::function<void()>& f){try{f();}catch(const std::runtime_error&){return true;}return false;}
int main() {
    const DsromC8SourceOffer offer{320,17,19,8,3,4,(uint64_t(3)<<31)|(uint64_t(8)<<21)|19};
    const DsromS81NativeResultTerminal terminal{offer,"released/native/head.weight/argmax",6,9};
    NativeDie die;auto& p=*die.d;p.native_result_identity=offer.identity;
    auto reader=dsrom_s81_bind_native_result_read(die,terminal,41,true);
    auto ReadResult=dsrom_s81_native_read_result_callback(reader);
    assert(!ReadResult(offer));
    // Fresh bound producer accepted at its literal PC. No result/stage credit yet.
    p.native_result_pc=6;p.native_result_producer_take=true;
    reader->sample_before_edge();reader->after_edge();assert(!ReadResult(offer));
    // Actual END/completion captures token ZERO and raw nonfinite bits unchanged.
    p.native_result_producer_take=false;p.native_result_am_any=true;
    p.native_result_pc=9;p.native_result_end_take=true;
    reader->sample_before_edge();p.native_result_done=true;
    p.native_result_token=0;p.native_result_value=0x7fc01234;reader->after_edge();
    assert(!ReadResult(offer)); // retirement still missing
    p.native_result_end_take=false;p.native_result_active=false;
    reader->sample_before_edge();p.c8_retire_v=true;p.c8_retire_identity=offer.identity;reader->after_edge();
    auto result=ReadResult(offer);assert(result&&result->request_sequence==41&&result->identity==offer.identity);
    assert(result->next_token==0&&result->next_value==0x7fc01234);
    // ReadResult holds its actual captured bits even when output ports change later.
    p.native_result_token=55;p.native_result_value=0x3f800000;
    assert(ReadResult(offer)->next_value==0x7fc01234&&ReadResult(offer)->next_token==0);
    auto foreign=offer;foreign.entry=5;assert(refuses([&]{ReadResult(foreign);}));
    reader->warm_quarantine();assert(reader->fault()&&refuses([&]{ReadResult(offer);}));
    // FIELD+END/reset/stale AMAX registers without THIS producer cannot supply output.
    NativeDie absent;absent.d->native_result_identity=offer.identity;
    auto missing=dsrom_s81_bind_native_result_read(absent,terminal,42,true);
    absent.d->native_result_pc=9;absent.d->native_result_end_take=true;
    absent.d->native_result_am_any=true;absent.d->native_result_done=true;
    assert(refuses([&]{missing->sample_before_edge();}));
    // Another producer PC must not authorize the expected terminal instruction.
    NativeDie other;other.d->native_result_identity=offer.identity;
    auto wrong=dsrom_s81_bind_native_result_read(other,terminal,43,true);
    other.d->native_result_pc=7;other.d->native_result_producer_take=true;
    wrong->sample_before_edge();wrong->after_edge();
    other.d->native_result_producer_take=false;other.d->native_result_pc=9;
    other.d->native_result_end_take=true;other.d->native_result_am_any=true;
    assert(refuses([&]{wrong->sample_before_edge();}));
    NativeDie disabled;disabled.d->native_result_selected=false;
    auto off=dsrom_s81_bind_native_result_read(disabled,terminal,44);
    assert(!(*off)(offer));
    assert(refuses([&]{dsrom_s81_bind_native_result_read(disabled,terminal,44,true);}));
}
