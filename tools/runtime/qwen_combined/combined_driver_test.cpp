#include "combined_driver.hpp"
#include <iostream>
#include <string>
#include <vector>
using namespace qwen_combined;
static unsigned checks=0;
static void require(bool x) {if(!x)throw std::runtime_error("control failed");++checks;}
template<class F>void rejects(F f) {bool bad=false;try{f();}catch(const std::exception&){bad=true;}require(bad);}
static Edges cr{1,true,false,true,false};
static RankPins pins(unsigned l=0) {
    return {true,false,false,false,false,true,false,l,128,6280,l,128,false,false,false,false,false};
}
static void arm(LayerFence& f,RankPins& p) {
    p.stage_start=true;f.observe(p,cr);p.stage_start=false;p.kv_arm=true;
    p.core_start=true;p.kv_layer_start=true;f.observe(p,cr);
    p.kv_arm=false;p.core_start=false;p.kv_layer_start=false;
}
// Driver fixture models only edge sampling and arm recurrence, no numerical or
// memory implementation. These controls never qualify the combined hardware.
struct Binding {
    bool c=false,s=false,pulse=false;uint64_t now=0;
    std::array<RankPins,4> p;
    Binding(){for(auto& x:p)x=pins();}
    void check_geometry(){require_join_geometry(6144,64,18,44,true,true);}
    void set_time_fs(uint64_t t){now=t;}
    void drive_clocks(bool cc,bool ss){
        if(cc&&!c)for(auto& x:p) {x.kv_arm=x.stage_start?true:(x.core_start?false:x.kv_arm);}
        c=cc;s=ss;
    }
    void eval(){}
    void set_stage(unsigned l,unsigned pos,unsigned tok){for(auto& x:p){x.layer=l;x.pos=pos;x.token=tok;x.service_layer=l;x.service_pos=pos;}}
    void pulse_stage_start(bool v){pulse=v;for(auto& x:p)x.stage_start=v;}
    RankPins sample(unsigned r)const{return p.at(r);}
};
int main(){
    ClockDriver clocks({8,4},{10,3});
    std::vector<uint64_t> core,service;
    for(int i=0;i<60;++i){auto e=clocks.next();if(e.core_rise())core.push_back(e.time_fs);if(e.service_rise())service.push_back(e.time_fs);}
    require(core[0]==4&&service[0]==3);
    for(unsigned i=1;i<core.size();++i)require(core[i]-core[i-1]==8);
    for(unsigned i=1;i<service.size();++i)require(service[i]-service[i-1]==10);
    ClockDriver tied({8,4},{8,4});auto e=tied.next();require(e.core_rise()&&e.service_rise());
    e=tied.next();require(!e.core_high&&!e.service_high&&e.time_fs==8);
    rejects([]{ClockDriver x({0,1},{8,1});});rejects([]{ClockDriver x({7,1},{8,1});});
    rejects([]{ClockDriver x({8,0},{8,1});});
    rejects([]{ClockDriver x({8,UINT64_MAX-1},{8,UINT64_MAX});x.next();});
    LayerFence f;auto p=pins();f.begin(0,128,6280);arm(f,p);
    // Additional core segments in the SAME layer never restart the service.
    p.core_start=true;f.observe(p,cr);p.core_start=false;
    p.service_start=true;f.observe(p,cr);p.service_start=false;
    p.stage_done=true;p.kv_ok=p.row_drained=true;require(!f.can_retire(p));
    rejects([&]{f.retire(p);});p.write_drained=true;require(f.can_retire(p));f.retire(p);
    f.begin(1,128,6280);p=pins(1);arm(f,p);p.service_start=true;f.observe(p,cr);p.service_start=false;
    p.stage_done=p.kv_ok=p.write_drained=p.row_drained=true;f.retire(p);require(true);
    rejects([]{LayerFence x;x.begin(36,1,1);});
    rejects([]{LayerFence x;x.begin(0,8192,1);});
    rejects([]{LayerFence x;x.begin(0,1,1);x.begin(1,1,1);});
    rejects([]{LayerFence x;auto p=pins();x.begin(0,128,6280);arm(x,p);p.kv_arm=true;x.observe(p,cr);});
    rejects([]{LayerFence x;auto p=pins();x.begin(0,128,6280);p.core_start=true;p.kv_layer_start=true;x.observe(p,cr);});
    rejects([]{LayerFence x;auto p=pins();x.begin(0,128,6280);arm(x,p);p.service_start=true;p.service_layer=1;x.observe(p,cr);});
    rejects([]{LayerFence x;auto p=pins();x.begin(0,128,6280);arm(x,p);p.service_start=true;x.observe(p,cr);x.observe(p,cr);});
    rejects([]{LayerFence x;auto p=pins();x.begin(0,128,6280);arm(x,p);p.stage_start=true;x.observe(p,cr);p.stage_start=false;p.kv_arm=p.core_start=p.kv_layer_start=true;x.observe(p,cr);});
    rejects([]{LayerFence x;auto p=pins();p.fault=true;x.observe(p,cr);});
    LayerFence embed;auto ep=pins(255);embed.begin(255,128,6280);
    ep.stage_start=true;embed.observe(ep,cr);ep.stage_start=false;ep.kv_arm=ep.core_start=true;
    embed.observe(ep,cr);ep.kv_arm=ep.core_start=false;ep.stage_done=true;require(embed.can_retire(ep));embed.retire(ep);
    Binding b;CombinedDriver<Binding> driver(b,{8,4},{10,3});driver.begin(0,128,6280);
    driver.step();require(b.pulse);driver.step();require(!b.pulse&&b.now==4);
    for(auto& x:b.p){x.core_start=x.kv_layer_start=true;}
    while(!driver.step().core_rise()){};
    for(auto& x:b.p){x.core_start=x.kv_layer_start=false;x.service_start=true;}
    while(!driver.step().core_rise()){};
    for(auto& x:b.p){x.service_start=false;x.stage_done=x.kv_ok=x.write_drained=x.row_drained=true;}
    b.p[3].write_drained=false;require(!driver.ready_to_retire());rejects([&]{driver.retire();});
    b.p[3].write_drained=true;require(driver.ready_to_retire());driver.retire();
    std::cout<<"PASS "<<checks<<" driver controls (not RTL/full-token qualification)\n";
}
