#include "s81_minimum_return_cut_join.hpp"
#include <array>
#include <cassert>

int main() {
    // Packed ABI test only, not a stand-in native model or hardware gate.
    std::array<uint32_t,12> pins{};
    pins.fill(0xa5a5a5a5);
    const auto before=pins;
    // Region10 position bits30..32 straddle a native wide-word boundary.
    dsrom_s81_minimum::root_pin_field(pins,30,3,5);
    for(unsigned b=0;b<384;b++) {
        const auto actual=(pins[b/32]>>(b%32))&1;
        const auto expected=b>=30&&b<33 ? (5u>>(b-30))&1 :
                            (before[b/32]>>(b%32))&1;
        assert(actual==expected);
    }
    dsrom_s81_minimum::root_pin_field(pins,32*11,32,0x80000001);
    assert(pins[11]==0x80000001);
    bool refused=false;
    try{dsrom_s81_minimum::root_pin_field(pins,0,3,8);}
    catch(const std::runtime_error&){refused=true;}
    assert(refused);
}
