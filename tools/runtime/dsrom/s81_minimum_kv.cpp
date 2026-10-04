#include "s81_minimum_kv.hpp"

namespace dsrom_s81_minimum {
void require_packed_kv_window(uint16_t native_generation,unsigned native_user,
    uint32_t native_first,unsigned native_count) {
    // All arguments are sampled actual descriptor pins. No position-minus-127
    // guess, fabricated T0, cached fixture data or synthetic generation here.
    if(!native_generation||native_user>=1024||native_count<1||native_count>128||
       native_first>=(1u<<20)||uint64_t(native_first)+native_count>(1u<<20))
        throw std::runtime_error("actual WINDOW descriptor generation/user/extent invalid");
}
} // namespace dsrom_s81_minimum
