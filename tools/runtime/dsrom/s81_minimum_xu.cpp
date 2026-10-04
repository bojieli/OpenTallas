#include "s81_minimum_xu.hpp"
#include "VDsromXu.h"
#include "verilated.h"

DsromS81PrefixNativeEngine dsrom_s81_bind_minimum_xu(
    DsromS81MinimumRuntime& runtime,uint64_t identity,
    dsrom_s81_minimum::PrefixPublication& publication,
    const DsromS81MinimumSourceIo& io,const DsromS81MinimumSourceTags& tags) {
    if(!runtime.context)throw std::runtime_error("native XU requires the shared VerilatedContext");
    auto native=std::make_shared<VDsromXu>(runtime.context,"minimum_native_xu");
    return dsrom_s81_bind_minimum_xu(runtime,identity,publication,io,tags,std::move(native));
}
