import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class MinimumStage(unittest.TestCase):
    def test_native_owner_visible_and_reset_boundaries(self):
        source = r'''
#include <cassert>
#include "s81_minimum_pair_stage.hpp"
using namespace dsrom_s81_minimum;
template<class F>void refuses(F f){bool bad=false;try{f();}catch(const std::runtime_error&){bad=true;}assert(bad);}
int main(){
 PairResult raw;raw.valid=3;raw.error=2;raw.values=(uint64_t(0x3f800000)<<32)|0x80000000;
 raw.rows=(23u<<16)|17;raw.positions=(5u<<3)|2;
 raw.segments=(11u<<5)|7;raw.segment_counts=(19u<<5)|13;
 auto a=partial(raw,0),b=partial(raw,1);
 assert(a.valid&&!a.error&&a.fp32_bits==0x80000000&&a.row==17&&a.position==2&&a.segment==7&&a.segments==13);
 assert(b.valid&&b.error&&b.fp32_bits==0x3f800000&&b.row==23&&b.position==5&&b.segment==11&&b.segments==19);
 refuses([&]{partial(raw,2);});
 NativeVmReceipts q;VmWord w;w.address=4;w.mask=1;w.data[0]=0x80000000;w.owner[0]=19;
 CaptureOwner s;s.identity=19;s.phase=2;s.row=0;s.root=0;s.element_address=64;
 VmReceipt ack{w.address,w.mask,w.owner};
 refuses([&]{q.accepted(0,w,s,1,false);});assert(q.empty());
 refuses([&]{q.accepted(1,w,s,1,true);});assert(q.empty());
 auto aliases=s;aliases.element_address=65+(1u<<19);
 refuses([&]{q.accepted(0,w,aliases,1,true);});assert(q.empty());
 refuses([&]{q.accepted(0,w,s,2,true);});assert(q.empty());
 q.accepted(0,w,s,1,true);assert(q.outstanding()==1);
 auto wrong=ack;wrong.owner[0]^=1;
 refuses([&]{q.visible(0,wrong,true);});assert(q.outstanding()==1);
 wrong=ack;wrong.mask=2;
 refuses([&]{q.visible(0,wrong,true);});assert(q.outstanding()==1);
 refuses([&]{q.cold_fenced(true);});assert(q.outstanding()==1);
 q.warm_reset();assert(q.quarantine()&&q.outstanding()==1);
 refuses([&]{q.accepted(0,w,s,1,true);});
 assert(q.visible(0,ack,true)==1);assert(q.empty()&&q.quarantine());
 refuses([&]{q.visible(0,ack,true);});
 refuses([&]{q.cold_fenced(false);});q.cold_fenced(true);
 assert(!q.quarantine()&&q.empty());
 // Finite accepted pipeline, no unlimited observer seats or timer retirement.
 for(unsigned i=0;i<4;i++){w.address=uint16_t(4*i);s.element_address=16*w.address;w.owner[0]=100+i;q.accepted(0,w,s,1,true);}
 assert(!q.can_observe_accept(0)&&q.outstanding()==4);
 refuses([&]{q.accepted(0,w,s,1,true);});
 for(unsigned i=0;i<4;i++){ack.address=uint16_t(4*i);ack.owner[0]=100+i;assert(q.visible(0,ack,true)==1);}
 assert(q.empty());
}
'''
        with tempfile.TemporaryDirectory() as td:
            cpp = Path(td) / "check.cpp"
            cpp.write_text(source)
            exe = Path(td) / "check"
            subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                            "-I"+str(ROOT/"tools/runtime/dsrom"),
                            "-I"+str(ROOT/"rtl/test/v41_runtime"),
                            str(cpp), "-o", str(exe)], check=True)
            subprocess.run([str(exe)], check=True)

if __name__ == "__main__":
    unittest.main()
