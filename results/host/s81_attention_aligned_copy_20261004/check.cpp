// Tiny standalone HOST helper check; no DUT, clocks or model libraries.
#include <verilated.h>
#include <array>
#include <chrono>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <type_traits>
struct Original {
    template<class Bus> static bool bit(const Bus& b,unsigned i) {
        if constexpr(std::is_integral<Bus>::value)return (uint64_t(b)>>i)&1u;
        else return (b[i/32]>>(i%32))&1u;
    }
    template<class Bus> static void bit(Bus& b,unsigned i,bool value) {
        if constexpr(std::is_integral<Bus>::value) {
            const uint64_t mask=uint64_t(1)<<i;
            b=(uint64_t(b)&~mask)|(value?mask:0);
        } else {
            const uint32_t mask=uint32_t(1)<<(i%32);
            b[i/32]=(b[i/32]&~mask)|(value?mask:0);
        }
    }
    template<class To,class From> static bool copy(To& to,unsigned a,
        const From& from,unsigned b,unsigned n) {
        bool changed=false;
        for(unsigned i=0;i<n;++i) {
            bool value=bit(from,b+i);changed|=value!=bit(to,a+i);bit(to,a+i,value);
        }
        return changed;
    }
};
struct Successor {
    template<class Bus> static bool bit(const Bus& b,unsigned i) {
        if constexpr(std::is_integral<Bus>::value)return (uint64_t(b)>>i)&1u;
        else return (b[i/32]>>(i%32))&1u;
    }
    template<class Bus> static void bit(Bus& b,unsigned i,bool value) {
        if constexpr(std::is_integral<Bus>::value) {
            const uint64_t mask=uint64_t(1)<<i;
            b=(uint64_t(b)&~mask)|(value?mask:0);
        } else {
            const uint32_t mask=uint32_t(1)<<(i%32);
            b[i/32]=(b[i/32]&~mask)|(value?mask:0);
        }
    }
    template<class To,class From> static bool copy(To& to,unsigned a,
        const From& from,unsigned b,unsigned n) {
        bool changed=false;
        unsigned i=0;
        // HOST-only exact copy of aligned wide-bus portions. Model input
        // values, changed detection, settle calls and all clock edges stay
        // identical. propagate() copies between distinct borrowed models.
        if constexpr(!std::is_integral<To>::value && !std::is_integral<From>::value) {
            if((a%32)==0 && (b%32)==0) {
                for(;n-i>=32;i+=32) {
                    const uint32_t value=from[(b+i)/32];
                    changed|=value!=to[(a+i)/32];to[(a+i)/32]=value;
                }
            }
        }
        for(;i<n;++i) {
            bool value=bit(from,b+i);changed|=value!=bit(to,a+i);bit(to,a+i,value);
        }
        return changed;
    }
};

using Wide=VlWide<1124>;
static unsigned cases=0;
template<class To,class From>
void check(To initial,const From& source,unsigned a,unsigned b,unsigned n) {
    To x=initial,y=initial;
    bool old=Original::copy(x,a,source,b,n),fresh=Successor::copy(y,a,source,b,n);
    if(old!=fresh || std::memcmp(&x,&y,sizeof(x)))throw std::runtime_error("copy mismatch");
    if(Original::copy(x,a,source,b,n)||Successor::copy(y,a,source,b,n))
        throw std::runtime_error("unchanged flag mismatch");
    ++cases;
}
volatile uint64_t sink=0;
template<class Copier> __attribute__((noinline)) double timed(unsigned count) {
    Wide source{},target{};
    for(unsigned i=0;i<1124;++i)source[i]=0x9e3779b9u*(i+1);
    uint64_t changes=0;
    auto start=std::chrono::steady_clock::now();
    for(unsigned i=0;i<count;++i) {
        // Mix changed and unchanged invocations; same pv_f/pv_y destination offsets.
        if((i%4)==0)source[i%1056]^=0x40000001u;
        changes+=Copier::copy(target,0,source,0,1024);
        changes+=Copier::copy(target,1024,source,1024,32768);
        asm volatile("" : : "g"(&target) : "memory");
    }
    auto end=std::chrono::steady_clock::now();
    sink=changes+target[1055];
    return std::chrono::duration<double>(end-start).count();
}
int main() {
    Wide source{},target{};
    for(unsigned i=0;i<1124;++i) {
        source[i]=0x9e3779b9u*(i+1); target[i]=~source[i];
    }
    for(auto s:std::array<std::array<unsigned,3>,12>{{
        {0,0,1024},{1024,0,32768},{0,0,0},{32,64,65},
        {0,0,31},{0,0,33},{1,0,1024},{0,1,1024},
        {7,13,2001},{0,0,35938},{0,0,32768},{1024,1024,32768}}})
        check(target,source,s[0],s[1],s[2]);
    check(uint8_t(0x55),uint8_t(0xaa),0,0,8);
    check(uint16_t(0x55),uint16_t(0xaaaa),1,2,13);
    check(uint32_t(0x55555555),uint32_t(0xaaaaaaaa),0,0,32);
    check(uint64_t(0x5555555555555555),uint64_t(0xaaaaaaaaaaaaaaaa),0,0,64);
    check(uint64_t(0),source,0,13,64);
    check(target,uint64_t(0xaaaaaaaaaaaaaaaa),35,0,64);
    constexpr unsigned iterations=4000;
    double original=timed<Original>(iterations);
    double successor=timed<Successor>(iterations);
    std::cout.precision(12);
    std::cout<<"PASS bitcopy_and_changedOR cases="<<cases
             <<" iterations="<<iterations<<" aligned_bits_per_iteration=33792\n"
             <<"original_seconds="<<original<<" successor_seconds="<<successor
             <<" speedup="<<original/successor<<" checksum="<<sink<<"\n";
}
