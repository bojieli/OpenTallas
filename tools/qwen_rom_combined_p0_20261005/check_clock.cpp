#include "clock.hpp"
#include <cassert>
#include <vector>

int main() {
    // Actual independent root event order, including a coincident edge and
    // a controller-only edge between successive core edges. No RTL substitute.
    qwen_combined_p0::Clocks clocks;
    bool h=false, core=false;
    std::vector<unsigned> states;
    auto ctl=[&](bool hi){h=hi;};
    auto settle=[&]{states.push_back(unsigned(h)*2+unsigned(core));};
    clocks.edge(0,ctl,[&]{core=false;},settle);
    clocks.edge(416666,ctl,[&]{core=true;},settle);
    clocks.edge(833333,ctl,[&]{core=false;},settle);
    clocks.edge(1250000,ctl,[&]{core=true;},settle);
    assert((states==std::vector<unsigned>{2,3,1,0,2,3}));
    bool refused=false;
    try {clocks.edge(10,ctl,[]{},settle);} catch(const std::logic_error&) {refused=true;}
    assert(refused);
    qwen_combined_p0::Clocks coincident(416666);
    states.clear(); h=false;core=false;
    coincident.edge(416666,ctl,[&]{core=true;},settle);
    assert((states==std::vector<unsigned>{3}));
}
