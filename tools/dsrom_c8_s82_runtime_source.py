#!/usr/bin/env python3
"""Source-select native C8 callbacks and S82 word/return wiring into W17 host.

Original host unchanged. DSROM_C8_S82 defaults off. Erdos can include this
runtime with DSROM_C8_LIBRARY=1 and supply the real two-position scheduler.
"""
import argparse
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN='f6df84e14c2bc5908bdbf85b2bd95cd56b1f5520'
SOURCE='rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp'


def transform(source):
    def replace(old,new):
        nonlocal source
        if source.count(old)!=1:raise ValueError('retained host anchor changed: '+old[:60])
        source=source.replace(old,new)
    replace('#include <sys/resource.h>', '''#include <sys/resource.h>
#ifndef DSROM_C8_S82
#define DSROM_C8_S82 0
#endif
#if DSROM_C8_S82
#include "dsrom_s82_rom_client.hpp"
#endif''')
    replace('struct PairMem {', 'struct PairMem { int source_stage=-1, source_rank=-1, source_pair=-1;')
    replace('    const auto& v = it->second.first->rom[bank];', '''#if DSROM_C8_S82
    auto* native=it->second.first;
    auto word=dsrom_s82::read(native->source_stage,native->source_rank,native->source_pair,bank,addr);
    for(int k=0;k<9;k++)q[k]=word[k];
    return;
#endif
    const auto& v = it->second.first->rom[bank];''')
    replace('    const auto& c = it->second->cfg;', '''    const auto& c = it->second->cfg;
#if DSROM_C8_S82
    if(addr<0 || size_t(addr)>=c.size())throw std::runtime_error("unbound actual S82 cfg phase/address");
#endif''')
    replace('    for (int mb = 0; mb < 2; mb++) {', '''#if !DSROM_C8_S82
    for (int mb = 0; mb < 2; mb++) {''')
    replace('    std::ifstream f(dir + "/e" + std::to_string(p) + ".cfg.hex");', '''#endif
    std::ifstream f(dir + "/e" + std::to_string(p) + ".cfg.hex");
#if DSROM_C8_S82
    if(!f)throw std::runtime_error("actual source-bound configuration is required; no zero cfg fallback");
#endif''')
    replace('    std::vector<int> act;', '    std::vector<int> return_owner;\n    std::vector<int> act;')
    replace('        NL = 2 * meta.np;', '''#if DSROM_C8_S82
        if(meta.np!=2388 || meta.r!=128 || meta.active.size()!=2388 || meta.bf.size()!=512)
            throw std::runtime_error("selected canonical S82 field inventory required");
        const char* stage_env=getenv("DSROM_S82_STAGE");
        if(!stage_env)throw std::runtime_error("actual S82 stage owner is required");
        int source_stage=std::stoi(stage_env);
        if(source_stage<0 || source_stage>=82)throw std::runtime_error("S82 stage bounds");
        std::vector<bool> seen(2388,false);
        for(int pair:meta.active){if(pair<0 || pair>=2388 || seen[pair])throw std::runtime_error("duplicate/missing physical element");seen[pair]=true;}
        std::vector<bool> seen_bf(2388,false);
        for(int pair:meta.bf){if(pair<0 || pair>=2388 || seen_bf[pair])throw std::runtime_error("invalid BF element owner");seen_bf[pair]=true;}
        return_owner.assign(4096,-1);
        for(int pair=0;pair<2388;pair++)return_owner[dsrom_s82::return_pair(pair)]=pair;
        NL=8192;
#else
        NL = 2 * meta.np;
#endif
        ''')
    replace('        for (int s : meta.active) load_pair(mem[s], dir, s);', '''        for (int s : meta.active) {
#if DSROM_C8_S82
            mem[s].source_stage=source_stage;mem[s].source_rank=die_id;mem[s].source_pair=s;
#endif
            load_pair(mem[s], dir, s);
        }''')
    replace('        if (l == 0) return leaf(g >> 1, g & 1);', '''        if (l == 0) {
#if DSROM_C8_S82
            int pair=return_owner.at(g>>1);
            return pair<0 ? Node{} : leaf(pair,g&1);
#else
            return leaf(g >> 1, g & 1);
#endif
        }''')
    # Template calls use real generated top pins. No model receipt or external
    # retirement tuple substitutes for the native callback.
    replace('    virtual uint32_t vm_word(int a) = 0;', '''    virtual uint32_t vm_word(int a) = 0;
#if DSROM_C8_S82
    virtual bool c8_ready()=0;
    virtual void c8_offer(uint8_t,uint32_t,uint32_t,uint32_t,uint16_t,uint16_t)=0;
    virtual void c8_restored(bool)=0;
    virtual bool c8_context(uint64_t&,uint32_t&,uint16_t&)=0;
    virtual bool c8_retired(uint64_t&)=0;
    virtual void c8_observe(long)=0;
#endif''')
    replace('    uint32_t vm_word(int adr) override {', '''#if DSROM_C8_S82
    bool c8_ready() override {return d->c8_offer_ready;}
    void c8_offer(uint8_t valid,uint32_t tok,uint32_t pos,uint32_t user,uint16_t epoch,uint16_t entry) override {
        if(tok>=(1u<<21)||pos>=(1u<<21)||user>=(1u<<10)||entry>=(1u<<14))throw std::runtime_error("C8 offered descriptor bounds");
        d->start=valid;d->token=tok;d->pos=pos;d->user=user;d->c8_entry=entry;
        d->c8_position_identity=(uint64_t(epoch)<<31)|(uint64_t(user)<<21)|pos;
    }
    void c8_restored(bool visible) override {d->c8_context_restored=visible;}
    bool c8_context(uint64_t& identity,uint32_t& token,uint16_t& entry) override {
        identity=d->c8_context_identity;token=d->c8_context_token;entry=d->c8_context_entry;return d->c8_context_v;
    }
    bool c8_retired(uint64_t& identity) override {identity=d->c8_retire_identity;return d->c8_retire_v;}
    long c8_observed_cycle=-1;
    void c8_observe(long cycle) override {
        if(c8_observed_cycle==cycle)return;c8_observed_cycle=cycle;
        for(int port=0;port<128;port++)if(getb(d->c8_visible_v,port,1))
            printf("C8_NATIVE_VISIBLE rank=%d cycle=%ld port=%d identity=%llu addr=%llu writer=%llu\\n",id,cycle,port,
                (unsigned long long)getb(d->c8_visible_identity,47*port,47),
                (unsigned long long)getb(d->c8_visible_addr,30*port,30),
                (unsigned long long)getb(d->c8_visible_writer,2*port,2));
        if(d->c8_own_visible_v)printf("C8_OWN_VISIBLE rank=%d cycle=%ld identity=%llu gid=%u\\n",id,cycle,(unsigned long long)d->c8_own_visible_identity,d->c8_own_visible_gid);
        if(d->c8_retire_v)printf("C8_STAGE_RETIRED rank=%d cycle=%ld identity=%llu\\n",id,cycle,(unsigned long long)d->c8_retire_identity);
        if(d->c8_write_fault||d->c8_write_quarantine||d->c8_stage_quarantine)
            throw std::runtime_error("C8 accepted work fault/quarantine; no unchecked retirement");
    }
#endif
    uint32_t vm_word(int adr) override {''')
    replace('int main(int argc, char** argv) {', '''#ifndef DSROM_C8_LIBRARY
int main(int argc, char** argv) {
#if DSROM_C8_S82
    throw std::runtime_error("use the actual C8 caller scheduler; legacy singleton driver is not a combined run");
#endif''')
    return source+'\n#endif // DSROM_C8_LIBRARY\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise FileExistsError(a.out)
    source=subprocess.check_output(['git','show',PIN+':'+SOURCE],cwd=ROOT,text=True)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(transform(source))

if __name__=='__main__':main()
