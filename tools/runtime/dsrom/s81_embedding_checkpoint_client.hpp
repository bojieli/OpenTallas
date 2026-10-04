#pragma once
#include <array>
#include <cerrno>
#include <cstring>
#include <stdexcept>
#include <string>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

class DsromS81EmbeddingCheckpointClient {
 int fd=-1;
 uint32_t token,position;
 static void put(unsigned char* b,uint64_t x,unsigned n){for(unsigned k=0;k<n;k++)b[k]=x>>(8*k);}
 static uint64_t get(const unsigned char* b,unsigned n){uint64_t v=0;for(unsigned k=0;k<n;k++)v|=uint64_t(b[k])<<(8*k);return v;}
 void transfer(void* data,size_t size,bool write) {
   size_t n=0;
   while(n<size) {
     ssize_t count=write?send(fd,static_cast<char*>(data)+n,size-n,MSG_NOSIGNAL):recv(fd,static_cast<char*>(data)+n,size-n,0);
     if(count<0 && errno==EINTR)continue;
     if(count<=0)throw std::runtime_error("native embedding checkpoint connection/read failed");
     n+=size_t(count);
   }
 }
public:
 DsromS81EmbeddingCheckpointClient(const std::string& path,uint32_t token_,uint32_t position_)
 :token(token_),position(position_) {
   sockaddr_un addr{};addr.sun_family=AF_UNIX;
   if(path.empty() || path.size()>=sizeof(addr.sun_path))throw std::runtime_error("embedding socket path");
   std::memcpy(addr.sun_path,path.c_str(),path.size()+1);
   fd=socket(AF_UNIX,SOCK_STREAM,0);
   if(fd<0)throw std::runtime_error("embedding socket create failed");
   if(connect(fd,reinterpret_cast<sockaddr*>(&addr),sizeof(addr))) {
     close(fd);fd=-1;throw std::runtime_error("actual embedding service unavailable");
   }
 }
 ~DsromS81EmbeddingCheckpointClient(){if(fd>=0)close(fd);}
 DsromS81EmbeddingCheckpointClient(const DsromS81EmbeddingCheckpointClient&)=delete;
 std::array<uint32_t,8> read(uint64_t identity,uint32_t macro,uint32_t row) {
   unsigned char request[24],response[52];
   put(request,identity,8);put(request+8,token,4);put(request+12,position,4);
   put(request+16,macro,4);put(request+20,row,4);
   transfer(request,sizeof(request),true);transfer(response,sizeof(response),false);
   if(get(response,4)!=0 || get(response+4,8)!=identity || get(response+12,4)!=macro || get(response+16,4)!=row)
     throw std::runtime_error("embedding source rejected or foreign response; no zero fallback");
   std::array<uint32_t,8> words{};
   for(unsigned n=0;n<8;n++)words[n]=uint32_t(get(response+20+4*n,4));
   return words;
 }
};
