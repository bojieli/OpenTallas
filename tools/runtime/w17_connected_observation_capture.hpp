#pragma once
// Simulation host state only. No DUT writes, service timers, or retirement inference.
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <stdexcept>
#include <string>
namespace w17_capture {
inline constexpr uint64_t LIMIT = uint64_t(4) << 30;
struct Trace {
    FILE* file=nullptr; uint64_t bytes=0; bool ckv;
    std::array<bool,4> seen{};
    std::array<uint64_t,4> cycle{},host{};
    const char* stage;
    explicit Trace(bool selected):ckv(selected),stage(selected?"layer20":"layer0") {
        const char* path=std::getenv("W17_OBSERVATION_TRACE");
        if(!path || !*path) throw std::invalid_argument("exclusive W17_OBSERVATION_TRACE required");
        file=std::fopen(path,"wx");
        if(!file) throw std::runtime_error("trace create failed; existing evidence never overwritten");
        emit(std::string("W17_CAUSAL_TRACE_V1 ")+stage+(ckv?" CKV\n":" WINDOW\n"));
    }
    ~Trace(){if(file)std::fclose(file);}
    void emit(const std::string& line) {
        if(line.size()>LIMIT-bytes)throw std::runtime_error("TRACE_CAP; incomplete evidence, never completion");
        if(std::fwrite(line.data(),1,line.size(),file)!=line.size() || std::fflush(file))throw std::runtime_error("trace write failed");
        bytes+=line.size();
    }
    template<class Words> void edge(unsigned rank,uint64_t host_cycle,const Words& p,
        bool done,uint32_t fault,uint32_t fs,uint64_t state) {
        if(rank>=4 || (uint32_t(p[31])>>28) || (uint32_t(p[4])&3)!=rank ||
           bool((uint32_t(p[4])>>2)&1)!=ckv)throw std::runtime_error("packet envelope/mode mismatch");
        uint64_t epoch=uint64_t(p[0])|(uint64_t(p[1])<<32);
        uint64_t native=uint64_t(p[2])|(uint64_t(p[3])<<32);
        if(epoch!=1 || (seen[rank] && (cycle[rank]==UINT64_MAX || native!=cycle[rank]+1 || host_cycle!=host[rank]+1)))
            throw std::runtime_error("reset/repeated/gapped capture; no fence claim");
        char prefix[160];int n=std::snprintf(prefix,sizeof(prefix),"OBS %u %llu %u %08x %08x %016llx ",rank,
            (unsigned long long)host_cycle,unsigned(done),fault,fs,(unsigned long long)state);
        if(n<=0 || size_t(n)>=sizeof(prefix))throw std::runtime_error("trace formatting");
        std::string line(prefix,size_t(n));
        for(int i=31;i>=0;--i){char word[9];std::snprintf(word,sizeof(word),"%08x",uint32_t(p[i]));line+=word;}
        line+='\n';emit(line);seen[rank]=true;cycle[rank]=native;host[rank]=host_cycle;
    }
};
inline std::unique_ptr<Trace> trace;
}
