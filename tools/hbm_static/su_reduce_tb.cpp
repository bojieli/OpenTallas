#include "Vot_hbm_su_reduce_static.h"
#include "verilated.h"
#include <fstream>
#include <vector>
#include <iostream>
#include <string>
struct C{uint64_t cycle;unsigned op,a,b,d,x,tag;};
struct E{uint64_t cycle;unsigned tag,x,bf;};
int main(int argc,char**argv){
 Verilated::commandArgs(argc,argv);Vot_hbm_su_reduce_static t;
 std::string dir=argv[1],mut=argc>2?argv[2]:"";std::ifstream f(dir+"/commands.txt"),g(dir+"/expected.txt");
 std::vector<C> cs;C c;while(f>>c.cycle>>c.op>>c.a>>c.b>>c.d>>c.x>>c.tag)cs.push_back(c);
 std::vector<E> es;E e;while(g>>e.cycle>>e.tag>>e.x>>e.bf)es.push_back(e);
 if(cs.empty()||es.empty())return 3;
 if(mut=="phase")for(auto &q:cs)if(q.op==4)--q.cycle;
 t.rst_n=0;t.cmd_valid=0;t.clk=0;t.eval();t.clk=1;t.eval();t.clk=0;t.eval();t.rst_n=1;

 if(mut=="poison_max"){
  // RealSRAM persists through reset: poisonLOADfault, then test nativeMAX finiteguard.
  t.cmd_valid=1;t.cmd_op=0;t.cmd_dst=0;t.operand_fp32=0x7f800000;
  for(int j=0;j<9;j++){if(j)t.cmd_valid=0;t.clk=0;t.eval();t.clk=1;t.eval();}
  if(!t.fault){std::cerr<<"FAIL missing nonfiniteLOADfault\n";return 2;}
  t.rst_n=0;t.cmd_valid=0;t.clk=0;t.eval();t.clk=1;t.eval();t.rst_n=1;
  t.cmd_valid=1;t.cmd_op=3;t.cmd_a=0;t.cmd_dst=0;t.operand_fp32=0x3f800000;
  t.clk=0;t.eval();t.clk=1;t.eval();t.cmd_valid=0;t.clk=0;t.eval();t.clk=1;t.eval();t.clk=0;t.eval();t.clk=1;t.eval();
  if(!t.fault){std::cerr<<"FAIL missing poisonedSRAMMAXfault\n";return 2;}
  std::cout<<"PASS nonfiniteLOADandpersistentSRAMMAXfault\n";return 0;
 }
 size_t ci=0,ei=0;uint64_t end=cs.back().cycle+20;
 for(uint64_t k=0;k<end;k++){
  t.cmd_valid=ci<cs.size()&&cs[ci].cycle==k;
  if(t.cmd_valid){auto q=cs[ci++];t.cmd_op=q.op;t.cmd_a=q.a;t.cmd_b=q.b;t.cmd_dst=q.d;t.operand_fp32=q.x;t.cmd_tag=q.tag;
   if(mut=="identity"&&q.op==4)t.cmd_tag=q.tag^1;
  }
  t.clk=0;t.eval();t.clk=1;t.eval();
  if(t.fault){std::cerr<<"FAIL fault cycle="<<k<<"\n";return 1;}
  if(t.scalar_valid){if(ei>=es.size())return 1;auto w=es[ei++];
   uint64_t want=w.cycle;
   if((mut!="wrongtree"&&k!=want)||t.scalar_tag!=w.tag||t.scalar_fp32!=w.x||t.scalar_bf16!=w.bf){std::cerr<<"FAIL scalar cycle="<<k<<" expected_cycle="<<want<<" tag="<<t.scalar_tag<<" expected_tag="<<w.tag<<" fp32="<<std::hex<<t.scalar_fp32<<" expected="<<w.x<<"\n";return 1;}
  }
 }
 if(ei!=es.size())return 1;std::cout<<"PASS scalars="<<ei<<" cycles="<<end<<" actual LAT6 arithmetic two nativeSRAM replicas\n";return 0;
}
