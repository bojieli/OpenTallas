"""New actual-accept callback checks only; prior binder/provider gates untouched."""
import pathlib
import subprocess
import tempfile
import unittest
from test_dsrom_s81_embedding_macro_sink import PORTS
ROOT=pathlib.Path(__file__).resolve().parents[1]
CPP=PORTS+r'''


#include "s81_published_span_accept_sink.hpp"
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


struct AcceptRun {
    TargetModel vm;
    unsigned writes_seen=0,reads_seen=0,acks_seen=0;
    bool throw_observer=false,throw_read=false;
    std::vector<unsigned> banks;
    PublishedSpanAcceptSink<TargetModel> binder{vm,123,64,fixture_record,
        [](uint64_t id,uint32_t a,unsigned n){return id==123&&a>=46464&&uint64_t(a)+n<=51584;},
        [](uint64_t id,uint32_t a,unsigned n){return id==123&&a>=46464&&uint64_t(a)+n<=51584;},
        [this](const MacroWrite&,const VmReceipt&){acks_seen++;},
        {true,
            [this](unsigned bank,const MacroWrite& c){
                // Actual bank rising completed BEFORE acceptance notification.
                assert(vm.clk&&vm.rst_n);assert(c.word.address%4==bank);
                assert(c.word.owner==fixture_record(batch(c.source.element_address&~15u),c.source.element_address&15).word.owner);
                writes_seen++;banks.push_back(bank);
                if(throw_observer)throw std::runtime_error("source ledger refused");
            },
            [this](uint32_t a,const auto& owner){
                assert(vm.clk&&vm.rst_n&&vm.rd_accept_v);assert(a==46464);
                for(unsigned i=0;i<8;i++)assert(owner[i]==vm.rd_owner[i]);
                reads_seen++;if(throw_read)throw std::runtime_error("read ledger refused");
            }}};
    DsromS81MinimumParticipant p=binder.participant();
    AcceptRun(){tick(false);}
    void tick(bool released=true){p.prepare({});p.rising(released);p.falling(released);}
};
int main() {
    {AcceptRun r;
     const unsigned offsets[]={0,5120,10240,15360,16};
     for(unsigned i=0;i<5;i++) {
         auto o=batch(64+offsets[i]);assert(r.binder.offer(o));
         assert(!r.binder.source_span_lease(123,o.vm_address,16));
         for(unsigned edge=0;edge<19;edge++)r.tick();
         assert(r.binder.visible(o));
         assert(r.binder.source_span_lease(123,o.vm_address,16));
         assert(r.binder.published_words()==16*(i+1));
         if(i<4)assert(!r.binder.source_span_lease(123,80,16));
     }
     assert(!r.binder.source_span_lease(123,96,16));
    }
    {AcceptRun r;assert(!r.writes_seen&&!r.reads_seen);
     r.tick();assert(!r.writes_seen&&!r.reads_seen); // idle strobe=0
     auto o=batch(46464);assert(r.binder.offer_prefix(o,16));
     assert(!r.writes_seen); // construction/offer NEVER advances accepted ledger
     for(unsigned i=0;i<16;i++){r.tick();assert(r.writes_seen==i+1);}
     assert(r.acks_seen==13); // accepts are not inferred from later ACKs
     for(unsigned i=0;i<3;i++){r.tick();assert(r.writes_seen==16);}
     assert(r.acks_seen==16&&r.binder.visible_prefix(o,16));
     auto tag=fixture_record(o,0).word.owner;assert(!r.binder.target_word(46464,tag));
     assert(!r.reads_seen);r.tick();assert(r.reads_seen==1);
     for(unsigned i=0;i<4;i++){r.tick();assert(r.reads_seen==1&&r.writes_seen==16);}
     assert(r.binder.target_word(46464,tag)); // completion is NOT another acceptance
    }
    {AcceptRun r;auto o=batch(46527); // word2907 bank3 thenword2908 bank0
     r.binder.offer_prefix(o,2);r.tick();
     assert((r.banks==std::vector<unsigned>{0,3})); // actualbankpriority not laneorder
    }
    {AcceptRun r;r.binder.offer_prefix(batch(46464),1);r.p.prepare({});
     r.vm.wr_owner[0]^=1;refuses([&]{r.p.rising(true);});
     assert(r.writes_seen==0&&r.binder.fault()); // changed current pins not accepted ownerproof
    }
    {AcceptRun r;r.binder.offer_prefix(batch(46464),1);r.vm.wr_fault=true;
     refuses([&]{r.tick();});assert(r.writes_seen==0&&r.binder.fault());}
    {AcceptRun r;r.throw_observer=true;r.binder.offer_prefix(batch(46464),1);
     refuses([&]{r.tick();});assert(r.writes_seen==1&&r.binder.accepted_words()==1&&r.binder.fault());}
    {AcceptRun r;r.binder.offer_prefix(batch(46464),1);r.tick();
     refuses([&]{r.tick(false);});assert(r.writes_seen==1&&r.reads_seen==0&&r.binder.fault());}
    {AcceptRun r;auto o=batch(46464);r.binder.offer_prefix(o,1);
     for(unsigned i=0;i<4;i++){r.tick();}r.binder.visible_prefix(o,1);
     r.throw_read=true;assert(!r.binder.target_word(46464,fixture_record(o,0).word.owner));
     refuses([&]{r.tick();});assert(r.reads_seen==1&&r.binder.fault());}
    {TargetModel vm;
     auto construct=[&](ActualVmAcceptObservers hooks){
        PublishedSpanAcceptSink<TargetModel> b(vm,123,64,fixture_record,
            [](uint64_t,uint32_t,unsigned){return false;},
            [](uint64_t,uint32_t,unsigned){return false;},
            [](const MacroWrite&,const VmReceipt&){},hooks);
     };
     construct({}); // old API default-off observers remain compatible
     refuses([&]{construct({true,{},{}});});
     refuses([&]{construct({true,[](unsigned,const MacroWrite&){},{}});});
     refuses([&]{construct({true,{},[](uint32_t,const auto&){}});});
    }
    std::cout<<"PASS actual accept observers: preedge retained write/read tuple, successfulsharededge, bankorder, no offer/ACK/idle/reset callback, fault quarantine, selectedmissingrefusal\n";
}
'''
class TestActualAccept(unittest.TestCase):
    def test_source_ledger_notifications(self):
        with tempfile.TemporaryDirectory(prefix="s81-actual-accept-") as d:
            source=pathlib.Path(d)/"check.cpp";binary=pathlib.Path(d)/"check"
            source.write_text(CPP)
            subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror",
                "-I",str(ROOT/"tools/runtime/dsrom"),"-I",str(ROOT/"rtl/test/v41_runtime"),
                str(source),"-o",str(binary)],check=True)
            result=subprocess.run([str(binary)],check=True,capture_output=True,text=True)
            self.assertIn("PASS actual accept observers:",result.stdout)
if __name__=="__main__":unittest.main()
