#include "Vot_ds_hbm_simulator20.h"
#include "verilated.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>

struct Simulation {
 std::unique_ptr<VerilatedContext> context{new VerilatedContext};
 std::unique_ptr<Vot_ds_hbm_simulator20> top;
 std::array<uint64_t,4> next{{416,500,450,2000}};
 const std::array<uint64_t,4> period{{833,1000,900,4000}};
 std::array<bool,4> level{{false,false,false,false}};
 uint64_t cycles=0;
 Simulation(int argc,char**argv) {
  context->commandArgs(argc,argv);top.reset(new Vot_ds_hbm_simulator20(context.get()));
  top->por_n=0;top->clk_sm=top->clk_mem=top->clk_link=top->clk_host=0;
  top->cmd_we=top->db_v=top->cpl_rdy=top->im_we=0;
  top->cmd_addr=top->im_addr=0;top->im_data=0;
  top->db_token=top->db_pos=top->db_job=top->db_generation=0;
  for(int i=0;i<4;i++)top->cmd_wdata[i]=0;
  top->eval();
 }
 bool event() {
  auto at=std::min_element(next.begin(),next.end())-next.begin();
  context->time(next[at]);
  // All coincident clocks are updated before evaluation.
  bool smrise=false; auto now=context->time();
  for(int i=0;i<4;i++)if(next[i]==now){
   level[i]=!level[i];next[i]+=level[i]?period[i]-period[i]/2:period[i]/2;
   if(i==0){top->clk_sm=level[i];smrise=level[i];}
   if(i==1)top->clk_mem=level[i];if(i==2)top->clk_link=level[i];if(i==3)top->clk_host=level[i];
  }
  top->eval();if(context->gotFinish())throw std::runtime_error("RTL terminal before requested completion");
  if(smrise)cycles++;return smrise;
 }
 void tick() {
  while(!event()){}
  uint64_t target=next[0]+period[0]/2-1; // stable pre-edge sample before next SM rise
  while(*std::min_element(next.begin(),next.end())<=target)event();
  context->time(target);top->eval();
 }
 static uint64_t wide(const uint32_t*data,int offset,int count){
  uint64_t value=0;for(int i=0;i<count;i++)value|=uint64_t((data[(offset+i)/32]>>((offset+i)%32))&1)<<i;
  return value;
 }
 void snapshot(){
  std::cout<<"DS20_REPLY {\"rst_sm_n\":"<<unsigned(top->rst_sm_n)<<",\"sys_fault\":"<<unsigned(top->sys_fault)
   <<",\"cycle\":"<<cycles<<",\"time_ps\":"<<context->time()<<",\"dies\":[";
  for(int d=0;d<2;d++){
   if(d)std::cout<<",";
   std::cout<<"{\"db_rdy\":"<<((top->db_rdy>>d)&1)<<",\"cpl_v\":"<<((top->cpl_v>>d)&1)
    <<",\"cpl_lo\":"<<wide(top->cpl_data.data(),d*109,64)<<",\"cpl_hi\":"<<wide(top->cpl_data.data(),d*109+64,45)<<"}";
  }
  std::cout<<"],\"sms\":[";
  for(int i=0;i<4;i++){
   if(i)std::cout<<",";
   std::cout<<"{\"die\":"<<i/2<<",\"sm\":"<<i%2<<",\"pc\":"<<top->debug_pc[i]
    <<",\"instructions\":"<<top->debug_instructions[i]<<",\"stall_mem\":"<<top->debug_stall_mem[i]
    <<",\"busy\":"<<((top->debug_busy>>i)&1)<<"}";
  }
  std::cout<<"]}"<<std::endl;
 }
 void drive(std::istringstream& in){
  uint64_t d,we,addr,data,v,tok,pos,job,gen,ready;
  if(!(in>>d>>we>>addr>>data>>v>>tok>>pos>>job>>gen>>ready) || d>=2 || we>1 || addr>=256 || v>1 || tok>=131072 || pos>=1048576 || job>=(uint64_t(1)<<32) || gen>=16 || ready>1)
   throw std::runtime_error("invalid physical CP20 drive fields");
  auto bit=[d](auto &port,uint64_t val){port=(port&~(uint64_t(1)<<d))|(val<<d);};
  bit(top->cmd_we,we);bit(top->db_v,v);bit(top->cpl_rdy,ready);
  top->cmd_addr=(top->cmd_addr&~(uint32_t(255)<<(d*8)))|(addr<<(d*8));
  top->cmd_wdata[2*d]=uint32_t(data);top->cmd_wdata[2*d+1]=uint32_t(data>>32);
  top->db_token=(top->db_token&~(uint64_t(131071)<<(d*17)))|(tok<<(d*17));
  top->db_pos=(top->db_pos&~(uint64_t(1048575)<<(d*20)))|(pos<<(d*20));
  top->db_job=(top->db_job&~(uint64_t(0xffffffff)<<(d*32)))|(job<<(d*32));
  top->db_generation=(top->db_generation&~(uint32_t(15)<<(d*4)))|(gen<<(d*4));
  top->eval();
 }
 void load(std::istringstream& in){
  int d,s;std::string path;if(!(in>>d>>s>>path)||d<0||d>=2||s<0||s>=2)throw std::runtime_error("invalid instruction image binding");
  if(top->db_rdy!=3 || top->cpl_v || top->debug_busy)throw std::runtime_error("IMEM is owned by a live kernel");
  std::ifstream file(path);if(!file)throw std::runtime_error("missing native instruction image");
  std::string line;unsigned address=0;
  while(std::getline(file,line)){
   if(line.empty())continue;
   if(address>=16384)throw std::runtime_error("native image exceeds IMEM");
   size_t used=0;auto word=std::stoull(line,&used,16);
   if(used!=line.size())throw std::runtime_error("malformed native image word");
   top->im_we=1<<(d*2+s);top->im_addr=address++;top->im_data=word;top->eval();tick();
  }
  if(!address)throw std::runtime_error("empty native image");
  top->im_we=0;top->eval();std::cout<<"DS20_REPLY {\"loaded_words\":"<<address<<"}"<<std::endl;
 }
};
int main(int argc,char**argv){
 try{
  Simulation sim(argc,argv);std::string line;
  while(std::getline(std::cin,line)){
   std::istringstream in(line);std::string cmd;in>>cmd;
   if(cmd=="RESET"){
    if(sim.cycles)throw std::runtime_error("refuse reset of an existing simulator owner");
    for(int i=0;i<32;i++)sim.tick();sim.top->por_n=1;sim.top->eval();
    while(!sim.top->rst_sm_n)sim.tick();sim.snapshot();
   }else if(cmd=="SNAP")sim.snapshot();
   else if(cmd=="TICK"){sim.tick();sim.snapshot();}
   else if(cmd=="DRIVE"){sim.drive(in);std::cout<<"DS20_REPLY {}"<<std::endl;}
   else if(cmd=="LOAD")sim.load(in);
   else if(cmd=="CLOSE"){
    if(sim.top->debug_busy || sim.top->cpl_v)throw std::runtime_error("refuse closing an active kernel");
    sim.top->final();std::cout<<"DS20_REPLY {}"<<std::endl;return 0;
   }else throw std::runtime_error("unknown simulator command");
  }
  throw std::runtime_error("owner connection lost; no completion fabricated");
 }catch(const std::exception&e){std::cerr<<"DS20_ERROR "<<e.what()<<std::endl;return 1;}
}
