#pragma once
// FUNCTIONAL ONLY. Mutable VM and actual input ROM backing, never oracle outputs.
// begin_edge() before the rising eval; commit_after_edge() after it. Reads
// snapshot old memory before writes and reach inputs on the following edge.
#include <array>
#include <cstdint>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <stdexcept>
#include <algorithm>
#include <unordered_map>
namespace qwen_native {
constexpr unsigned G=3072,W=16,SW=64,VM_WORDS=56816;
template<size_t N> using HexWord=std::array<uint32_t,N>;
template<size_t N> std::vector<HexWord<N>> read_hex(const std::string& path) {
    std::ifstream f(path); if(!f) throw std::runtime_error("missing actual image: "+path);
    std::vector<HexWord<N>> out; std::string line; size_t address=0;
    while(std::getline(f,line)) {
        auto comment=line.find("//"); if(comment!=std::string::npos)line.resize(comment);
        std::istringstream in(line);std::string token;
        while(in>>token) {
            if(token[0]=='@'){address=std::stoull(token.substr(1),nullptr,16);continue;}
            if(token.size()>N*8)throw std::runtime_error("image width exceeded: "+path);
            if(out.size()<=address)out.resize(address+1);
            auto& word=out[address++];word.fill(0);
            for(size_t i=0;i<N && i*8<token.size();++i){
                size_t end=token.size()-i*8,begin=end>8?end-8:0;
                auto part=token.substr(begin,end-begin);
                if(part.find_first_not_of("0123456789abcdefABCDEF")!=std::string::npos)
                    throw std::runtime_error("unknown image bit: "+path);
                word[i]=std::stoul(part,nullptr,16);
            }
        }
    } return out;
}
template<class V> uint32_t bits(const V& v,unsigned offset,unsigned width) {
    uint64_t x=v[offset/32];unsigned shift=offset%32;
    if(shift+width>32)x|=uint64_t(v[offset/32+1])<<32;
    return uint32_t(x>>shift)&(width==32?0xffffffffu:((1u<<width)-1));
}
template<class V,size_t N> void drive(V& v,const HexWord<N>& a){for(size_t i=0;i<N;++i)v[i]=a[i];}
struct Commit {unsigned address;uint32_t value;std::string port;uint64_t edge;};
struct Accepted {unsigned global_pc,unit;uint64_t edge;HexWord<32> instruction;};
struct Response {
    HexWord<32> program{};
    HexWord<G*W/4> code{}; // G*W*8 bits
    HexWord<G*W/2> scales{}; // G*W*16 bits
    HexWord<SW*2> constants{};
    HexWord<G> x{};
    HexWord<SW> a{},b{},c{};
};
class RomVmAdapter {
public:
    std::vector<uint32_t> vm;
    std::vector<Commit> commits;
    std::vector<Accepted> accepted;
    std::vector<unsigned> retired, speculative_fetches;
    unsigned segment_base=0;uint64_t edge=0;
    std::vector<HexWord<32>> program;
    std::vector<HexWord<G*W/4>> code;
    std::vector<HexWord<W/2>> scales;
    std::vector<HexWord<2>> constants;
    Response pending,next;
    std::vector<Commit> writes;
    RomVmAdapter(const std::string& image,const std::string& fused_program,const std::string& x_preload)
      :vm(VM_WORDS,0),program(read_hex<32>(fused_program)),
       code(read_hex<G*W/4>(image+"/matrix_int8.hex")),
       scales(read_hex<W/2>(image+"/matrix_scale_bf16.hex")),
       constants(read_hex<2>(image+"/crom.hex")) {
        auto x=read_hex<1>(x_preload);if(x.size()>vm.size())throw std::runtime_error("VM preload too large");
        for(size_t i=0;i<x.size();++i)vm[i]=x[i][0];
        if(code.size()!=512)throw std::runtime_error("actual compact code bank must contain512words");
    }
    uint32_t load(unsigned addr)const{if(addr>=vm.size())throw std::runtime_error("VM read outside56816: "+std::to_string(addr));return vm[addr];}
    void store(unsigned addr,uint32_t value,const char* port){if(addr>=vm.size())throw std::runtime_error("VM write outside56816: "+std::to_string(addr));writes.push_back({addr,value,port,edge});}
    template<class Model> void drive_responses(Model& m) {
        drive(m.prog_q,pending.program);drive(m.int8_wrom_q,pending.code);
        drive(m.scale_q,pending.scales);drive(m.crom_q,pending.constants);
        drive(m.vx_q,pending.x);drive(m.va_q,pending.a);drive(m.vb_q,pending.b);drive(m.vc_q,pending.c);
    }
    template<class Model> void snapshot_edge(Model& m) {
        next=pending;writes.clear();
        if(m.prog_re){unsigned pc=segment_base+m.prog_addr;if(pc>=4096)throw std::runtime_error("program fetch outside4096wordROM");if(pc>=program.size()){next.program.fill(0);speculative_fetches.push_back(pc);}else next.program=program[pc];}
        if(m.int8_wrom_re){if(m.int8_wrom_addr>=code.size())throw std::runtime_error("code read outside actual compact bank");next.code=code[m.int8_wrom_addr];}
        if(m.wrom_re)throw std::runtime_error("unprovided BF16 stream ROM read; no fabricated response");
        for(unsigned g=0;g<G;++g){
            if(bits(m.scale_gre,g,1)){unsigned a=bits(m.scale_addr,g*24,24);if(a>=scales.size())throw std::runtime_error("scale read outside actual independent bank");for(unsigned j=0;j<W/2;++j)next.scales[g*(W/2)+j]=scales[a][j];}
            if(bits(m.vx_re,g,1))next.x[g]=load(bits(m.vx_addr,g*24,24));
            if(bits(m.vw_me_we,g,1)){unsigned a=bits(m.vw_me_addr,g*24,24)*W;for(unsigned j=0;j<W;++j)if(bits(m.vw_me_mask,g*W+j,1))store(a+j,m.vw_me_data[g*W+j],"ME");}
        }
        for(unsigned s=0;s<SW;++s){
            uint64_t mask=uint64_t(1)<<s;
            if(m.va_re&mask)next.a[s]=load(bits(m.va_addr,s*24,24));
            if(m.vb_re&mask)next.b[s]=load(bits(m.vb_addr,s*24,24));
            if(m.vc_re&mask)next.c[s]=load(bits(m.vc_addr,s*24,24));
            if(m.crom_re&mask){unsigned a=bits(m.crom_addr,s*24,24);if(a>=constants.size())throw std::runtime_error("constant read outside actual bank");next.constants[2*s]=constants[a][0];next.constants[2*s+1]=constants[a][1];}
            if(m.vw_su_we&mask)store(bits(m.vw_su_addr,s*24,24),m.vw_su_data[s],"SU");
        }
        if(m.vw_rd_we)store(m.vw_rd_addr,m.vw_rd_data,"REDUCER");
        if(m.vw_mx_we){unsigned a=m.vw_mx_addr*W;for(unsigned j=0;j<W;++j)if(m.vw_mx_mask&(1u<<j))store(a+j,m.vw_mx_data[j],"MAX");}
        if(m.instruction_issue){unsigned pc=segment_base+m.instruction_pc;if(pc>=program.size())throw std::runtime_error("accepted PC outside image");if(unsigned(m.instruction_unit)!=(program[pc][0]&3))throw std::runtime_error("accepted unit differs from pinned instruction");accepted.push_back({pc,unsigned(m.instruction_unit),edge,program[pc]});}
        if(m.end_retired)retired.push_back(segment_base+m.end_pc);
    }
    // Convenience API requires clk=0. Production integration may instead call
    // drive_responses(), eval all coupled models, then snapshot_edge() explicitly.
    template<class Model> void begin_edge(Model& m){drive_responses(m);m.eval();snapshot_edge(m);}
    void commit_after_edge(){
        std::unordered_map<unsigned,uint32_t> seen;
        for(const auto& w:writes){auto old=seen.emplace(w.address,w.value);if(!old.second && old.first->second!=w.value)throw std::runtime_error("conflicting same-edge VM writes");}
        for(const auto& w:writes)vm[w.address]=w.value;
        commits.insert(commits.end(),writes.begin(),writes.end());pending=next;++edge;
    }
    // Collectives/native service commit actual result data here; caller supplies
    // genuine acknowledged writes. This is not an oracle preload operation.
    void external_commit(unsigned addr,uint32_t value,const char* port){if(addr>=vm.size())throw std::runtime_error("external VM write outside56816");vm[addr]=value;commits.push_back({addr,value,port,edge});}
};
}
