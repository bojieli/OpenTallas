#include "s81_minimum_qe.hpp"
#include <fstream>
#include <set>
#include <sys/socket.h>
#include <cerrno>
#include <mutex>
#include <memory>
namespace {
std::vector<uint64_t> hex_words(const std::string&path,unsigned bits){
 std::ifstream f(path);if(!f)throw std::runtime_error("QE emitted control missing: "+path);
 std::vector<uint64_t> words;std::string s;
 while(std::getline(f,s)){
  if(s.empty())continue;
  if(s[0]=='-'||s[0]=='+'||s.size()>16)throw std::runtime_error("QE malformed native control");
  size_t n=0;auto w=std::stoull(s,&n,16);
  if(s.find_first_not_of(" \r\t",n)!=std::string::npos||(bits<64&&w>>bits))
   throw std::runtime_error("QE native control width");
  words.push_back(w);
 }
 return words;
}
void transfer(int fd,void*data,size_t count,bool transmit){
 auto p=static_cast<unsigned char*>(data);
 while(count){auto n=transmit?send(fd,p,count,MSG_NOSIGNAL):recv(fd,p,count,0);
  if(n<0&&errno==EINTR)continue;
  if(n<=0)throw std::runtime_error("QE borrowed native source connection closed");
  p+=n;count-=n;
 }
}
uint32_t read32(const unsigned char*p){return uint32_t(p[0])|uint32_t(p[1])<<8|uint32_t(p[2])<<16|uint32_t(p[3])<<24;}
}
DsromS81QeWordReader dsrom_s81_qe_word_reader(int borrowed_fd){
 if(borrowed_fd<0)throw std::runtime_error("QE source inherited fd missing");
 auto lock=std::make_shared<std::mutex>();
 return [borrowed_fd,lock](int stage,int rank,int macro,int row){
  if(stage<0||stage>=81||rank<0||rank>=4||macro<0||macro>=9668||row<0||row>=4096)
   throw std::runtime_error("QE native source coordinate range");
  std::lock_guard<std::mutex> hold(*lock);
  unsigned char request[16],reply[40];const uint32_t fields[]={uint32_t(stage),uint32_t(rank),uint32_t(macro),uint32_t(row)};
  for(unsigned f=0;f<4;f++)for(unsigned b=0;b<4;b++)request[4*f+b]=(fields[f]>>(8*b))&255;
  transfer(borrowed_fd,request,sizeof request,true);transfer(borrowed_fd,reply,sizeof reply,false);
  if(read32(reply))throw std::runtime_error("released QE source rejected native word");
  std::array<uint32_t,9> word{};for(unsigned j=0;j<9;j++)word[j]=read32(reply+4+4*j);
  if(word[8]>>18)throw std::runtime_error("QE native source word exceeds274bits");
  return word;
 };
}
DsromS81QePhase dsrom_s81_qe_load_controls(const DsromS81PrefixOperation&op,
 const std::vector<dsrom_s81_minimum::ReturnPhaseBinding>&bindings,
 const std::vector<unsigned>&actual_bf_sites,const std::string&emitted_directory,
 uint32_t input_base,uint32_t cut_only_output_alias){
 if(bindings.empty()||(op.unit!=3&&op.unit!=1))throw std::runtime_error("QE source bindings/operation required");
 const auto ph=hex_words(emitted_directory+"/spine_phase.hex",64);
 if(ph.size()!=2)throw std::runtime_error("QE exact selected PHROM two-word extent");
 DsromS81QePhase out{};out.operation=op;out.xbase=input_base;out.cut_output_alias=cut_only_output_alias;
 out.phrom={ph[0],ph[1]};out.ops=(ph[0]>>46)&65535;
 // The existing native input cut is VAW16. Declare an input-only staging alias
 // for real VM19 operands above its aperture; actual SourceIo still uses the
 // original source address and owner, never an aliased VM participant request.
 unsigned k=(ph[0]>>1)&8191;
 out.cut_input_alias=uint64_t(input_base)+k<=65536?input_base:0;
 out.stream=hex_words(emitted_directory+"/spine_stream.hex",48);
 std::set<unsigned> bf(actual_bf_sites.begin(),actual_bf_sites.end());
 if(bf.size()!=519||bf.size()!=actual_bf_sites.size()||*bf.rbegin()>=2417)
  throw std::runtime_error("QE actual selected BF-dual inventory519 required");
 for(const auto&b:bindings){
  if(b.phrom0!=ph[0]||b.phrom1!=ph[1])throw std::runtime_error("QE control/binding PHROM mismatch");
  DsromS81QePairBinding p{};p.returned=b;p.physical_bf_site=bf.count(b.pair);
  // Binding names the source-exact predecessor-inclusive CFG, not a fabricated
  // zero phase prefix. Parent enrollment separately hashes the emitted bundle.
  p.config=hex_words(b.cfg_path,48);out.pairs.push_back(std::move(p));
 }
 return out;
}
