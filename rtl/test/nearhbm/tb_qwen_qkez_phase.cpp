// Verilator harness: near-HBM attention exact gate (4 stacks + hub) against the golden (tools/hdc_golden.py via
// tools/qwen_nearhbm_attn_ref.py vectors).  Models each stack's HBM: per-engine in-order request queues, a token
// bucket of BPC bytes per 1.2 GHz cycle per stack (750 = 0.9 TB/s), one row per engine per cycle, fixed latency.
//   ./Vtb <vector dir> [hbm_latency=16] [bytes_per_cycle=750] [max_cycles=400000]
#include "Vot_qwen_qkez_phase_tb.h"
#include "verilated.h"
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <fstream>
#include <string>
#include <vector>

#ifndef NHB_R
#define NHB_R 1
#endif
#ifndef NHB_HD
#define NHB_HD 128
#endif
#ifndef NHB_HEADS
#define NHB_HEADS 2
#endif
#ifndef NHB_Q_FP32
#define NHB_Q_FP32 0
#endif
#ifndef NHB_PV_SPLIT
#define NHB_PV_SPLIT 512
#endif
static const int R = NHB_R, HD = NHB_HD, KVH = NHB_HEADS, NH = 4 * KVH;
static const int QW = NHB_Q_FP32 ? 32 : 16, QLANES = 512 / QW;
static_assert(KVH == 1 || KVH == 2, "supported KV-head profiles");

template <typename T> static uint64_t gbits(const T& v, int off, int w) { return (uint64_t(v) >> off) & ((w == 64) ? ~0ull : ((1ull << w) - 1)); }
static uint64_t gbits(const uint32_t* v, int off, int w) {
    uint64_t r = 0;
    for (int i = 0; i < w; i++) if ((v[(off + i) / 32] >> ((off + i) % 32)) & 1) r |= 1ull << i;
    return r;
}
static void sbit_words(uint32_t* v, int off, int w, uint64_t x) {
    for (int i = 0; i < w; i++) {
        int b = off + i;
        if ((x >> i) & 1) v[b / 32] |= 1u << (b % 32); else v[b / 32] &= ~(1u << (b % 32));
    }
}
template <typename T> static void sbits(T& v, int off, int w, uint64_t x) {
    uint64_t m = ((w == 64) ? ~0ull : ((1ull << w) - 1)) << off;
    v = (T)((uint64_t(v) & ~m) | ((x << off) & m));
}
static void sbits(uint32_t* v, int off, int w, uint64_t x) { sbit_words(v, off, w, x); }
template <std::size_t N> static uint64_t gbits(const VlWide<N>& v, int off, int w) { return gbits(v.data(), off, w); }
template <std::size_t N> static void sbits(VlWide<N>& v, int off, int w, uint64_t x) { sbit_words(v.data(), off, w, x); }

