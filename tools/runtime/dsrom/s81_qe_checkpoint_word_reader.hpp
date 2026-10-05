#pragma once
// Source-only transport for Hubble's DsromS81QeWordReader; no arithmetic or tick.
#include <array>
#include <cerrno>
#include <cstdint>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <limits.h>
#include <sys/wait.h>
#include <unistd.h>

class DsromS81QeCheckpointWordReader {
    int fd_=-1;
    pid_t child_=-1;
    std::mutex lock_;
    bool delayed_=false,bound_=false;
    std::array<unsigned char,32> source_digest_{};
    static void transfer(int fd, unsigned char* data, size_t n, bool send_data) {
        while(n) {
            ssize_t k=send_data ? ::send(fd,data,n,MSG_NOSIGNAL) : ::recv(fd,data,n,0);
            if(k<0&&errno==EINTR)continue;
            if(k<=0)throw std::runtime_error("released QE provider disconnected; no zero fallback");
            data+=k;n-=size_t(k);
        }
    }
    static uint32_t le32(const unsigned char* p) {
        return uint32_t(p[0])|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;
    }
public:
    // Construct before native-model worker threads. Borrow the reader via a
    // shared_ptr in the actual participant callback; retain it through drain.
    DsromS81QeCheckpointWordReader(const std::string& python,const std::string& script,
        const std::string& owner,const std::string& checkpoint,const std::string& node,
        unsigned rank,unsigned fragment=0,const std::vector<unsigned>& captured_eids={},bool delayed_expert_binding=false) {
        if(rank>=4)throw std::runtime_error("QE TP4 rank");
        if(delayed_expert_binding&&!captured_eids.empty())throw std::runtime_error("delayed actor cannot prefill EIDs");
        delayed_=delayed_expert_binding;
        std::string eids;
        if(!captured_eids.empty()) {
            if(captured_eids.size()!=6)throw std::runtime_error("six captured native EIDs required");
            for(size_t i=0;i<captured_eids.size();++i){
                if(captured_eids[i]>=384||(i&&captured_eids[i]<=captured_eids[i-1]))
                    throw std::runtime_error("captured EID order/range");
                if(i)eids+=",";
                eids+=std::to_string(captured_eids[i]);
            }
        }
        int pair[2];if(::socketpair(AF_UNIX,SOCK_STREAM,0,pair))throw std::runtime_error("QE private transport");
        const std::string descriptor="3";
        auto r=std::to_string(rank),f=std::to_string(fragment);
        child_=::fork();
        if(child_<0){::close(pair[0]);::close(pair[1]);throw std::runtime_error("QE provider fork");}
        if(!child_){
            ::close(pair[0]);
            if(pair[1]!=3 && ::dup2(pair[1],3)<0)::_exit(126);
            // Do not retain the live field service or native model descriptors.
            bool closed=false;
#ifdef SYS_close_range
            closed=(::syscall(SYS_close_range,4u,UINT_MAX,0)==0);
#endif
            if(!closed){long n=::sysconf(_SC_OPEN_MAX);for(int i=4;i<n;++i)::close(i);}
            if(delayed_expert_binding) {
                ::execl(python.c_str(),python.c_str(),"-u",script.c_str(),"--fd",descriptor.c_str(),
                    "--owner",owner.c_str(),"--checkpoint",checkpoint.c_str(),"--node",node.c_str(),
                    "--rank",r.c_str(),"--fragment",f.c_str(),"--delayed-expert-binding",static_cast<char*>(nullptr));
                ::_exit(127);
            }
            ::execl(python.c_str(),python.c_str(),"-u",script.c_str(),"--fd",descriptor.c_str(),
                "--owner",owner.c_str(),"--checkpoint",checkpoint.c_str(),"--node",node.c_str(),
                "--rank",r.c_str(),"--fragment",f.c_str(),"--expert-ids",eids.c_str(),static_cast<char*>(nullptr));
            ::_exit(127);
        }
        ::close(pair[1]);fd_=pair[0];
        if(delayed_) {
            unsigned char ready[40];
            try {
                transfer(fd_,ready,sizeof ready,false);
                if(le32(ready)||le32(ready+36)!=1)throw std::runtime_error("delayed source not ready");
                for(unsigned i=0;i<32;++i)source_digest_[i]=ready[4+i];
            } catch(...) {
                ::close(fd_);fd_=-1;int status;
                while(::waitpid(child_,&status,0)<0&&errno==EINTR){}
                child_=-1;throw;
            }
        }
    }
    DsromS81QeCheckpointWordReader(const DsromS81QeCheckpointWordReader&)=delete;
    ~DsromS81QeCheckpointWordReader() {
        if(fd_>=0){::shutdown(fd_,SHUT_RDWR);::close(fd_);}
        if(child_>0){int status;while(::waitpid(child_,&status,0)<0&&errno==EINTR){}}
    }
    // Call only after native EID publication/capture under the caller's lease.
    // This never forks. The fixed child stays alive through operator drain.
    void bind_captured_eids(const std::vector<unsigned>& eids,
                           const std::string& expected_node_sha256,unsigned rank,unsigned fragment=0) {
        std::lock_guard<std::mutex> held(lock_);
        if(!delayed_||bound_||eids.size()!=6||rank>=4||expected_node_sha256.size()!=64)
            throw std::runtime_error("invalid/duplicate delayed EID bind");
        unsigned char request[72]{},reply[40];
        uint32_t fields[4]={0xffffffffu,1u,rank,fragment};
        for(unsigned i=0;i<4;++i)for(unsigned b=0;b<4;++b)request[4*i+b]=(fields[i]>>(8*b))&255;
        auto hex=[](char c)->unsigned {
            if(c>='0'&&c<='9')return unsigned(c-'0');
            if(c>='a'&&c<='f')return unsigned(c-'a'+10);
            throw std::runtime_error("source SHA must be lowercase hex");
        };
        for(unsigned i=0;i<32;++i) {
            request[16+i]=static_cast<unsigned char>((hex(expected_node_sha256[2*i])<<4)|hex(expected_node_sha256[2*i+1]));
            if(request[16+i]!=source_digest_[i])throw std::runtime_error("wrong delayed source identity");
        }
        for(unsigned i=0;i<6;++i) {
            if(eids[i]>=384||(i&&eids[i]<=eids[i-1]))throw std::runtime_error("captured EID order/range");
            for(unsigned b=0;b<4;++b)request[48+4*i+b]=(eids[i]>>(8*b))&255;
        }
        transfer(fd_,request,sizeof request,true);transfer(fd_,reply,sizeof reply,false);
        if(le32(reply))throw std::runtime_error("delayed captured EIDs rejected by source");
        for(unsigned i=0;i<32;++i)if(reply[4+i]!=source_digest_[i])throw std::runtime_error("delayed bind source echo mismatch");
        bound_=true;
    }
    pid_t source_child_pid()const{return child_;}
    std::array<uint32_t,9> read(int stage,int rank,int macro,int row) {
        if(stage<0||stage>=81||rank<0||rank>=4||macro<0||macro>=9668||row<0||row>=4096)
            throw std::runtime_error("QE physical source address");
        std::lock_guard<std::mutex> held(lock_);
        uint32_t fields[4]={uint32_t(stage),uint32_t(rank),uint32_t(macro),uint32_t(row)};
        unsigned char request[16],reply[40];
        for(unsigned i=0;i<4;++i)for(unsigned b=0;b<4;++b)request[4*i+b]=(fields[i]>>(8*b))&255;
        transfer(fd_,request,sizeof request,true);transfer(fd_,reply,sizeof reply,false);
        if(le32(reply))throw std::runtime_error("released QE source rejected address");
        std::array<uint32_t,9> words{};
        for(unsigned i=0;i<9;++i)words[i]=le32(reply+4+4*i);
        if(words[8]>>18)throw std::runtime_error("released QE word exceeds274bits");
        return words;
    }
};
