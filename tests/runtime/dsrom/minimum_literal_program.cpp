#include "s81_minimum_prefix.hpp"
#include <cassert>
#include <set>
// Sequencer boundary fixture only; no native arithmetic or token result.
DsromS81MinimumEmbedding::DsromS81MinimumEmbedding(DsromS81MinimumRuntime&,const std::string&,
    const std::string&,uint32_t,uint32_t,uint64_t,uint32_t,DsromS81EmbeddingSink){}
bool DsromS81MinimumEmbedding::complete()const{return true;}
int main(){
 DsromS81MinimumRuntime runtime{};runtime.stage=80;runtime.identity=17;
 DsromS81MinimumEmbedding embedding(runtime,"","",0,0,17,0,{});
 bool go=false,drained=false,cold_visible=true;unsigned driving=0;std::set<unsigned> accepted,published;
 auto engine=[&](const char* name){
  DsromS81PrefixNativeEngine e;
  e.participant={name,[](auto){},[](bool){},[](bool){},[](){return false;}};
  e.ready=[](){return true;};e.idle=[&](){return drained;};
  e.inputs_ready=[](auto){return true;};
  e.drive=[&](const auto& op,bool take){if(take){go=true;driving=op.index;}};
  return e;
 };
 DsromS81PrefixVm vm;
 vm.instruction_accepted=[&](auto id,unsigned i){assert(id==17&&go&&driving==i);assert(accepted.insert(i).second);go=false;};
 vm.cold_inputs_visible=[&](auto){return cold_visible;};
 vm.outputs_visible=[&](auto,unsigned i){return published.count(i)!=0;};
 vm.fault=[](){return false;};vm.xn_span=[](auto,auto){return std::optional<std::array<uint32_t,16>>{};};
 auto op=dsrom_s81_l0_prefix_operations()[0];std::vector<DsromS81PrefixOperation> program;
 for(unsigned i=20;i<29;++i){op.index=i;program.push_back(op);}
 DsromS81MinimumPrefix execute(runtime,embedding,17,engine("su"),engine("he"),vm,program,{{4,engine("xu")}});
 auto edge=[&](bool release){for(auto& p:runtime.participants)p.prepare({});for(auto& p:runtime.participants)p.rising(release);for(auto& p:runtime.participants)p.falling(release);};
 edge(false);execute.start();edge(true);assert(accepted.count(20));
 published.insert(20);edge(true);assert(accepted.size()==1&&!execute.complete()); // staged/active debt blocks retirement, not launch
 published.erase(20);
 drained=true;
 edge(true);assert(accepted.size()==1&&!execute.complete()); // idle alone cannot advance
 for(unsigned i=20;i<29;++i){published.insert(i);edge(true);}
 assert(execute.complete()&&accepted.size()==9);
 op.index=30;op.unit=4;execute.load_program({op});edge(true);assert(accepted.count(30)&&!execute.complete());
 published.insert(30);edge(true);assert(execute.complete());
 bool refused=false;try{execute.xn_span(46464);}catch(const std::runtime_error&){refused=true;}assert(refused);
 // Source-only entry still needs positive target publication before GO.
 accepted.clear();published.clear();cold_visible=false;drained=false;go=false;
 DsromS81MinimumRuntime target{};target.stage=37;target.identity=17;
 op.index=40;
 DsromS81MinimumPrefix source(target,17,engine("su"),engine("he"),vm,{op},{{4,engine("xu")}});
 auto target_edge=[&](bool release){for(auto& p:target.participants)p.prepare({});for(auto& p:target.participants)p.rising(release);for(auto& p:target.participants)p.falling(release);};
 target_edge(false);source.start();target_edge(true);assert(accepted.empty());
 cold_visible=true;target_edge(true);assert(accepted.count(40));
 published.insert(40);target_edge(true);assert(!source.complete());
 drained=true;target_edge(true);assert(source.complete());
}