struct Req { int v, g, t; };
struct Rsp { uint64_t at; int v, g, t; };

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    if (argc < 2) { fprintf(stderr, "usage: Vtb DIR [lat] [bpc] [maxcyc]\n"); return 2; }
    std::string dir = argv[1];
    int LAT = argc > 2 ? atoi(argv[2]) : 16;
    int BPC = argc > 3 ? atoi(argv[3]) : 750;
    int STALL = argc > 5 ? atoi(argv[5]) : 0;
    std::string MUT = argc > 6 ? argv[6] : "none";
    if (LAT < 0 || BPC <= 0 || STALL < 0) return 2;
    uint64_t MAXC = argc > 4 ? strtoull(argv[4], 0, 10) : 400000;
    // vectors
    int T = 0;
    {
        std::ifstream m(dir + "/meta.json");
        std::string s((std::istreambuf_iterator<char>(m)), std::istreambuf_iterator<char>());
        size_t p = s.find("\"ctx\":");
        T = atoi(s.c_str() + p + 6);
    }
    std::vector<uint32_t> q;
    { std::ifstream f(dir + "/q.hex"); std::string l; while (f >> l) q.push_back((uint32_t)strtoul(l.c_str(), 0, 16)); }
    std::vector<std::vector<uint8_t>> kv[2];     // [v][t*2+g] -> HD bytes
    {
        std::ifstream f(dir + "/kv.hex"); std::string l; int n = 0;
        while (f >> l) {
            std::vector<uint8_t> row(HD);
            for (int d = 0; d < HD; d++) row[d] = (uint8_t)strtoul(l.substr(2 * (HD - 1 - d), 2).c_str(), 0, 16);
            kv[n < KVH * T ? 0 : 1].push_back(row); n++;
        }
    }
    std::vector<uint32_t> gold;
    { std::ifstream f(dir + "/gold.hex"); std::string l; while (f >> l) gold.push_back((uint32_t)strtoul(l.c_str(), 0, 16)); }
    if ((int)q.size() != NH * HD || (int)kv[0].size() != KVH * T || (int)kv[1].size() != KVH * T || (int)gold.size() != NH * HD) {
        fprintf(stderr, "bad vectors q=%zu k=%zu v=%zu gold=%zu T=%d\n", q.size(), kv[0].size(), kv[1].size(), gold.size(), T);
        return 2;
    }

    if (T < 1 || T > 8192) return 2;
    Vot_qwen_qkez_phase_tb* top = new Vot_qwen_qkez_phase_tb;
    uint64_t cyc = 0;
    auto tick = [&]() { top->clk = 0; top->eval(); top->clk = 1; top->eval(); cyc++; };
    top->rst_n = 0; top->start = 0; top->T = MUT == "context_length" ? T - 1 : T; top->q_valid = 0;
    for (int i = 0; i < 5; i++) tick();
    top->rst_n = 1; tick();

    std::deque<Req> rq[4 * R];
    std::deque<Rsp> pend[4 * R];
    double tok[4] = {0, 0, 0, 0};
    int rr[4] = {0, 0, 0, 0};
    std::vector<uint32_t> out(NH * HD, 0xDEADBEEF);
    std::vector<int> got(NH * HD, 0);
    int nout = 0;
    auto readhex=[&](const char* name){std::vector<uint32_t> v; std::ifstream f(dir+"/"+name);std::string l;while(f>>l)v.push_back(strtoul(l.c_str(),0,16));return v;};
    auto gs=readhex("score.hex"), ge=readhex("exp_bf16.hex"), gm=readhex("max.hex"), gz=readhex("denom.hex");
    if(gs.size()!=4*T || ge.size()!=4*T || gm.size()!=4 || gz.size()!=4) return 2;
    std::vector<int> cs(4*T),ce(4*T),cm(4),cz(4);
    int ns=0,ne=0,nm=0,nz=0,wrong=0,tagerr=0;
    int64_t scfirst=-1,sclast=-1,efirst=-1,elast=-1,zlast=-1;
    auto check=[&](std::vector<int>& seen,const std::vector<uint32_t>& expected,int idx,uint32_t actual,int& count){
        if(idx<0 || idx>=int(seen.size())){tagerr++;return;}
        if(seen[idx]++) tagerr++;
        count++;
        if(actual!=expected[idx]) { if(wrong<8) fprintf(stderr,"phase mismatch idx=%d got=%08x expected=%08x\n",idx,actual,expected[idx]);wrong++; }
    };
    // events
    const int NEV = 16;
    int64_t ev_first[4][NEV], hub_first[8];
    for (int s = 0; s < 4; s++) for (int b = 0; b < NEV; b++) ev_first[s][b] = -1;
    for (int b = 0; b < 8; b++) hub_first[b] = -1;
    int64_t row_first[4][2], row_last[4][2];
    for (int s = 0; s < 4; s++) for (int v = 0; v < 2; v++) { row_first[s][v] = -1; row_last[s][v] = -1; }
    int64_t out_first = -1, out_last = -1;
    uint64_t t0 = cyc;
    int fault = 0;
    uint64_t served = 0;
    // start + q beats (32 BF16 per beat)
    const int NQB = NH * HD * QW / 512;
    int qb = -1;
    while (cyc - t0 < MAXC && !(ns==4*T && ne==4*T && nm==4 && nz==4)) {
        // inputs for this edge
        top->start = (qb == -1);
        top->q_valid = (qb >= 0 && qb < NQB && (!STALL || cyc % 7 != 3));
        if (top->q_valid) {
            top->q_beat = MUT == "group" ? qb + NQB : qb;
            for (int i = 0; i < QLANES; i++) { uint32_t w=q[QLANES * (MUT == "q_order" ? (qb ^ 1) : qb) + i]; if(MUT=="precision")w&=0xffff0000u; sbits(top->q_data,QW*i,QW,w); }
        }
        if (qb == -1 || top->q_valid) qb++;
        // HBM responses due this edge (one per engine)
        for (int x = 0; x < 4 * R; x++) {
            int s = x / R;
            (void)s;
            if (!pend[x].empty() && pend[x].front().at <= cyc && (!STALL || (cyc + x) % 11 != 4)) {
                Rsp r = pend[x].front(); pend[x].pop_front();
                sbits(top->rsp_valid, x, 1, 1);
                int mt = MUT == "context" ? (r.t + 1) % T : r.t;
                const std::vector<uint8_t>& row = kv[r.v][KVH * mt + r.g];
                for (int d = 0; d < HD; d++) sbits(top->rsp_data, (x * HD + d) * 8, 8, (MUT=="drop_k" && !r.v) ? 0 : row[d]);
            } else sbits(top->rsp_valid, x, 1, 0);
        }
        tick();
        uint64_t now = cyc - t0;
        for(int x=0;x<4*R;x++) {
            int s=x/R;
            for(int phase=0;phase<2;phase++) {
                bool valid=phase?gbits(top->dbg_ew_v,x,1):gbits(top->dbg_sc_v,x,1);
                if(!valid) continue;
                int a=phase?gbits(top->dbg_ew_a,12*x,12):gbits(top->dbg_sc_a,12*x,12);
                int t=512*((a&2047)/128)+128*s+(a&127);
                if(a&2048){tagerr++;continue;}
                for(int h=0;h<4;h++) {
                    uint32_t d=phase?gbits(top->dbg_ew_d,64*x+16*h,16):gbits(top->dbg_sc_d,128*x+32*h,32);
                    check(phase?ce:cs,phase?ge:gs,h*T+t,d,phase?ne:ns);
                }
                if(phase){if(efirst<0)efirst=now;elast=now;} else {if(scfirst<0)scfirst=now;sclast=now;}
            }
        }
        if(top->dbg_m_v){if(top->dbg_m_g)tagerr++;check(cm,gm,top->dbg_m_h,top->dbg_m_d,nm);}
        if(top->dbg_z_v){check(cz,gz,top->dbg_z_h,top->dbg_z_d,nz);zlast=now;}
        // requests issued at this edge
        for (int x = 0; x < 4 * R; x++)
            if (gbits(top->req_valid, x, 1)) {
                Req r{(int)gbits(top->req_v, x, 1), (int)gbits(top->req_g, x, 1), (int)gbits(top->req_t, 13 * x, 13)};
                if (r.t >= T || r.g >= KVH || ((r.t % NHB_PV_SPLIT) / (NHB_PV_SPLIT / 4)) != x / R) { fprintf(stderr, "bad request t=%d T=%d x=%d\n", r.t, T, x); return 3; }
                rq[x].push_back(r);
            }
        // HBM service: token bucket per stack, round robin over its engines, one row per engine per cycle
        for (int s = 0; s < 4; s++) {
            tok[s] += BPC;
            if (tok[s] > BPC + HD) tok[s] = BPC + HD;
            for (int k = 0; k < R; k++) {
                int x = s * R + (rr[s] + k) % R;
                if (rq[x].empty() || tok[s] < HD || (STALL && (cyc + s) % 13 == 5)) continue;
                Req r = rq[x].front(); rq[x].pop_front();
                tok[s] -= HD;
                pend[x].push_back(Rsp{cyc + (uint64_t)LAT, r.v, r.g, r.t});
                served++;
                if (row_first[s][r.v] < 0) row_first[s][r.v] = now;
                row_last[s][r.v] = now;
            }
            rr[s] = (rr[s] + 1) % R;
        }
        // events
        for (int s = 0; s < 4; s++)
            for (int b = 0; b < NEV; b++)
                if (ev_first[s][b] < 0 && gbits(top->ev_stack, 16 * s + b, 1)) ev_first[s][b] = now;
        for (int b = 0; b < 8; b++) if (hub_first[b] < 0 && ((top->ev_hub >> b) & 1)) hub_first[b] = now;
        if (top->fault) fault |= top->fault;
        if (top->out_valid) {
            int g = top->out_g, beat = top->out_beat;
            int bph = HD / 16, h = 4 * g + beat / bph, d0 = (beat % bph) * 16;
            if (g >= KVH || beat >= 4 * bph || h >= NH) {
                fprintf(stderr, "bad output group=%d beat=%d KVH=%d\n", g, beat, KVH); return 3;
            }
            for (int l = 0; l < 16; l++) {
                int i = h * HD + d0 + l;
                out[i] = (uint32_t)gbits(top->out_data, 32 * l, 32);
                got[i]++; nout++;
            }
            if (out_first < 0) out_first = now;
            out_last = now;
        }
    }
    int missing=0;
    for(auto* a:{&cs,&ce,&cm,&cz}) for(int n:*a) if(n!=1) missing++;
    bool exact=wrong==0 && tagerr==0 && missing==0 && fault==0;
    printf("{\"scope\":\"QK_EXP_Z_PHASE_ONLY\",\"ctx\":%d,\"scores\":%d,\"exponents\":%d,\"maxima\":%d,\"denominators\":%d,\"data_mismatches\":%d,\"tag_errors\":%d,\"missing_words\":%d,\"fault\":%d,\"exact\":%s,\"cycles\":%llu,\"rows_served\":%llu,\"score_first\":%lld,\"score_last\":%lld,\"exp_first\":%lld,\"exp_last\":%lld,\"denom_last\":%lld}\n",T,ns,ne,nm,nz,wrong,tagerr,missing,fault,exact?"true":"false",(unsigned long long)(cyc-t0),(unsigned long long)served,(long long)scfirst,(long long)sclast,(long long)efirst,(long long)elast,(long long)zlast);
    delete top;return exact?0:1;
}
