#pragma once
// Source-exact HOST bench fixture. Not production board RTL or a native result
// provider. Models only host RAM, routed class528 queues and physical wires.
// Bench provenance: tb_qkd_host_control_token_service.sv board tasks/callbacks;
// tb_qkd_host_native_fdi8_boot_guard.sv actual paired adapters and 223 stages.
#include <array>
#include <cstdint>
#include <deque>
#include <map>
#include <stdexcept>
#include <vector>

namespace qkd_host_fixture {
using Payload = std::array<uint32_t,16>;
using Word528 = std::array<uint32_t,17>;
using Flit1043 = std::array<uint32_t,33>;
inline Word528 packet(unsigned cls,const Payload& p) {
 if(cls>15) throw std::runtime_error("invalid class528 class");
 Word528 w{};for(unsigned i=0;i<16;++i)w[i]=p[i];w[16]=cls<<12;return w;
}
inline Payload payload(const Word528& w) {
 Payload p{};for(unsigned i=0;i<16;++i)p[i]=w[i];return p;
}
inline uint64_t get64(const Payload& p,unsigned lowword) {
 return uint64_t(p[lowword])|(uint64_t(p[lowword+1])<<32);
}
inline void put64(Payload& p,unsigned lowword,uint64_t value) {
 p[lowword]=uint32_t(value);p[lowword+1]=uint32_t(value>>32);
}
struct Wire { bool v=false;Flit1043 flit{}; };
struct BarResponse { unsigned rank;uint16_t id;bool read;unsigned response;uint32_t data; };
struct Completion { unsigned rank;uint64_t data; };
class Router {
 static constexpr unsigned ranks=8,depth=64,phy_latency=223;
 struct Queued { Word528 word;int origin; };
 // Original sender ownership is distinct from destination logical capacity.
 std::array<std::deque<Queued>,ranks> q_{};
 std::array<std::array<std::deque<int>,3>,ranks> owners_{};
 std::array<std::array<unsigned,3>,ranks> logical_{};
 std::array<unsigned,ranks> tx_capacity_{};
 std::array<std::array<Wire,phy_latency>,ranks> to_host_{},to_board_{};
 std::map<uint64_t,uint64_t> ram_{};
 std::vector<BarResponse> bars_{};
 std::vector<Completion> completions_{};
 std::array<bool,ranks> irq_{},pause_ctrl_{};
 uint64_t dma_reads_=0,dma_writes_=0,ctrl_forwarded_=0,ctrl_retired_=0;
 static void require(bool ok,const char* what) { if(!ok)throw std::runtime_error(what); }
 static int group(unsigned cls) { return cls==0?0:(cls==1?1:(cls>=2&&cls<=4?2:-1)); }
 static unsigned limit(unsigned g) { return g==2?16:4; }
 static void check_rank(unsigned rank) { require(rank<ranks,"rank outside ND8"); }
 bool add(unsigned dest,const Word528& w,int origin) {
  check_rank(dest);if(q_[dest].size()==depth)return false;
  q_[dest].push_back({w,origin});return true;
 }
 void add_required(unsigned dest,const Word528& w,int origin) {
  require(add(dest,w,origin),"router reservation queue exhausted");
 }
 void credit(unsigned dest,unsigned g,unsigned count) {
  require(g<3&&count<=4,"invalid peer TX credit packet");
  Payload p{};p[0]=count<<(8*g);
  // Credit packets bypass destination application windows and must pass blocked
  // data in order to break a full logical-window stall.
  require(q_[dest].size()<depth,"router credit reservation exhausted");
  q_[dest].push_front({packet(7,p),-1});
 }
 void returned(unsigned dest,const Payload& p) {
  require((p[0]&0xff000000u)==0,"credit packet reserved bits");
  for(unsigned n=1;n<16;++n)require(p[n]==0,"credit packet upper bits");
  for(unsigned g=0;g<3;++g) {
   unsigned n=(p[0]>>(g*8))&255;
   require(n<=owners_[dest][g].size(),"unowned or duplicate destination credit");
   require(logical_[dest][g]+n<=limit(g),"destination logical credit overflow");
   logical_[dest][g]+=n;
   while(n--) {
    int source=owners_[dest][g].front();owners_[dest][g].pop_front();
    if(source>=0) { credit(unsigned(source),g,1);if(g==1)++ctrl_retired_; }
   }
  }
 }
 void board_host(unsigned rank,const Payload& p) {
  unsigned op=p[0]&255;unsigned version=(p[0]>>8)&255;
  require(version==1,"board HOST payload version");
  Payload reply{};
  if(op==0x81||op==0x82) {
   bars_.push_back({rank,uint16_t(p[0]>>16),op==0x82,p[1]&3,p[3]});
  } else if(op==0x12) {
   uint64_t address=get64(p,1);require((address&7)==0,"unaligned DMA read");
   reply[0]=0x0113;reply[1]=4;put64(reply,3,load64(address));
   add_required(rank,packet(0,reply),-1);++dma_reads_;
  } else if(op==0x14) {
   uint64_t address=get64(p,1);require((address&7)==0,"unaligned DMA write");
   uint64_t old=load64(address),value=get64(p,3);unsigned mask=p[5]&255;
   for(unsigned b=0;b<8;++b)if(mask&(1u<<b)) {
    uint64_t m=uint64_t(255)<<(8*b);old=(old&~m)|(value&m);
   }
   ram_[address]=old;reply[0]=0x0115;
   add_required(rank,packet(0,reply),-1);++dma_writes_;
  } else throw std::runtime_error("unrecognized actual HOST board opcode");
  // Board has genuinely consumed this outgoing HOST word, so return one
  // source HOST credit. This is unrelated to an incoming DMA response credit.
  credit(rank,0,1);
 }
 void receive(unsigned source,const Word528& w) {
  require((w[16]&0xffff0fffu)==0,"class528 reserved/padding bits");
  unsigned cls=(w[16]>>12)&15;Payload p=payload(w);
  switch(cls) {
   case 0:board_host(source,p);break;
   case 1: {
    unsigned mask=(p[0]>>24)&255;
    require(mask&&!(mask&(mask-1)),"CTRL must retain one addressed destination");
    unsigned destination=0;while(!(mask&(1u<<destination)))++destination;
    add_required(destination,w,int(source));++ctrl_forwarded_;break;
   }
   case 5:completions_.push_back({source,get64(p,0)});credit(source,2,1);break;
   case 6:require((p[0]&~1u)==0,"IRQ reserved bits");irq_[source]=p[0]&1;break;
   case 7:returned(source,p);break;
   default:throw std::runtime_error("unexpected die-to-board class");
  }
 }
public:
 Router() { reset_all(); }
 // Invoke only after the caller observes genuine coherent reset of every port
 // and both FDI pipelines. Quiet time alone never authorizes ownership clear.
 // Board RAM persists across a HOST/link reset; outstanding callbacks flush.
 void reset_all() {
  for(unsigned r=0;r<ranks;++r) {
   q_[r].clear();tx_capacity_[r]=4;irq_[r]=false;pause_ctrl_[r]=false;
   for(unsigned g=0;g<3;++g){owners_[r][g].clear();logical_[r][g]=limit(g);}
   to_host_[r]={};to_board_[r]={};
  }
  bars_.clear();completions_.clear();
 }
 void pause_ctrl_destination(unsigned rank,bool pause) {check_rank(rank);pause_ctrl_[rank]=pause;}
 bool enqueue(unsigned destination,unsigned cls,const Payload& p) {
  require(cls<=4||cls==7,"invalid board-to-die class");
  return add(destination,packet(cls,p),-1);
 }
 bool write_bar(unsigned rank,uint16_t address,uint32_t value,unsigned strobes=15,uint16_t id=0) {
  require(address<8192&&strobes<16,"BAR address/strobe range");
  Payload p{};p[0]=0x0101|(uint32_t(id)<<16);p[1]=address;p[3]=value;p[4]=strobes;
  return enqueue(rank,0,p);
 }
 bool read_bar(unsigned rank,uint16_t address,uint16_t id=0) {
  require(address<8192,"BAR address range");Payload p{};p[0]=0x0102|(uint32_t(id)<<16);p[1]=address;
  return enqueue(rank,0,p);
 }
 bool service_begin(unsigned rank=0) { return write_bar(rank,0x10a0,1); }
 bool boot_end(unsigned rank) { Payload p{};p[0]=2;return enqueue(rank,2,p); }
 void store64(uint64_t address,uint64_t value) {
  require((address&7)==0,"unaligned fixture RAM store");ram_[address]=value;
 }
 uint64_t load64(uint64_t address)const {
  auto it=ram_.find(address);return it==ram_.end()?0:it->second;
 }
 // FMT1 descriptor/pr143/PROMPT behavior remains actual RTL. These words only
 // populate the original host RAM submission image, no native callback.
 void fmt1_descriptor(uint64_t address,uint64_t prompt_address,const std::vector<uint32_t>& tokens,
                      uint16_t max_new,uint16_t tag=0xcafe,uint32_t eos0=0x3ffff,uint32_t eos1=0x3ffff) {
  require(!tokens.empty()&&tokens.size()<=8192,"FMT1 prompt length");
  for(auto token:tokens)require(token<151936,"FMT1 vocabulary token range");
  store64(address,0x0101ull|(uint64_t(tag)<<16)|(uint64_t(tokens.size())<<32)|(uint64_t(max_new)<<48));
  store64(address+8,prompt_address);store64(address+16,0);
  store64(address+24,uint64_t(eos0)|(uint64_t(eos1)<<32));
  for(unsigned n=0;n<tokens.size();n+=2)
   store64(prompt_address+4*n,uint64_t(tokens[n])|(n+1<tokens.size()?uint64_t(tokens[n+1])<<32:0));
 }
 const std::vector<BarResponse>& bar_responses()const{return bars_;}
 const std::vector<Completion>& completions()const{return completions_;}
 bool irq(unsigned rank)const{check_rank(rank);return irq_[rank];}
 uint64_t dma_reads()const{return dma_reads_;}uint64_t dma_writes()const{return dma_writes_;}
 uint64_t ctrl_forwarded()const{return ctrl_forwarded_;}uint64_t ctrl_retired()const{return ctrl_retired_;}
 // Router state only: not proof of actual HOST/adapter/CDC/native drain.
 bool router_empty()const {
  for(unsigned r=0;r<ranks;++r) {
   if(!q_[r].empty()||tx_capacity_[r]!=4)return false;
   for(const auto& owner:owners_[r])if(!owner.empty())return false;
  }return true;
 }
 bool fdi_pipelines_empty()const {
  for(unsigned r=0;r<ranks;++r)for(unsigned i=0;i<phy_latency;++i)
   if(to_host_[r][i].v||to_board_[r][i].v)return false;
  return true;
 }
 // Call SAMPLE then DRIVE once, before the actual receiving-core rising edge.
 // Never repeat these methods during fixedpoint combinational eval iterations.
 template<class Boards>void sample_core(const Boards& board,bool core_edge_now=true) {
  if(!core_edge_now)return;
  for(unsigned r=0;r<ranks;++r) {
   auto& b=*board[r];b.core_rx_cr=0;
   if(!b.rst_n)continue;
   if(b.core_tx_cr){require(tx_capacity_[r]<4,"unowned board core TX credit");++tx_capacity_[r];}
   if(b.core_rx_v) {
    Word528 w{};for(unsigned n=0;n<17;++n)w[n]=b.core_rx_d[n];
    receive(r,w);b.core_rx_cr=1;
   }
  }
 }
 template<class Boards>void drive_core(const Boards& board,bool core_edge_now=true) {
  if(!core_edge_now)return;
  for(unsigned r=0;r<ranks;++r) {
   auto& b=*board[r];b.core_tx_v=0;
   if(!b.rst_n||!tx_capacity_[r]||q_[r].empty())continue;
   // Other independent classes may pass a stalled class, but words within
   // each application class stay in order. Credit packets have priority.
   auto selected=q_[r].end();
   for(auto it=q_[r].begin();it!=q_[r].end();++it) {
    unsigned cls=(it->word[16]>>12)&15;int g=group(cls);
    if(cls==1&&pause_ctrl_[r])continue;
    if(g<0||logical_[r][unsigned(g)]!=0){selected=it;break;}
   }
   if(selected==q_[r].end())continue;
   Queued event=*selected;q_[r].erase(selected);unsigned cls=(event.word[16]>>12)&15;int g=group(cls);
   if(g>=0){--logical_[r][unsigned(g)];owners_[r][unsigned(g)].push_back(event.origin);}
   --tx_capacity_[r];for(unsigned n=0;n<17;++n)b.core_tx_d[n]=event.word[n];b.core_tx_v=1;
  }
 }
 template<class Hosts,class Boards>void step_phy(const Hosts& host,const Boards& board) {
  // Snapshot every source first; assignments must not affect another source.
  std::array<Wire,ranks> h{},b{};
  for(unsigned r=0;r<ranks;++r) {
   h[r].v=host[r]->phy_tx_v;b[r].v=board[r]->phy_tx_v;
   for(unsigned n=0;n<33;++n){h[r].flit[n]=host[r]->phy_tx_flit[n];b[r].flit[n]=board[r]->phy_tx_flit[n];}
  }
  for(unsigned r=0;r<ranks;++r) {
   Wire hr=to_host_[r].back(),br=to_board_[r].back();
   for(unsigned n=phy_latency-1;n>0;--n){to_host_[r][n]=to_host_[r][n-1];to_board_[r][n]=to_board_[r][n-1];}
   to_host_[r][0]=b[r];to_board_[r][0]=h[r];
   if(!host[r]->host_rst_n||!board[r]->rst_n){to_host_[r]={};to_board_[r]={};hr={};br={};}
   host[r]->phy_rx_v=hr.v;board[r]->phy_rx_v=br.v;
   for(unsigned n=0;n<33;++n){host[r]->phy_rx_flit[n]=hr.flit[n];board[r]->phy_rx_flit[n]=br.flit[n];}
  }
 }
};
} // namespace qkd_host_fixture
