#include "actual_phy.hpp"
#include "verilated.h"
#include <iostream>
#include <algorithm>
#include <memory>
#include <string>
using namespace qwen_actual_phy;
struct Cmd {uint32_t row,bank,col; std::array<uint32_t,8> data;};
int main(int argc,char**argv){
 bool data_mut=argc>1&&std::string(argv[1])=="data_mut";
 bool ack_mut=argc>1&&std::string(argv[1])=="ack_mut";
 try{
 VerilatedContext ctx;ctx.commandArgs(argc,argv);
 Vqwen_native_hbm_pc_provider m(&ctx,"pc31");Backing phy;phy.corrupt_read=data_mut;
 m.pc=31;m.ck=0;m.pll_hbm=0;m.rst_n=0;m.hrst=0;m.fi=0;m.ki=0;
 std::fill(m.ci.data(),m.ci.data()+10,0);std::fill(m.pi.data(),m.pi.data()+10,0);std::fill(m.host_es.data(),m.host_es.data()+9,0);std::fill(m.land_es.data(),m.land_es.data()+9,0);m.eval();
 std::vector<Cmd> cmd;
 for(unsigned i=0;i<12;i++){Cmd c{100+i/4,i%2,i%4,{}};for(unsigned j=0;j<8;j++)c.data[j]=0x9e3779b9u*(8*i+j+1)^0x13579bdf;cmd.push_back(c);}
 uint64_t ck_next=553667,hb_next=512000,ckedges=0,hbedges=0;
 unsigned host_credit=4,land_credit=4,posted=0,read_posted=0,acks=0,received=0;
 bool host_live=false,land_live=false;
 for(unsigned events=0;events<200000;events++){
  bool core=ck_next<hb_next;ctx.time(core?ck_next:hb_next);
  if(core){ck_next+=416667;
   if(!m.ck){++ckedges;
    if(m.rst_n){
     if(m.host_cr)++host_credit;
     if(m.host_ack){
      auto ix=acks+(ack_mut?1:0);
      if(ix>=phy.written_keys.size()||phy.written_keys[ix]!=key(cmd[acks].row,cmd[acks].bank,cmd[acks].col))throw std::runtime_error("ACK physical write identity mismatch");
      if(hbedges<phy.written_at[ix]+12)throw std::runtime_error("ACK before actual WDONE17 deadline");++acks;
     }
     if(bits(m.land_er.data(),259,1))++land_credit;
     if(bits(m.land_er.data(),0,1)){
      if(received>=cmd.size())throw std::runtime_error("ghost read return");
      for(unsigned i=0;i<8;i++)if(bits(m.land_er.data(),1+i*32,32)!=cmd[received].data[i])throw std::runtime_error("read payload differs from posted quarter");
      if(bits(m.land_er.data(),258,1))throw std::runtime_error("uncorrectable PHY codeword");++received;
     }
     if(m.fo||m.static_fault||m.completion_fault||bits(m.land_er.data(),260,1))throw std::runtime_error("actual controller/static fault");
    }
   } else {
    // Inputs set on falling edge, accepted on the next actual core rising edge.
    std::fill(m.host_es.data(),m.host_es.data()+9,0);std::fill(m.land_es.data(),m.land_es.data()+9,0);
    if(hbedges>=160&&posted<cmd.size()&&host_credit){
     auto&c=cmd[posted++];--host_credit;
     put(m.host_es.data(),0,1,1);put(m.host_es.data(),286,2,3);put(m.host_es.data(),281,5,c.bank);put(m.host_es.data(),276,5,c.col);put(m.host_es.data(),257,19,c.row);
     for(unsigned i=0;i<8;i++)put(m.host_es.data(),1+32*i,32,c.data[i]);
    }
    if(acks==cmd.size()&&read_posted<cmd.size()&&land_credit){
     auto&c=cmd[read_posted++];--land_credit;
     put(m.land_es.data(),0,1,1);put(m.land_es.data(),281,5,c.bank);put(m.land_es.data(),276,5,c.col);put(m.land_es.data(),257,19,c.row);
    }
   }
   m.ck=!m.ck;m.eval();
  } else {hb_next+=512000;
   if(!m.pll_hbm){++hbedges;auto pi=phy.sample_hbm(m);m.pll_hbm=1;m.eval();for(unsigned i=0;i<10;i++)m.pi[i]=pi[i];m.eval();}
   else {m.pll_hbm=0;m.eval();}
   if(hbedges==8){m.rst_n=1;m.hrst=1;m.eval();}
  }
  if(received==cmd.size()){
   if(data_mut||ack_mut)throw std::runtime_error("mutant escaped observation");
   std::cout<<"PASS ACTUAL_PHY writes="<<phy.writes<<" reads="<<phy.reads<<" returns="<<phy.returns<<" host_ack="<<acks<<" quarter_bytes=32 acts="<<phy.acts<<" pre="<<phy.pres<<" ck="<<ckedges<<" hclk="<<hbedges<<" core_period_fs=833334 hbm_period_fs=1024000 RL=14 WD=5\n";return 0;
  }
 }
 throw std::runtime_error("actual controller progress missing");
 }catch(const std::exception&e){std::cout<<"OBSERVED_FAIL "<<e.what()<<"\n";return (data_mut||ack_mut)?0:1;}
}
