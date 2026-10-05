// Pure fake-driver harness. No Verilator/generated models/RTL/payloads.
#include "w17_future_driver_validation.hpp"
#include <algorithm>
#include <iostream>
#include <cstdlib>
using namespace w17_future;
struct FakeDie {
    Snapshot s;
    uint32_t pc() const{return s.pc;}
    uint32_t busy() const{return s.busy;}
    uint32_t issue() const{return s.issue;}
    uint32_t fault() const{return s.fault;}
    uint32_t words() const{return s.words;}
    uint32_t sources() const{return s.sticky_sources;}
    uint64_t state() const{return s.state;}
    bool done() const{return s.done;}
};
std::vector<Snapshot> capture(const std::vector<FakeDie>& dies) {
    std::vector<Snapshot> samples;
    for(const auto& d:dies) samples.push_back({d.pc(),d.busy(),d.issue(),d.fault(),d.words(),d.sources(),d.state(),d.done()});
    return samples;
}
void require(bool b,const char* why){if(!b)throw std::runtime_error(why);}
template<class F> void rejects(F f,const char* why){bool bad=false;try{f();}catch(const std::exception&){bad=true;}require(bad,why);}
void tests() {
    std::vector<FakeDie> d(4);for(auto& x:d)x.s.pc=24;
    Monitor m(4,0,50,5);Verdict v;
    for(long c=0;c<=6;c++) {
        d[1].s.pc=uint32_t(c);for(auto& x:d){x.s.busy=c%2;x.s.words=uint32_t(c);x.s.state=uint64_t(c);}
        v=m.sample(c,capture(d));
    }
    require(std::find(v.pc_silent.begin(),v.pc_silent.end(),0)!=v.pc_silent.end(),"rank starvation masked by other PC or busy");
    require(!v.success&&!v.maxc&&v.bound_missing,"diagnostic falsely terminal or service bound claimed");
    for(auto& x:d)x.s.done=true;
    v=m.sample(7,capture(d));require(v.success,"diagnostic improperly poisons later healthy DONE");
    std::cout<<"PASS rank_starvation_and_busy_not_progress\n";

    Monitor f(4,0,20,5);
    d[2].s.fault=1;
    v=f.sample(0,capture(d));require(v.all_done&&v.fault&&!v.success,"same-edge fault AND DONE accepted");
    d[2].s.fault=0;
    v=f.sample(1,capture(d));require(v.fault&&!v.success,"late completion cleared fault");
    std::cout<<"PASS fault_done_priority_and_sticky\n";

    for(auto& x:d){x.s.done=false;x.s.state=0;x.s.fault=0;x.s.sticky_sources=0;}
    Monitor sticky(4,0,20,5);
    d[0].s.state=uint64_t(1)<<32;d[1].s.sticky_sources=4;
    v=sticky.sample(0,capture(d));require(v.fault,"existing packed/optional sticky source missed");
    std::cout<<"PASS packed_and_optional_fault_sources\n";

    Monitor deadline(4,0,100,5,10); // explicit SYNTHETIC test-only bound, not a live bound
    for(auto& x:d){x.s.state=0;x.s.sticky_sources=0;}
    deadline.sample(0,capture(d));
    for(auto& x:d){x.s.pc=25;x.s.done=true;}
    v=deadline.sample(11,capture(d));require(v.deadline&&!v.success,"late DONE reset operation deadline");
    v=deadline.sample(12,capture(d));require(v.deadline&&!v.success,"deadline not sticky");
    std::cout<<"PASS late_completion_deadline_sticky\n";

    for(auto& x:d)x.s.done=false;
    Monitor cap(4,0,10,1);
    cap.sample(0,capture(d));v=cap.sample(2,capture(d));
    require(v.bound_missing&&!v.maxc&&!v.success&&!v.pc_silent.empty(),"missing timer bound confused with MAXC");
    v=cap.sample(10,capture(d));require(v.maxc&&!v.success,"MAXC did not terminate incomplete run");
    for(auto& x:d)x.s.done=true;
    v=cap.sample(11,capture(d));require(v.maxc&&!v.success,"late completion cleared MAXC failure");
    Monitor exact(4,0,10,1);v=exact.sample(10,capture(d));require(v.success,"exact MAXC completion wrongly rejected");
    std::cout<<"PASS unknown_service_bound_and_MAXC_separation\n";

    Monitor atomic(4,0,10,1);
    auto ss=capture(d);ss[3].pc=16384;
    rejects([&]{atomic.sample(0,ss);},"invalid port accepted");
    ss[3].pc=24;v=atomic.sample(0,ss);require(v.success,"invalid sample mutated monitor");
    rejects([&]{atomic.sample(0,ss);},"duplicate clock accepted");
    std::cout<<"PASS transactional_samples\n";

    auto age=link_age(100,120,48,2);
    require(age.enqueued==72&&age.age==28&&age.overdue==0&&age.queued==2,"age not derived from actual due timestamp");
    age=link_age(125,120,48,2);require(age.age==53&&age.overdue==5,"overdue wrong");
    rejects([]{link_age(10,120,48,1);},"future enqueue accepted");
    rejects([]{due_at(std::numeric_limits<long>::max(),1);},"due overflow accepted");
    rejects([]{next_cycle(std::numeric_limits<long>::max());},"cycle overflow accepted");
    std::cout<<"PASS actual_due_timestamp_link_age\n";
}
int main(int argc,char** argv) {
    try {
        if(argc==4&&std::string(argv[1])=="parse") {
            std::string type=argv[2];uint64_t n=0;
            if(type=="cycles")n=cycles(argv[3],"test");
            else if(type=="int")n=positive_int(argv[3],"test");
            else if(type=="latency")n=latency(argv[3],"test");
            else if(type=="bool")n=boolean(argv[3],"test");
            else throw std::invalid_argument("parse kind");
            std::cout<<n<<"\n";return 0;
        }
        tests();return 0;
    } catch(const std::exception& e) {std::cerr<<"FAIL "<<e.what()<<"\n";return 2;}
}
