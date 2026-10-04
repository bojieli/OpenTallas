"""Source-span lease extension tests; no previous binder/provider gate rerun."""
import pathlib
import subprocess
import tempfile
import unittest
from test_dsrom_s81_embedding_macro_sink import PORTS
ROOT=pathlib.Path(__file__).resolve().parents[1]
CPP=PORTS+r'''

#include "s81_published_span_macro_sink.hpp"
#include <map>
#ifdef S81_REAL_NATIVE_VM
#include "Vnative_vm.h"
using TargetModel=Vnative_vm;
#else
struct TargetModel:Ports {
    bool rd_accept_v=0,rd_out_v=0;
    unsigned rd_out_rot=0;
    std::array<uint32_t,8> rd_out_owner{};
    std::array<uint32_t,64> rd_out_bank_words{};
    struct Read {bool valid=0;uint16_t addr=0;std::array<uint32_t,8> owner{};};
    std::array<Read,4> reads{};
    std::map<unsigned,uint32_t> storage;
    void eval() {
        const bool rising=clk&&!oldclk;
        rd_accept_v=rst_n&&rd_v;
        if(rising) {
            if(!rst_n){reads={};rd_out_v=0;}
            else {
                auto old=reads[3];rd_out_v=old.valid;rd_out_owner=old.owner;
                rd_out_rot=old.addr&3;
                if(old.valid)for(unsigned b=0;b<4;b++)for(unsigned k=0;k<16;k++)
                    rd_out_bank_words[b*16+k]=storage[(old.addr+b)*16+k];
                reads[3]=reads[2];reads[2]=reads[1];reads[1]=reads[0];
                reads[0]={rd_accept_v,rd_base_word,rd_owner};
                for(unsigned b=0;b<4;b++)if(wr_v&(1u<<b)) {
                    unsigned address=(wr_word_addr>>(15*b))&32767;
                    unsigned mask=(wr_lane_mask>>(16*b))&65535;
                    for(unsigned k=0;k<16;k++)if(mask&(1u<<k))storage[address*16+k]=wr_word_data[b*16+k];
                }
            }
        }
        Ports::eval();
    }
};
#endif
MacroWrite fixture_record(const S81EmbeddingOutput& o,unsigned n) {
    // Directed test provenance only; production caller supplies source encoding.
    MacroWrite c;const unsigned address=o.vm_address+n,k=address&15;
    c.word.address=address>>4;c.word.mask=uint16_t(1)<<k;c.word.data[k]=o.vm_data[n];
    c.word.owner={uint32_t(o.vm_identity),uint32_t(o.vm_identity>>32),address,0x88991122,0xfadebeef,6,7,7};
    c.source={o.vm_identity,0,uint16_t(address),0,0,address};return c;
}
S81EmbeddingOutput batch(unsigned address=64) {
    S81EmbeddingOutput o{};o.vm_valid=1;o.vm_identity=123;o.vm_address=address;
    const uint32_t patterns[]={0x80000000,0x7fc0abcd,0x7f800000,0xff800000,0x00000001,0x3f800000};
    for(unsigned n=0;n<16;n++){o.vm_data[n]=patterns[n%6];}
    return o;
}

struct LeaseRun {
    TargetModel vm;
    bool lease=false,write_allowed=true;
    unsigned acknowledgments=0;
    PublishedSpanMacroSink<TargetModel> binder{vm,123,64,fixture_record,
        [this](uint64_t id,uint32_t a,unsigned n){return lease&&id==123&&a>=46464&&uint64_t(a)+n<=51584;},
        [this](uint64_t id,uint32_t a,unsigned n){return write_allowed&&id==123&&a>=46464&&uint64_t(a)+n<=51584;},
        [this](const MacroWrite& c,const VmReceipt& r){assert(c.word.owner==r.owner);acknowledgments++;}};
    DsromS81MinimumParticipant p=binder.participant();
    LeaseRun(){tick(false);}
    void tick(bool released=true){p.prepare({});p.rising(released);p.falling(released);}
};
int main() {
    // Metadata declarations / even a true external callback do NOT write XN.
    {LeaseRun r;r.lease=true;refuses([&]{r.binder.target_word(46464,{});});assert(r.binder.fault());}
    {LeaseRun r;auto o=batch(46464);assert(r.binder.offer_prefix(o,16));
     for(unsigned i=0;i<18;i++){r.tick();assert(!r.binder.visible_prefix(o,16));}
     r.tick();assert(r.binder.visible_prefix(o,16)&&r.acknowledgments==16);
     // Actual ACKs alone don't grant the source producer's complete lease.
     refuses([&]{r.binder.target_word(46464,fixture_record(o,0).word.owner);});assert(r.binder.fault());}
    {LeaseRun r;for(unsigned address=46464;address<51584;address+=16) {
        auto o=batch(address);r.binder.offer_prefix(o,16);
        for(unsigned i=0;i<19;i++){r.tick();}
        assert(r.binder.visible_prefix(o,16));
     }
     assert(r.acknowledgments==5120);assert(!r.binder.source_span_lease(123,46464,5120));r.lease=true;
     assert(r.binder.source_span_lease(123,46464,5120));
     assert(!r.binder.source_span_lease(124,46464,5120));
     assert(!r.binder.source_span_lease(123,46463,5121));
     assert(!r.binder.source_span_lease(123,46464,5121));
     for(unsigned a:{46464u,51583u}) {
         auto o=batch(a&~15u);auto owner=fixture_record(o,a&15).word.owner;
         assert(!r.binder.target_word(a,owner));for(unsigned i=0;i<5;i++){r.tick();}
         auto bits=r.binder.target_word(a,owner);assert(bits&&*bits==o.vm_data[a&15]);
     }
     refuses([&]{r.binder.target_word(51584,{});});assert(r.binder.fault());}
    {LeaseRun r;auto o=batch(46464);r.binder.offer_prefix(o,1);
     for(unsigned i=0;i<3;i++){r.tick();assert(!r.binder.visible_prefix(o,1));}
     r.tick();assert(r.binder.visible_prefix(o,1)&&r.acknowledgments==1);
     r.lease=true;auto owner=fixture_record(o,0).word.owner;
     assert(!r.binder.target_word(46464,owner));for(unsigned i=0;i<5;i++){r.tick();}
     assert(r.binder.target_word(46464,owner));
     // Literal source rewrite revokes old data/read cache until new ACK.
     o.vm_data[0]=0x11223344;r.binder.offer_prefix(o,1);
     refuses([&]{r.binder.target_word(46464,owner);});assert(r.binder.fault());}
    {LeaseRun r;auto o=batch(46464);r.binder.offer_prefix(o,1);
     for(unsigned i=0;i<4;i++){r.tick();}r.binder.visible_prefix(o,1);r.lease=true;
     assert(!r.binder.target_word(46464,fixture_record(o,0).word.owner));r.tick();r.lease=false;
     refuses([&]{r.tick();});assert(r.binder.fault());}
    {LeaseRun r;r.write_allowed=false;refuses([&]{r.binder.offer_prefix(batch(46464),16);});assert(r.acknowledgments==0);}
    {LeaseRun r;refuses([&]{r.binder.offer_prefix(batch(64),16);});assert(r.acknowledgments==0);}
    {LeaseRun r;refuses([&]{r.binder.offer_prefix(batch(51583),16);});assert(r.acknowledgments==0);}
    std::cout<<"PASS source lease: complete5120 XN ACKs, first/last native reads, scalar reduction, unwritten/partial/no-source/rewrite/revoked/range refusal\n";
}
'''
class TestPublishedSpan(unittest.TestCase):
    def test_actual_ack_and_source_lease_are_both_required(self):
        with tempfile.TemporaryDirectory(prefix="s81-span-lease-") as d:
            source=pathlib.Path(d)/"check.cpp";binary=pathlib.Path(d)/"check"
            source.write_text(CPP)
            subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror",
                "-I",str(ROOT/"tools/runtime/dsrom"),"-I",str(ROOT/"rtl/test/v41_runtime"),
                str(source),"-o",str(binary)],check=True)
            result=subprocess.run([str(binary)],check=True,text=True,capture_output=True)
            self.assertIn("PASS source lease:",result.stdout)
if __name__=="__main__":unittest.main()
