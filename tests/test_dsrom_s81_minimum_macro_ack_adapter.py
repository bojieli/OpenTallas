"""Native port-adapter tests only; this is not RTL or full-root qualification."""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CPP = r'''
#include "s81_minimum_macro_ack_adapter.hpp"
#include <cassert>
#include <iostream>
using namespace dsrom_s81_minimum;
// Port double implements only the source E+3 ACK contract. No memory arithmetic.
struct Ports {
    bool clk=0,rst_n=0,oldclk=0,rd_v=0;
    uint16_t rd_base_word=0;
    unsigned wr_v=0,wr_accept_v=0,wr_ack_v=0;
    bool wr_fault=0,rw_collision_fault=0,rd_fault=0;
    uint64_t wr_word_addr=0,wr_lane_mask=0,wr_ack_word_addr=0,wr_ack_lane_mask=0;
    std::array<uint32_t,64> wr_word_data{};
    std::array<uint32_t,29> wr_owner{},wr_ack_owner{};
    std::array<uint32_t,8> rd_owner{};
    struct Saved {unsigned valid=0;uint64_t addr=0,mask=0;std::array<uint32_t,29> owner{};};
    std::array<Saved,3> pipe{};
    int corrupt=0;
    void eval() {
        wr_accept_v=rst_n?wr_v:0;
        if(clk&&!oldclk) {
            if(!rst_n){pipe={};wr_ack_v=0;}
            else {
                auto p=pipe[2];wr_ack_v=p.valid;wr_ack_owner=p.owner;
                wr_ack_word_addr=p.addr;wr_ack_lane_mask=p.mask;
                pipe[2]=pipe[1];pipe[1]=pipe[0];
                pipe[0]={wr_accept_v,wr_word_addr,wr_lane_mask,wr_owner};
                if(wr_ack_v&&corrupt==1)wr_ack_owner[0]^=1;
                if(wr_ack_v&&corrupt==2)wr_ack_word_addr^=4;
                if(wr_ack_v&&corrupt==3)wr_ack_lane_mask^=2;
                if(corrupt==4){wr_ack_v=wr_accept_v;wr_ack_owner=wr_owner;wr_ack_word_addr=wr_word_addr;wr_ack_lane_mask=wr_lane_mask;}
            }
        }
        oldclk=clk;
    }
};
MacroWrite command(unsigned bank,unsigned variant=0) {
    MacroWrite c;
    c.word.address=bank+variant*4;c.word.mask=uint16_t(1)<<7;
    for(unsigned i=0;i<8;i++)c.word.owner[i]=0xfadebc91u+i+variant;
    c.word.owner[7]=7; // all three high TAG227 bits exercised
    c.word.data[7]=0x80000000u+variant; // raw negative zero is not converted
    c.source={123+variant,17,33,2,4,uint32_t(c.word.address*16+7)};
    return c;
}
struct Run {
    Ports ports;
    MacroAckAdapter<Ports>::Commands commands{};
    std::vector<MacroWrite> accepted,visible;
    bool throw_visible=false,throw_accept=false;
    MacroAckAdapter<Ports> adapter;
    DsromS81MinimumParticipant p;
    Run():adapter(ports,[this](auto const&){return commands;},
       [this](unsigned b,auto const& c){if(throw_accept)throw std::runtime_error("capture receipt refused");accepted.push_back(c);commands[b].reset();},
       [this](unsigned,auto const& c,auto const& r){
           assert(c.word.owner==r.owner&&c.word.address==r.address&&c.word.mask==r.mask);
           if(throw_visible)throw std::runtime_error("consumer refused receipt");
           visible.push_back(c);
       }),p(adapter.participant()) {tick(false);}
    void tick(bool reset=true){p.prepare({});p.rising(reset);p.falling(reset);}
};
template<class F> void refuses(F f){bool refused=false;try{f();}catch(std::runtime_error const&){refused=true;}assert(refused);}
int main() {
    {Run r;auto c=command(0);r.commands[0]=c;r.tick();
     assert(r.accepted.size()==1&&r.visible.empty()&&r.adapter.outstanding()==1);
     assert(r.accepted[0].word.data[7]==0x80000000u);
     // Current pins carry a different command: ACK must retain the OLD tuple.
     r.commands[0]=command(0,1);r.tick();r.tick();assert(r.visible.empty());
     r.tick();assert(r.visible.size()==1&&r.visible[0].word.owner==c.word.owner);
     assert(r.adapter.outstanding()==1);r.tick();assert(r.visible.size()==2&&r.adapter.drained());}
    {Run r;for(unsigned b=0;b<4;b++)r.commands[b]=command(b,b);
     r.tick();assert(r.adapter.outstanding()==4);r.tick();r.tick();r.tick();
     assert(r.visible.size()==4&&r.adapter.drained());
     assert(r.ports.wr_word_data[7]==0); // no arithmetic callback / stale command replay
    }
    for(int corrupt=1;corrupt<=3;corrupt++) {
        Run r;r.commands[0]=command(0);r.tick();r.tick();r.tick();r.ports.corrupt=corrupt;
        refuses([&]{r.tick();});assert(r.adapter.fault()&&r.adapter.outstanding()==1&&r.visible.empty());
    }
    {Run r;r.commands[0]=command(0);r.tick();r.tick(false);
     assert(r.adapter.fault()&&r.adapter.outstanding()==1);refuses([&]{r.tick();});}
    {Run r;r.commands[0]=command(0);r.tick();r.tick();r.tick();r.throw_visible=true;
     refuses([&]{r.tick();});assert(r.adapter.fault()&&r.adapter.outstanding()==1&&!r.adapter.drained());}
    {Run r;r.commands[0]=command(0);r.commands[0]->word.mask=2;
     refuses([&]{r.tick();});assert(r.accepted.empty()&&r.adapter.fault());}
    {Run r;r.commands[0]=command(0);r.ports.wr_fault=true;
     refuses([&]{r.tick();});assert(r.adapter.fault()&&r.accepted.empty());}
    {Run r;r.commands[0]=command(0);r.tick();r.tick();r.tick();r.tick();
     // Forged duplicate old ACK without another accepted command cannot release.
     r.ports.pipe[2].valid=1;
     refuses([&]{r.tick();});assert(r.adapter.fault()&&r.visible.size()==1);}
    {Run r;r.commands[0]=command(0);r.ports.corrupt=4;
     refuses([&]{r.tick();});assert(r.adapter.fault()&&r.adapter.outstanding()==1&&r.visible.empty());}
    {Run r;r.commands[0]=command(0);r.commands[1]=command(1);r.throw_accept=true;
     refuses([&]{r.tick();});assert(r.adapter.fault()&&r.adapter.outstanding()==2);}
    std::cout<<"PASS adapter: acceptance debt, E+3 oldtuple, 4bank TAG227, wrongowner/address/mask, reset, callback, mask, fault, duplicate\n";
}
'''


class TestMinimumMacroAckAdapter(unittest.TestCase):
    def test_actual_packed_ports_and_debt(self):
        with tempfile.TemporaryDirectory(prefix="s81-ack-adapter-") as tmp:
            source = pathlib.Path(tmp) / "check.cpp"
            binary = pathlib.Path(tmp) / "check"
            source.write_text(CPP)
            subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                            "-I", str(ROOT / "tools/runtime/dsrom"),
                            "-I", str(ROOT / "rtl/test/v41_runtime"),
                            str(source), "-o", str(binary)], check=True, text=True)
            result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
            self.assertIn("PASS adapter:", result.stdout)


if __name__ == "__main__":
    unittest.main()
