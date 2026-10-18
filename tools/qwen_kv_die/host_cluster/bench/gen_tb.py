#!/usr/bin/env python3
"""KVJ-A3 composition bench generator: cycle-by-cycle LOCK-STEP of the generated cluster qkd_hr_cluster against the flat
root qkd_host_root_admission (ENABLE_SERVICE/NATIVE/TOKEN=1, NL=2), both verilated, one C++ harness.

Clocks follow tools/qwen_native_host/host_owner.hpp: CORE half 416667 fs, HOST 500000, INGEST 833334, PHY 521500 (first
rising edges 553667 / 637002 / 1110336 / 892504 fs).  The flat root's 45 clock ports are driven from the four family
levels exactly as the cluster's D3 face is (kv_die.HOST_CLK_FAMILY + HOST_CLK_INFERRED); ck_phy[7:0] = the phy family.
Inputs change identically for both models after every CORE falling edge; every output of both models is compared after
every evaluation.  Modes: 0 random (p(valid)=0.3), 1 quiet (rare events); por_n low for the first 24 core cycles and,
in mode 0, a second reset pulse mid-run.

usage: gen_tb.py p1.json OUT.cpp
"""
import json
import sys
from pathlib import Path

# kv_die.HOST_CLK_FAMILY + HOST_CLK_INFERRED, frozen next to the bench (regenerate when kv_die changes) so the loop
# bench needs no kv_die import chain
FAMILY = json.load(open(Path(__file__).resolve().parent / 'clock_family.json'))


def family():
    return FAMILY

FIDX = dict(core=0, host=1, ingest=2, phy=3)


def main():
    J = json.load(open(sys.argv[1]))['modules']
    topm = [m for m in J if J[m].get('attributes', {}).get('top')][0]
    ports = J[topm]['ports']
    fam = family()
    clk, ins, outs = [], [], []
    for p, d in ports.items():
        w = len(d['bits'])
        if p == 'ck_phy' or p == 'ck_qm_bank' or p in fam:
            clk.append((p, w))
        elif d['direction'] == 'input':
            ins.append((p, w))
        else:
            outs.append((p, w))
    L = []
    a = L.append
    a('#include "Vflat.h"\n#include "Vclu.h"\n#include "verilated.h"\n#include <cstdio>\n#include <cstdlib>\n#include <cstdint>\n#include <random>')
    a('static std::mt19937_64 R;')
    a('template<class T> static void rnd(T& v,int w,double p1){ if(w==1){v=(R()%1000)<p1*1000;return;}'
      ' if(w<=64){uint64_t x=R(); if(w<64)x&=((1ull<<w)-1); v=x; return;} }')
    a('template<std::size_t N> static void rndw(VlWide<N>& v,int w){for(int i=0;i<(int)N;i++){uint32_t x=R(); int hi=w-32*i; if(hi<32)x&=(hi<=0?0:((1u<<hi)-1)); v[i]=x;}}')
    a('static bool eqw(const uint32_t* a,const uint32_t* b,int n){for(int i=0;i<n;i++)if(a[i]!=b[i])return false;return true;}')
    a('int main(int argc,char**argv){ Verilated::commandArgs(argc,argv);')
    a(' unsigned long seed=argc>1?strtoul(argv[1],0,0):1; int mode=argc>2?atoi(argv[2]):0; long ncore=argc>3?atol(argv[3]):20000;')
    a(' R.seed(seed); VerilatedContext c1,c2; Vflat* F=new Vflat(&c1); Vclu* C=new Vclu(&c2);')
    a(' const uint64_t half[4]={416667,500000,833334,521500}; uint64_t next[4]={553667,637002,1110336,892504}; bool lv[4]={0,0,0,0};')
    a(' long cores=0; uint8_t die=R()%8; uint64_t now=0; long cmp=0;')
    a(' auto clocks=[&](){')
    for p, w in clk:
        if p == 'ck_phy':
            a(f'  F->ck_phy=lv[3]?0xff:0;')
        elif p == 'ck_qm_bank':
            a(f'  F->ck_qm_bank=lv[2]?3:0;')
        else:
            a(f'  F->{p}=lv[{FIDX[fam[p]]}];')
    a('  C->ck_core=lv[0];C->ck_host=lv[1];C->ck_ingest=lv[2];C->ck_phy_fam=lv[3];C->ck_phy=lv[3]?0xff:0; };')
    a(' auto drive=[&](){ double pv=mode==0?0.3:0.01;')
    for p, w in ins:
        if p == 'por_n':
            a(f'  F->por_n=C->por_n=!(cores<24||(mode==0&&cores>ncore/2&&cores<ncore/2+8));')
        elif p == 'pll_locked':
            a('  F->pll_locked=C->pll_locked=1;')
        elif p == 'die_id':
            a('  F->die_id=C->die_id=die;')
        elif w > 64:
            a(f'  rndw(F->{p},{w}); for(int i=0;i<{(w + 31) // 32};i++)C->{p}[i]=F->{p}[i];')
        else:
            a(f'  {{uint64_t t; rnd(t,{w},pv); F->{p}=t; C->{p}=t;}}')
    a(' };')
    a(' auto compare=[&]()->bool{ cmp++;')
    for p, w in outs:
        if w > 64:
            a(f'  if(!eqw(F->{p}.data(),C->{p}.data(),{(w + 31) // 32})){{printf("MISMATCH %s t=%llu fs core=%ld\\n","{p}",(unsigned long long)now,cores);return false;}}')
        else:
            a(f'  if(F->{p}!=C->{p}){{printf("MISMATCH %s t=%llu fs core=%ld flat=%llx clu=%llx\\n","{p}",(unsigned long long)now,cores,(unsigned long long)F->{p},(unsigned long long)C->{p});return false;}}')
    a('  return true; };')
    a(' drive(); clocks(); F->eval(); C->eval(); if(!compare())return 1;')
    a(' while(cores<ncore){ int k=0; for(int i=1;i<4;i++) if(next[i]<next[k]) k=i; now=next[k];')
    a('  lv[k]=!lv[k]; next[k]+=half[k];')
    a('  clocks(); F->eval(); C->eval(); if(!compare())return 1;')
    a('  if(k==0&&!lv[0]){ cores++; if(getenv("DBG"))printf("c%ld sf %x %x dr %x %x\\n",cores,(unsigned)F->service_faults,(unsigned)C->service_faults,(unsigned)F->service_diag_raw,(unsigned)C->service_diag_raw); drive(); F->eval(); C->eval(); if(!compare())return 1; } }')
    a(f' printf("LOCKSTEP PASS seed=%lu mode=%d core_cycles=%ld compares=%ld outputs={len(outs)} inputs={len(ins)}\\n",seed,mode,cores,cmp);')
    a(' F->final(); C->final(); delete F; delete C; return 0; }')
    Path(sys.argv[2]).write_text('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
