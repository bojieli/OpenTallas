#include "Vot_qwen_tp8_pv256_ordered.h"
#include "verilated.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

static std::vector<uint32_t> read(const std::string& p, size_t n) {
    std::vector<uint32_t> a(n); std::ifstream f(p, std::ios::binary);
    if (!f.read(reinterpret_cast<char*>(a.data()), n*4)) throw std::runtime_error("missing vector " + p);
    return a;
}
int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    if(argc!=4) return 2;
    std::string dir=argv[1], mode=argv[2];
    auto prod=read(dir+"/products.bin",4*8192*128);
    auto gold=read(dir+"/leaves.bin",4*256*128);
    std::vector<uint32_t> actual(gold.size());
    Vot_qwen_tp8_pv256_ordered d;
    uint64_t cycles=0, products=0, mismatches=0;
    auto tick=[&]() { d.clk=0; d.eval(); d.clk=1; d.eval(); ++cycles; };
    d.rst_n=0; d.start=0; d.lo_valid=0; d.hi_valid=0; d.out_ready=0; tick(); tick(); d.rst_n=1; tick();
    for(unsigned h=0;h<4;h++) for(unsigned c=0;c<256;c++) for(unsigned b=0;b<8;b++) {
        d.start=1; d.context_len=8192; d.residue=c; d.epoch=37;
        d.head=h; d.block_id=b; tick(); d.start=0;
        uint64_t begun=cycles;
        while(!d.out_valid && !d.fault) {
            unsigned t=d.expected_t;
            bool valid=(cycles%7!=2 && cycles%11!=3);
            d.lo_valid=valid; d.hi_valid=valid;
            d.lo_t=t; d.hi_t=t; d.lo_epoch=37; d.hi_epoch=37;
            d.lo_head=h; d.hi_head=h; d.lo_block=b; d.hi_block=b;
            bool mutate=(h==0 && c==0 && b==0 && t==256);
            if(mutate && mode=="order") { d.lo_t=t^256; d.hi_t=t^256; }
            if(mutate && mode=="epoch") { d.lo_epoch=36; d.hi_epoch=36; }
            if(mutate && mode=="tag") { d.lo_head=1; d.hi_head=1; }
            for(unsigned l=0;l<16;l++) {
                auto word=prod[(h*8192+t)*128+b*16+l];
                if(mutate && mode=="data") word^=0x80000000;
                d.lo_product[l]=word; d.hi_product[l]=word;
            }
            d.clk=0; d.eval();
            if(valid && (d.lo_ready || d.hi_ready)) ++products;
            tick();
            if(cycles-begun>2000) { std::cerr<<"TIMEOUT\n"; return 2; }
        }
        if(d.fault) {
            std::cout<<"{\"observed_fault\":true,\"cycles\":"<<cycles<<",\"mutant\":\""<<mode<<"\"}\n";
            return (mode=="order" || mode=="epoch" || mode=="tag")?0:1;
        }
        d.lo_valid=0; d.hi_valid=0;
        auto saved=d.out_partial;
        for(unsigned stall=0;stall<3;stall++) {
            tick();
            if(!d.out_valid) return 2;
            for(unsigned l=0;l<16;l++) if(d.out_partial[l]!=saved[l]) return 2;
        }
        if(d.out_epoch!=37 || d.out_head!=h || d.out_block!=b || d.out_residue!=c) return 2;
        for(unsigned l=0;l<16;l++) {
            size_t i=(h*256+c)*128+b*16+l;
            actual[i]=d.out_partial[l]; mismatches+=(actual[i]!=gold[i]);
        }
        d.out_ready=1; tick(); d.out_ready=0;
    }
    std::ofstream out(argv[3], std::ios::binary); out.write(reinterpret_cast<char*>(actual.data()),actual.size()*4);
    std::cout<<"{\"mismatches\":"<<mismatches<<",\"leaf_words\":"<<actual.size()<<",\"products\":"<<products<<",\"cycles\":"<<cycles<<",\"mutant\":\""<<mode<<"\"}\n";
    if(mode=="data") return mismatches?0:1;
    return mismatches || mode!="none";
}
