// Immutable synthetic words only. DPI functions shared by both namespaces.
#include "svdpi.h"
#include <map>
#include <string>
#include <stdexcept>
#include <cstdint>
static std::map<svScope,std::string> banks;
extern "C" void v41rt_cfg_register() {}
extern "C" long long v41rt_cfg_read(int addr) {
    if(addr<0 || addr>=1600) throw std::runtime_error("cfg bounds");
    unsigned ph=addr/25,k=addr%25;
    bool empty=ph==0, bf=ph==3, fp4=ph==2;
    if(k<8) return (0x100+k) | (1ull<<21) | (uint64_t(fp4)<<26) | (1ull<<27) | (1ull<<28) | (uint64_t(bf)<<42);
    if(k<16) { unsigned c=k-8; return !empty | (uint64_t(c)<<1) | (1ull<<9) | (uint64_t(c)<<16) | (uint64_t(c)<<19) | (uint64_t(bf)<<22); }
    if(k==16) return 0; // one sub-block; np is ORed by the live pair loader
    return (ph==4 ? 0x8000 : 0x200)+(k-17);
}
extern "C" void v41rt_rom_register(const char* inst) { banks.emplace(svGetScope(),inst); }
extern "C" void v41rt_rom_read(int addr, svBitVecVal* q) {
    if(addr<0 || addr>=8192) throw std::runtime_error("ROM bounds");
    const std::string& inst=banks.at(svGetScope());
    bool bf=inst.find("bf")!=std::string::npos, second=inst.back()=='b';
    for(unsigned i=0;i<8;i++) {
        // Fixed lane variation, independent of live stimulus. Includes signed BF16 weights.
        unsigned lane=(addr+i+(second?3:0))%4;
        q[i]=bf ? ((lane&1)?0xbf803f81u:0x3f003f80u) : (0x38383838u ^ (lane*0x08080808u));
    }
    q[8]=0; // zero exponent/scaling metadata; unused high bits zero
}
