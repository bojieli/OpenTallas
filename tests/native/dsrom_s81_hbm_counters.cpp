#include "s81_minimum_hbm_counters.hpp"
#include <cassert>
using namespace dsrom_s81_minimum;
int main(){
 NativeHbmTrafficCounters c;std::array<unsigned,4> lens{2,1,4,1},owner{0,1,2,3};
 std::array<uint32_t,4> mask{0xffffffffu,0x0000ffffu,0,0};
 assert(!c.snapshot().first_observed_cycle&&!c.snapshot().index_b_active);
 c.sample(0,0,0,0,0,lens,owner,owner,mask); // no accepted events
 c.sample(4,3,0,0,2,lens,owner,owner,mask); // WINDOW read + masked CKV write
 c.sample(5,0,1,0,0,lens,owner,owner,mask); // only actual consumed response
 c.sample(6,0,0,2,0,lens,owner,owner,mask); // native completion, no new write
 c.sample(9,0,1,0,0,lens,owner,owner,mask);
 auto s=c.snapshot();assert(*s.first_observed_cycle==0&&*s.last_observed_cycle==9);
 assert(s.stack[0].owner[0].accepted_read.beats==2&&s.stack[0].total.accepted_read.bytes==64);
 assert(s.stack[0].owner[0].delivered_read.bytes==64);
 assert(*s.stack[0].total.delivered_read.first_cycle==5&&*s.stack[0].total.delivered_read.last_cycle==9);
 assert(s.stack[1].owner[1].accepted_write.beats==1&&s.stack[1].owner[1].accepted_write.bytes==16);
 assert(s.stack[1].total.accepted_write_carrier_bytes==32&&s.stack[1].observed_write_done==1);
 assert(s.stack[2].total.accepted_read.bytes==0&&!s.stack[2].total.accepted_read.first_cycle);
}
