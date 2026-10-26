from pathlib import Path
import re,json,hashlib
r=Path(__file__).parent;s=(r/'source/pinned_graph2d.cpp').read_text();dt=(r/'source/pinned_DataType.h').read_text()
def block(text,pattern):
 m=re.search(pattern,text);assert m,pattern
 start=m.start();i=text.index('{',m.end());depth=0
 for j in range(i,len(text)):
  if text[j]=='{':depth+=1
  elif text[j]=='}':
   depth-=1
   if depth==0:return text[start:j+1]
 raise RuntimeError(pattern)
edge=block(dt,r'struct Edge\s*//')+';'
patterns=[r'bool Graph2D::hasNDRCapacity\(',r'double Graph2D::getCostNDRAware\(',r'void Graph2D::updateNDRCapLayer\(',r'void Graph2D::updateEstUsageV\(const int x,\s+const int y,',r'void Graph2D::addEstUsageToUsage\(']
methods=[block(s,p) for p in patterns]
prefix=r'''// SPDX-License-Identifier: BSD-3-Clause
// Extracted OpenROAD accounting bodies retain copyright (c) 2019-2025 The OpenROAD Authors.
// Test harness/stubs below do not run a router or reproduce an actual E5 operation stream.
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iomanip>
#include <iostream>
#include <set>
#include <string>
#include <utility>
using std::uint16_t; using std::int16_t; using std::int8_t;
enum class EdgeDirection {Horizontal,Vertical};
struct FrNet {
 std::string name; int8_t cost;
 int8_t getEdgeCost() const {return cost;}
 int8_t getLayerEdgeCost(int) const {return cost;}
 int getMinLayer()const{return 0;} int getMaxLayer()const{return 0;}
 const char* getName() const {return name.c_str();}
};
'''
klass=r'''
class Graph2D {
public:
 struct Cap3D {uint16_t cap; double cap_ndr;};
 std::array<std::array<Edge,1>,1> h_edges_{},v_edges_{};
 std::array<std::array<std::array<Cap3D,1>,1>,1> h_cap_3D_{},v_cap_3D_{};
 std::array<std::array<std::set<FrNet*>,1>,1> h_ndr_nets_{},v_ndr_nets_{};
 std::set<std::pair<int,int>> v_used_ggrid_;
 void foreachEdge(const std::function<void(Edge&)>& f){f(h_edges_[0][0]);f(v_edges_[0][0]);}
 bool hasNDRCapacity(FrNet*,int,int,EdgeDirection);
 double getCostNDRAware(FrNet*,int,int,double,EdgeDirection);
 void updateNDRCapLayer(int,int,FrNet*,EdgeDirection,double);
 void updateEstUsageV(int,int,FrNet*,double);
 void addEstUsageToUsage();
};
'''
driver=r'''
static void step(Graph2D& g,FrNet& n,double amount,const char* action) {
 auto& e=g.v_edges_[0][0]; double before=e.est_usage;auto overflow=e.ndr_overflow;
 g.updateEstUsageV(0,0,&n,amount);
 std::cout<<"TRACE action="<<action<<" net="<<n.name<<" edge=V x=0 y=0 edgeCost="<<int(n.cost)
 <<" requested="<<amount<<" returned_delta="<<e.est_usage-before
 <<" ndr_before="<<overflow<<" ndr_after="<<e.ndr_overflow
 <<" est_before="<<before<<" est_after="<<e.est_usage
 <<" present="<<g.v_ndr_nets_[0][0].size()<<" cap_ndr="<<g.v_cap_3D_[0][0][0].cap_ndr<<"\n";
}
static void scenario(const char* label,int ac,int bc,int background,bool reverse) {
 Graph2D g;g.v_cap_3D_[0][0][0]={uint16_t(ac),double(ac)};g.h_cap_3D_[0][0][0]={uint16_t(ac),double(ac)};
 auto& e=g.v_edges_[0][0];e.est_usage=background;
 FrNet a{"A",int8_t(ac)},b{"B",int8_t(bc)};
 std::cout<<"SCENARIO "<<label<<" background="<<background<<"\n";
 step(g,a,ac,"add_A");step(g,b,bc,"add_B");
 if(reverse){step(g,b,-bc,"remove_B");step(g,a,-ac,"remove_A");}
 else {step(g,a,-ac,"remove_A");}
 const double signed_before=e.usage+e.est_usage;
 g.addEstUsageToUsage();
 std::cout<<"RESULT "<<label<<" signed_before_conversion="<<signed_before<<" stored_usage="<<e.usage<<"\n";
}
int main(int argc,char** argv) {
 int background=argc>1?std::atoi(argv[1]):15;
 if(argc>2 && std::string(argv[2])=="bad-only") {scenario("heterogeneous",5,3,background,false);return 0;}
 scenario("same_cost_negative_delta_safe",5,5,background,false);
 scenario("heterogeneous",5,3,background,false);
 scenario("heterogeneous_reverse_remove_safe",5,3,background,true);
 // A genuine positive penalized/congested quantity can have the identical stored value.
 Graph2D large;large.v_edges_[0][0].est_usage=65356.0;large.addEstUsageToUsage();
 std::cout<<"RESULT positive_control signed_before_conversion=65356 stored_usage="<<large.v_edges_[0][0].usage<<"\n";
}
'''
(r/'accounting.cpp').write_text(prefix+edge+klass+'\n\n'.join(methods)+driver)
(r/'extraction.json').write_text(json.dumps({'upstream':'https://github.com/The-OpenROAD-Project/OpenROAD/tree/6cb3f2b704','methods':[p for p in patterns],'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (r/'source').glob('pinned_*')},'model_scope':'One edge, one layer; exact accounting bodies; stub FrNet/capacity; synthetic event stream, not actual E5 trace'},indent=2)+'\n')
