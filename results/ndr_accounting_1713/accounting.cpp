// SPDX-License-Identifier: BSD-3-Clause
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
struct Edge  // An Edge is the routing track holder between two adjacent
             // MazePoints
{
  int16_t congCNT;
  uint16_t cap;    // the capacity of the edge
  uint16_t usage;  // the usage of the edge
  uint16_t red;
  uint16_t real_cap;  // the real capacity without user adjustment
  int16_t last_usage;
  uint16_t ndr_overflow;  // number of NDR nets in congestion
  double est_usage;       // the estimated usage of the edge

  uint16_t usage_red() const { return usage + red; }
  double est_usage_red() const { return est_usage + red; }
};
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
bool Graph2D::hasNDRCapacity(FrNet* net, int x, int y, EdgeDirection direction)
{
  const int8_t edgeCost = net->getEdgeCost();

  if (edgeCost == 1) {
    return true;
  }

  // For nets with high cost, we need at least one layer with sufficient
  // capacity
  for (int l = net->getMinLayer(); l <= net->getMaxLayer(); l++) {
    double layer_cap = 0;
    int8_t layer_edge_cost = net->getLayerEdgeCost(l);

    layer_cap = (direction == EdgeDirection::Horizontal)
                    ? h_cap_3D_[l][x][y].cap_ndr
                    : v_cap_3D_[l][x][y].cap_ndr;

    if (layer_cap >= layer_edge_cost) {
      return true;
    }
  }

  // No single layer can accommodate this NDR net
  return false;
}

double Graph2D::getCostNDRAware(FrNet* net,
                                int x,
                                int y,
                                const double edge_cost,
                                EdgeDirection direction)
{
  const int8_t edgeCost = net->getEdgeCost();

  // No processing needed for nets with 1 edge cost
  if (edgeCost == 1) {
    return edge_cost;
  }

  constexpr double OVERFLOW_COST_MULTIPLIER = 100.0;

  // Get references to the appropriate edge data based on direction
  auto& edge = (direction == EdgeDirection::Horizontal) ? h_edges_[x][y]
                                                        : v_edges_[x][y];
  auto& ndr_nets = (direction == EdgeDirection::Horizontal) ? h_ndr_nets_[x][y]
                                                            : v_ndr_nets_[x][y];

  const std::string& net_name = net->getName();
  bool is_net_present = ndr_nets.find(net) != ndr_nets.end();
  double final_edge_cost = 0;

  if (edge_cost < 0) {  // Rip-up: remove resource
    // If the net is in the list, remove it and compute the edge cost.
    // If the net is not in the list, it probably means that we are removing
    // half the edge cost a second time in the initial routing steps. But we
    // only need to count once to avoid problems when managing 3D capacity
    if (is_net_present) {
      ndr_nets.erase(net);
      // If the edge already has an overflow caused by NDR net we need to remove
      // the big edge cost value
      if (edge.ndr_overflow > 0) {
        edge.ndr_overflow--;
        final_edge_cost = -OVERFLOW_COST_MULTIPLIER * edgeCost;
      } else {
        final_edge_cost = -edgeCost;
      }
      updateNDRCapLayer(x, y, net, direction, edge_cost);
    }
  } else {  // Routing: add resource
    // If the net is not in the list, add it and compute the edge cost.
    // If the net is in the list, it probably means that we are in the
    // initial routing steps adding two times half the edge cost. But we
    // only need to count once to avoid problems when managing 3D capacity
    if (!is_net_present) {
      // If the edge already has an overflow caused by NDR net or it will have
      // an overflow due to lack of capacity in a single layer, we need to add
      // the big edge cost value
      if (edge.ndr_overflow > 0 || !hasNDRCapacity(net, x, y, direction)) {
        edge.ndr_overflow++;
        final_edge_cost = OVERFLOW_COST_MULTIPLIER * edgeCost;
      } else {
        final_edge_cost = edgeCost;
      }
      ndr_nets.insert(net);
      updateNDRCapLayer(x, y, net, direction, edge_cost);
    }
  }

  return final_edge_cost;
}

void Graph2D::updateNDRCapLayer(const int x,
                                const int y,
                                FrNet* net,
                                EdgeDirection dir,
                                const double edge_cost)
{
  const int8_t edgeCost = net->getEdgeCost();
  if (edgeCost == 1) {
    return;
  }

  auto& cap_3D = (dir == EdgeDirection::Horizontal) ? h_cap_3D_ : v_cap_3D_;
  int8_t layer_edge_cost = 0;

  for (int l = net->getMinLayer(); l <= net->getMaxLayer(); l++) {
    auto& layer_cap = cap_3D[l][x][y];
    layer_edge_cost = net->getLayerEdgeCost(l);
    if (edge_cost < 0) {  // Reducing edge usage
      // If we already have a NDR net in this layer, increase the NDR capacity
      // available again
      if (layer_cap.cap - layer_cap.cap_ndr >= layer_edge_cost) {
        layer_cap.cap_ndr += layer_edge_cost;
        return;
      }
    } else {  // Increasing edge usage
      // If there is NDR capacity available, reduce the capacity value
      if (layer_cap.cap_ndr >= layer_edge_cost) {
        layer_cap.cap_ndr -= layer_edge_cost;
        return;
      }
    }
  }

  // If the edge is already with congestion and there is no capacity available
  // in any layer, reduce the capacity available of the first layer.
  // When rippin-up, it will be the first to be released
  if (edge_cost > 0) {
    layer_edge_cost = net->getLayerEdgeCost(net->getMinLayer());
    cap_3D[net->getMinLayer()][x][y].cap_ndr -= layer_edge_cost;
  }
}

void Graph2D::updateEstUsageV(const int x,
                              const int y,
                              FrNet* net,
                              const double usage)
{
  v_edges_[x][y].est_usage
      += getCostNDRAware(net, x, y, usage, EdgeDirection::Vertical);

  if (usage > 0) {
    v_used_ggrid_.insert({x, y});
  }
}

void Graph2D::addEstUsageToUsage()
{
  foreachEdge([](Edge& edge) { edge.usage += edge.est_usage; });
}
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
 Graph2D g;g.v_cap_3D_[0][0][0]={4,4.0};g.h_cap_3D_[0][0][0]={4,4.0};
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
 int background=argc>1?std::atoi(argv[1]):16;
 if(argc>2 && std::string(argv[2])=="bad-only") {scenario("heterogeneous",4,2,background,false);return 0;}
 scenario("same_cost_negative_delta_safe",4,4,background,false);
 scenario("heterogeneous",4,2,background,false);
 scenario("heterogeneous_reverse_remove_safe",4,2,background,true);
 // A genuine positive penalized/congested quantity can have the identical stored value.
 Graph2D large;large.v_edges_[0][0].est_usage=65356.0;large.addEstUsageToUsage();
 std::cout<<"RESULT positive_control signed_before_conversion=65356 stored_usage="<<large.v_edges_[0][0].usage<<"\n";
}
