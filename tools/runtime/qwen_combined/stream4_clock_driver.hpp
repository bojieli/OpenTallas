#pragma once
#include "combined_driver.hpp"
#include <algorithm>
namespace qwen_stream4 {
struct ClockSpec {
    uint64_t period_fs, first_rise_fs;
    void check() const {
        if(period_fs<2 || !first_rise_fs)throw std::invalid_argument("positive STREAM4 clock/phase required");
    }
};
// Preserve literal CORE_FS=833333. Rising-edge intervals are exactly period_fs;
// odd periods have floor/ceil half intervals, rather than silently 833332.
class ClockDriver {
    ClockSpec core_,service_;
    uint64_t nc_,ns_,now_=0,cr_=0,sr_=0;
    bool ch_=false,sh_=false;
    static uint64_t add(uint64_t a,uint64_t b) {
        if(b>std::numeric_limits<uint64_t>::max()-a)throw std::overflow_error("clock overflow");
        return a+b;
    }
public:
    ClockDriver(ClockSpec c,ClockSpec s):core_(c),service_(s),nc_(c.first_rise_fs),ns_(s.first_rise_fs) {
        c.check();s.check();
    }
    qwen_combined::Edges next() {
        const uint64_t t=std::min(nc_,ns_);
        qwen_combined::Edges e{t,nc_==t,ns_==t,ch_,sh_};
        if(e.core_changed){e.core_high=!ch_;nc_=add(nc_,e.core_high?core_.period_fs/2:core_.period_fs-core_.period_fs/2);}
        if(e.service_changed){e.service_high=!sh_;ns_=add(ns_,e.service_high?service_.period_fs/2:service_.period_fs-service_.period_fs/2);}
        ch_=e.core_high;sh_=e.service_high;now_=t;cr_+=e.core_rise();sr_+=e.service_rise();return e;
    }
    uint64_t core_rises()const{return cr_;}
    uint64_t service_rises()const{return sr_;}
    uint64_t time_fs()const{return now_;}
};
}
