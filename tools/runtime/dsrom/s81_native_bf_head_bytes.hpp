#pragma once
#include "s81_native_bf_head_producer.hpp"
#include <cerrno>
#include <cstring>
#include <mutex>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

namespace dsrom_s81_minimum {
// Simulation transport to the existing ReleasedHeadByteProvider codec. One
// synchronous typed request, exact echoed coordinate, no substitute image.
class ReleasedNativeBfHeadBytes {
    int fd=-1;
    std::mutex mutex;
    static void transfer(int fd,unsigned char* p,size_t size,bool write) {
        while(size) {
            ssize_t n=write ? ::send(fd,p,size,MSG_NOSIGNAL) : ::recv(fd,p,size,0);
            if(n<0&&errno==EINTR)continue;
            if(n<=0)throw std::runtime_error("released head byte provider disconnected");
            p+=n;size-=n;
        }
    }
    static uint32_t get(const unsigned char* p) {
        return uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);
    }
public:
    explicit ReleasedNativeBfHeadBytes(const std::string& socket_path) {
        sockaddr_un a{};a.sun_family=AF_UNIX;
        if(socket_path.empty()||socket_path.size()>=sizeof(a.sun_path))
            throw std::runtime_error("explicit released head byte socket required");
        std::memcpy(a.sun_path,socket_path.c_str(),socket_path.size()+1);
        fd=::socket(AF_UNIX,SOCK_STREAM,0);
        if(fd<0||::connect(fd,reinterpret_cast<sockaddr*>(&a),sizeof(a))<0) {
            if(fd>=0)::close(fd);fd=-1;
            throw std::runtime_error("cannot connect actual released head byte provider");
        }
    }
    ~ReleasedNativeBfHeadBytes(){if(fd>=0)::close(fd);}
    NativeBfHeadRom::Word read(unsigned rank,unsigned row,unsigned h,unsigned b) {
        if(rank>=4||row>=32320||h>=40||b>=8)throw std::runtime_error("released BF head coordinate");
        std::lock_guard<std::mutex> lock(mutex);
        unsigned char request[16],reply[56];uint32_t fields[4]={rank,row,h,b};
        for(unsigned i=0;i<4;i++)for(unsigned j=0;j<4;j++)request[4*i+j]=(fields[i]>>(8*j))&255;
        transfer(fd,request,16,true);transfer(fd,reply,56,false);
        if(get(reply)||std::memcmp(request,reply+4,16))
            throw std::runtime_error("released BF head response fault/coordinate mismatch");
        NativeBfHeadRom::Word word{};
        for(unsigned i=0;i<9;i++)word[i]=get(reply+20+4*i);
        if(word[8]>>18)throw std::runtime_error("released BF head response exceeds274bits");
        return word;
    }
};
} // namespace dsrom_s81_minimum
