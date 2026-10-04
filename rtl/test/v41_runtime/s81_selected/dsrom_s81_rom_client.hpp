#pragma once
// Simulation-only native-word transport. No numerical decoding or cycle credit.
#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <stdexcept>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

namespace dsrom_s81 {
inline void transfer(int fd, void* data, size_t n, bool send) {
    auto* p = static_cast<unsigned char*>(data);
    while (n) {
        ssize_t k = send ? ::send(fd, p, n, MSG_NOSIGNAL) : ::recv(fd, p, n, 0);
        if (k <= 0) throw std::runtime_error("S81 native-word provider disconnected");
        p += k; n -= size_t(k);
    }
}
inline uint32_t le32(const unsigned char* p) {
    return uint32_t(p[0]) | uint32_t(p[1])<<8 | uint32_t(p[2])<<16 | uint32_t(p[3])<<24;
}
inline std::array<uint32_t,9> read(int stage, int rank, int pair, int bank, int logical) {
    if (stage<0 || stage>=81 || rank<0 || rank>=4 || pair<0 || pair>=2417 ||
        bank<0 || bank>=2 || logical<0 || logical>=8192)
        throw std::runtime_error("S81 native-word address out of bounds");
    static std::mutex mutex;
    static int fd=-1;
    std::lock_guard<std::mutex> lock(mutex);
    if (fd<0) {
        const char* path=std::getenv("DSROM_S81_ROM_SOCKET");
        if (!path) throw std::runtime_error("DSROM_S81_ROM_SOCKET is required");
        sockaddr_un a{};a.sun_family=AF_UNIX;
        if (std::strlen(path)>=sizeof(a.sun_path)) throw std::runtime_error("S81 socket path too long");
        std::strcpy(a.sun_path,path);
        fd=::socket(AF_UNIX,SOCK_STREAM,0);
        if (fd<0 || ::connect(fd,reinterpret_cast<sockaddr*>(&a),sizeof(a))<0)
            throw std::runtime_error("cannot connect S81 native-word provider");
    }
    // PP adapter presents logical 8192 address; select the exact physical4096
    // leaf, preserving both bank and even/odd parity. No re-encoding here.
    uint32_t fields[4]={uint32_t(stage),uint32_t(rank),uint32_t(4*pair+2*bank+(logical&1)),uint32_t(logical>>1)};
    unsigned char request[16],reply[40];
    for(int i=0;i<4;i++)for(int b=0;b<4;b++)request[4*i+b]=(fields[i]>>(8*b))&255;
    transfer(fd,request,sizeof(request),true);transfer(fd,reply,sizeof(reply),false);
    if (le32(reply)) throw std::runtime_error("S81 rejected unowned/invalid native ROM read; no zero fallback");
    std::array<uint32_t,9> result{};
    for(int i=0;i<9;i++)result[i]=le32(reply+4+4*i);
    if(result[8]>>18)throw std::runtime_error("S81 provider exceeded 274 bits");
    return result;
}
}
