#pragma once
#include <array>
#include <cstdint>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace qwen_combined {
struct NearPositionBases { std::uint32_t q, output; };
inline std::vector<NearPositionBases> load_near_position_bases(const std::string& path) {
    std::ifstream in(path);
    if(!in) throw std::runtime_error("actual near slot bases missing: "+path);
    std::vector<NearPositionBases> slots;
    std::string word;
    while(in>>word) {
        std::size_t end=0;
        const auto bits=std::stoull(word,&end,16);
        if(end!=word.size() || bits>>48 || slots.size()==4)
            throw std::runtime_error("actual near slot base width/count");
        slots.push_back({std::uint32_t(bits&0xffffff),std::uint32_t(bits>>24)});
    }
    if(slots.empty()) throw std::runtime_error("actual near slot bases empty");
    return slots;
}
inline std::array<std::uint32_t,6> pack_near_position_bases(
        const std::vector<NearPositionBases>& slots,bool output,std::size_t vm_elements) {
    if(slots.empty() || slots.size()>4 || vm_elements<1024)
        throw std::runtime_error("actual near block/VM extent");
    std::array<std::uint32_t,6> packed{};
    for(std::size_t slot=0;slot<slots.size();++slot) {
        const auto base=output?slots[slot].output:slots[slot].q;
        if(base>=0x1000000 || base%16 || base>vm_elements-1024)
            throw std::runtime_error("actual near slot base outside VM");
        const auto index=slot*24/32,shift=slot*24%32;
        packed[index]|=base<<shift;
        if(shift>8)packed[index+1]|=base>>(32-shift);
    }
    return packed;
}
template<class Die> void initialize_dspark_inputs(Die& d) {
    d.rm_npos=1;d.h_commit_v=0;d.h_commit_n=0;
    d.acc_start_v=0;d.acc_start_tok=0;d.acc_tokx_v=0;d.acc_tokx_slot=0;d.acc_tokx_tok=0;
    d.acc_arm=0;d.acc_commit_en=0;
    for(unsigned i=0;i<6;++i)d.rm_near_qbases[i]=d.rm_near_obases[i]=0;
}
template<class Die> void bind_dspark_decoder_slots(Die& d,
        const std::vector<NearPositionBases>& slots,unsigned position,std::size_t vm_elements) {
    if(position>=8192 || slots.size()>8192-position || d.rm_layer>=36 || d.h_start || d.clk)
        throw std::runtime_error("near slot binding requires bounded decoder before launch");
    const auto q=pack_near_position_bases(slots,false,vm_elements);
    const auto o=pack_near_position_bases(slots,true,vm_elements);
    for(unsigned i=0;i<6;++i){d.rm_near_qbases[i]=q[i];d.rm_near_obases[i]=o[i];}
    d.rm_npos=slots.size();
}
} // namespace qwen_combined
