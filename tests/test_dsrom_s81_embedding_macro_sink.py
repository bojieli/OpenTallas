"""New sink-binding checks; reuse the native VM archive when explicitly selected."""
import os
import pathlib
import subprocess
import tempfile
import unittest

from test_dsrom_s81_minimum_macro_ack_adapter import CPP as ACK_CPP

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Existing port double is reused only by adapter unit tests, never production.
PORTS = ACK_CPP.split('int main() {')[0]
CPP = PORTS + r'''
#include "s81_embedding_macro_sink.hpp"
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
struct SinkRun {
#ifdef S81_REAL_NATIVE_VM
    VerilatedContext context;
    TargetModel vm{&context};
#else
    TargetModel vm;
#endif
    EmbeddingMacroSink<TargetModel> binder{vm,123,64,fixture_record};
    DsromS81MinimumParticipant p=binder.participant();
    SinkRun(){tick(false);}
    void tick(bool released=true){p.prepare({});p.rising(released);p.falling(released);}
};
int main() {
    {SinkRun r;auto o=batch();assert(r.binder.offer(o));
     assert(!r.binder.visible(o));
     for(unsigned i=0;i<18;i++) {r.tick();if(i<18-1)assert(!r.binder.visible(o));}
     assert(!r.binder.visible(o)); // final command E16, final ACK E19
     r.tick();assert(r.binder.visible(o)&&r.binder.published_words()==16);
     // Accessor returns the TARGET VM response, with exact native read tags.
     for(unsigned n=0;n<16;n++) {
         auto owner=fixture_record(o,n).word.owner;
         assert(!r.binder.target_word(o.vm_address+n,owner));
         for(unsigned i=0;i<4;i++){r.tick();assert(!r.binder.target_word(o.vm_address+n,owner));}
         r.tick();auto value=r.binder.target_word(o.vm_address+n,owner);
         assert(value&&*value==o.vm_data[n]);
     }
     refuses([&]{r.binder.target_word(80,{});});assert(r.binder.fault());
    }
#ifndef S81_REAL_NATIVE_VM
    {SinkRun r;auto o=batch();r.binder.offer(o);r.tick();assert(!r.binder.visible(o));
     r.vm.corrupt=1;r.tick();r.tick();refuses([&]{r.tick();});assert(r.binder.fault()&&r.binder.published_words()==0);}
    {SinkRun r;auto o=batch();r.binder.offer(o);r.tick();refuses([&]{r.tick(false);});assert(r.binder.fault());}
    {SinkRun r;auto o=batch();r.binder.offer(o);o.vm_data[9]^=1;
     refuses([&]{r.binder.offer(o);});assert(r.binder.fault());}
    {SinkRun r;auto o=batch();r.binder.offer(o);for(unsigned i=0;i<19;i++){r.tick();}r.binder.visible(o);
     o=batch(80);assert(r.binder.offer(o));assert(!r.binder.visible(o));
     for(unsigned i=0;i<19;i++){r.tick();}assert(r.binder.visible(o)&&r.binder.published_words()==32);}
    {SinkRun r;auto o=batch();r.binder.offer(o);for(unsigned i=0;i<19;i++){r.tick();}r.binder.visible(o);
     auto tag=fixture_record(o,0).word.owner;assert(!r.binder.target_word(64,tag));
     for(unsigned i=0;i<4;i++){r.tick();}r.vm.reads[3].owner[0]^=1;
     refuses([&]{r.tick();});assert(r.binder.fault());}
#endif
    std::cout<<"PASS sink: 16 exact scalar ACKs, held payload, TARGET native read rawbits, publication bounds\n";
}
'''


class TestEmbeddingMacroSink(unittest.TestCase):
    def test_sixteen_matched_receipts_and_target_accessor(self):
        with tempfile.TemporaryDirectory(prefix="s81-embedding-sink-") as tmp:
            source = pathlib.Path(tmp) / "check.cpp"
            binary = pathlib.Path(tmp) / "check"
            source.write_text(CPP)
            command = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                       "-I", str(ROOT / "tools/runtime/dsrom"),
                       "-I", str(ROOT / "rtl/test/v41_runtime"), str(source)]
            archive = os.environ.get("DSROM_S81_NATIVE_VM_DIR")
            if archive:
                directory = pathlib.Path(archive)
                verilator = pathlib.Path(os.environ["DSROM_S81_VERILATOR_ROOT"])
                command += ["-DS81_REAL_NATIVE_VM", "-I", str(directory),
                            "-isystem", str(verilator / "include"),
                            "-isystem", str(verilator / "include/vltstd"),
                            str(directory / "Vnative_vm__ALL.a"),
                            str(directory / "verilated.o"), str(directory / "verilated_threads.o"),
                            "-pthread"]
            command += ["-o", str(binary)]
            subprocess.run(command, check=True)
            result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
            self.assertIn("PASS sink:", result.stdout)


if __name__ == "__main__":
    unittest.main()
