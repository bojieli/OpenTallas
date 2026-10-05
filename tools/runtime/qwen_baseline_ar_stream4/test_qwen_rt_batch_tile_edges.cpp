#include "qwen_rt_batch_tile_edges.hpp"
#include <cassert>
#include <memory>
#include <vector>
#include <iostream>
struct Pool {
 int worker=-1, phase=0, dispatches=0;
 std::vector<int> events;
 int size() const {return 16;}
 template<class F> void run(size_t n,F f){
  ++dispatches; ++phase;
  for(int w=0;w<16;++w){worker=w;for(size_t i=w;i<n;i+=16)f(i);}
  worker=-1;
 }
};
struct Tile {
 Pool* pool; int owner,clk=1,out=0;
 void eval(){assert(pool->worker==owner);pool->events.push_back(clk?3:1);out+=clk?101:7;}
};
struct Line {int a=0,b=0,va=0;};
struct Fabric {
 Pool& p; int stages;
 std::vector<std::unique_ptr<Tile>> t;
 std::vector<int> hl,hp;
 std::vector<std::vector<Line>> ext;
 Fabric(Pool& pool,int n,int ns,int seed):p(pool),stages(ns){
  for(int i=0;i<n;++i){t.emplace_back(new Tile{&p,i%16,1,seed+i});hl.push_back(1);hp.push_back(i/2);ext.emplace_back(ns,Line{seed,seed+1,seed+2});}
 }
 void set_clk(int c){for(auto& x:t)x->clk=c;}
 int word(int,int i){assert(p.worker>=0);p.events.push_back(2);return t[i]->out;}
 int valid(int,int i){return t[i]->out&1;}
 void edge(){
  bool lo=false;for(auto& x:t)lo|=bool(x->clk);
  if(lo){set_clk(0);p.run(t.size(),[&](size_t i){t[i]->eval();});}
  if(stages>0)p.run(t.size(),[&](size_t i){auto& e=ext[i];for(int s=stages-1;s>0;--s)e[s]=e[s-1];e[0].a=word(0,2*hp[i]);e[0].b=word(0,2*hp[i]+1);e[0].va=valid(0,2*hp[i]);});
  set_clk(1);p.run(t.size(),[&](size_t i){t[i]->eval();});
 }
};
void scenario(int ns,int mask,int cold,bool opt=true){
 Pool a,b;
 Fabric a0(a,32,ns,0),a1(a,32,ns,1000),a2(a,32,ns,2000),a3(a,32,ns,3000);
 Fabric b0(b,32,ns,0),b1(b,32,ns,1000),b2(b,32,ns,2000),b3(b,32,ns,3000);
 Fabric* x[4]={&a0,&a1,&a2,&a3};Fabric* y[4]={&b0,&b1,&b2,&b3};
 uint8_t en[4];for(int d=0;d<4;++d){en[d]=(mask>>d)&1;if((cold>>d)&1){x[d]->set_clk(0);y[d]->set_clk(0);}}
 qwen_rt_batch_tile_edges(a,x,en,4,32,ns); // default-off oracle
 qwen_rt_batch_tile_edges(b,y,en,4,32,ns,opt);
 for(int d=0;d<4;++d)for(int i=0;i<32;++i){
  assert(x[d]->t[i]->clk==y[d]->t[i]->clk&&x[d]->t[i]->out==y[d]->t[i]->out);
  for(int s=0;s<ns;++s){auto l=x[d]->ext[i][s],r=y[d]->ext[i][s];assert(l.a==r.a&&l.b==r.b&&l.va==r.va);}
 }
 if(opt){int last=0;for(int e:b.events){assert(e>=last);last=e;}assert(b.dispatches<=3);if(mask==15&&ns==4&&cold==0){assert(a.dispatches==12&&b.dispatches==3);}}
 else assert(a.events==b.events&&a.dispatches==b.dispatches);
 // Same masks on a second edge exercise retained HIGH/previous-gated state.
 qwen_rt_batch_tile_edges(a,x,en,4,32,ns);
 qwen_rt_batch_tile_edges(b,y,en,4,32,ns,opt);
 for(int d=0;d<4;++d)for(int i=0;i<32;++i){assert(x[d]->t[i]->clk==y[d]->t[i]->clk&&x[d]->t[i]->out==y[d]->t[i]->out);for(int s=0;s<ns;++s){auto l=x[d]->ext[i][s],r=y[d]->ext[i][s];assert(l.a==r.a&&l.b==r.b&&l.va==r.va);}}
}
int main(){
 for(int ns:{0,4})for(int mask=0;mask<16;++mask)for(int cold=0;cold<16;++cold)scenario(ns,mask,cold);
 scenario(4,15,0,false);
 Pool p;Fabric f(p,30,4,0);Fabric* x[1]={&f};uint8_t en[1]={1};bool rejected=false;
 try{qwen_rt_batch_tile_edges(p,x,en,1,30,4,true);}catch(const std::invalid_argument&){rejected=true;}
 assert(rejected&&p.dispatches==0&&f.t[0]->clk==1&&f.t[0]->out==0);
 std::cout<<"PASS mock phase order/ownership: 512 mixed enable/previous-clock cases, repeated edges, default serial, pre-mutation rejection; all-active dispatch12->3. No RTL/numeric/performance verdict.\n";
}
