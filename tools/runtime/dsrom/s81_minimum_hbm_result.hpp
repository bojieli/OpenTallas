#pragma once
#include "s81_minimum_hbm_counters.hpp"
#include <cstdio>
#include <filesystem>
#include <memory>
#include <stdexcept>

namespace dsrom_s81_minimum {
// Export interval deltas from actual native observations. Read bytes are
// consumed 32-byte sectors; accepted write bytes count asserted strobes.
// Neither is a semantic FP/KV payload size. No controller peak is inferred.
inline void dsrom_s81_write_l20_hbm_result(const std::string& output,unsigned rank,
    const NativeHbmTrafficSnapshot& before,const NativeHbmTrafficSnapshot& after,
    long start_cycle,long end_cycle,uint64_t native_clock_ps) {
    if(rank>=4||start_cycle<0||end_cycle<=start_cycle||!native_clock_ps||
       !after.first_observed_cycle||!after.last_observed_cycle||
       *after.last_observed_cycle!=end_cycle-1||
       (before.last_observed_cycle&&*before.last_observed_cycle!=start_cycle-1))
        throw std::runtime_error("L20 measurement requires actual sampled interval and explicit native clock");
    auto delta=[](uint64_t a,uint64_t b) {
        if(b<a)throw std::runtime_error("native traffic counter reset inside measured L20 interval");
        return b-a;
    };
    const auto path=std::filesystem::path(output)/("L20_hbm_rank"+std::to_string(rank)+".tsv");
    std::unique_ptr<FILE,decltype(&fclose)> file(fopen(path.c_str(),"wx"),fclose);
    if(!file)throw std::runtime_error("preserve existing L20 measured traffic result");
    const long cycles=end_cycle-start_cycle;
    auto checked=[&](int n){if(n<0)throw std::runtime_error("L20 native measurement write failed");};
    checked(fprintf(file.get(),"# scope=seeded-representative-L20 position=1048575 cycles=%ld start=%ld end_exclusive=%ld native_clock_ps=%llu\n",
        cycles,start_cycle,end_cycle,(unsigned long long)native_clock_ps));
    checked(fprintf(file.get(),"# index_b_active=%s index_measurement=%s stack_peak=NOT_SUPPLIED utilization=NOT_COMPUTED semantic_kv_bytes=NOT_INFERRED\n",
        after.index_b_active?"true":"false",after.index_b_active?"SEPARATE_NATIVE_PROVIDER_REQUIRED":"NOT_MEASURED"));
    for(unsigned s=0;s<4;++s)
        checked(fprintf(file.get(),"# stack=%u observed_write_done=%llu\n",s,
            (unsigned long long)delta(before.stack[s].observed_write_done,after.stack[s].observed_write_done)));
    checked(fprintf(file.get(),"rank\tstack\towner\taccepted_read_requests\taccepted_read_sector_bytes\tdelivered_read_sector_bytes\taccepted_write_strobed_bytes\taccepted_write_carrier_bytes\tdelivered_read_bytes_per_cycle\tdelivered_read_TB_s\taccepted_write_strobed_bytes_per_cycle\taccepted_write_strobed_TB_s\n"));
    static const char* names[]={"WINDOW","CKV","RoPE","invalid","TOTAL"};
    for(unsigned s=0;s<4;++s)for(unsigned o=0;o<5;++o) {
        const auto& a=o==4?before.stack[s].total:before.stack[s].owner[o];
        const auto& b=o==4?after.stack[s].total:after.stack[s].owner[o];
        const auto read=delta(a.delivered_read.bytes,b.delivered_read.bytes);
        const auto write=delta(a.accepted_write.bytes,b.accepted_write.bytes);
        const double rbpc=double(read)/cycles,wbpc=double(write)/cycles;
        checked(fprintf(file.get(),"%u\t%u\t%s\t%llu\t%llu\t%llu\t%llu\t%llu\t%.17g\t%.17g\t%.17g\t%.17g\n",
            rank,s,names[o],(unsigned long long)delta(a.accepted_read_requests,b.accepted_read_requests),
            (unsigned long long)delta(a.accepted_read.bytes,b.accepted_read.bytes),
            (unsigned long long)read,(unsigned long long)write,
            (unsigned long long)delta(a.accepted_write_carrier_bytes,b.accepted_write_carrier_bytes),
            rbpc,rbpc/native_clock_ps,wbpc,wbpc/native_clock_ps));
    }
    if(fflush(file.get())||ferror(file.get()))throw std::runtime_error("L20 native measurement flush failed");
}
} // namespace dsrom_s81_minimum
