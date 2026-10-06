// Tile-only replay of one W12 tile element (ot_qwen_rom_tile_logic_w12) from the port records the HA8 host
// writes with RT_TILE_TRACE (qwen_hbmacc_rt_w12.cpp TileRec): one record per fabric clock edge of the real
// decode, inputs just before the rising edge, outputs just after it.  The replay applies each record's inputs,
// clocks the tile once, and compares every output bit-exact with the host's (exit 3 on any mismatch), so the
// activity it dumps is the activity of the tile inside the exact decode.  Gated cycles (the die's ME_IDLE_GATE
// holds the fabric clock) have no record: the VCD covers clocked cycles only, at the 1.2 GHz period.
//
//   qwen_tile_replay REC [+VCD=path] [+BEGIN=n] [+END=n] [+HALF_PS=417] [+FLIP=rec] [+STATS=json]
//     BEGIN/END: record window traced to the VCD (default: all);  FLIP: negative control, invert the whole
//     instruction word of the first issue (ib_go) at or after that record (the replay must then report mismatches);  STATS: per-record port counts (ROM bank reads,
//     KV reads) for the macro access energy.
// Compile with Verilator --trace, top ot_qwen_rom_tile_logic_w12, prefix Vtile, at the host's tile parameters.
#include "Vtile.h"
#include "verilated.h"
#include "verilated_vcd_c.h"
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#define OT_TILE_INPUTS(X) X(rst_n) X(tile_id) X(ib_go) X(ib) X(xl) X(n_a) X(n_b) X(n_va) X(rom_rd) X(kvs_rd) X(kv_q)
#define OT_TILE_OUTPUTS(X) X(t_out) X(t_vout) X(n_y) X(n_vy) X(fault) X(rom_ce) X(rom_addr) X(kvs_r_ce) X(kvs_r_addr) X(kv_re) X(kv_addr)

static unsigned long long plus(const char* name, unsigned long long d) {
    std::string k = std::string(name) + "=";
    const char* p = Verilated::commandArgsPlusMatch(k.c_str());
    return (p && *p) ? strtoull(p + k.size() + 1, nullptr, 10) : d;
}
static std::string plus_s(const char* name) {
    std::string k = std::string(name) + "=";
    const char* p = Verilated::commandArgsPlusMatch(k.c_str());
    return (p && *p) ? std::string(p + k.size() + 1) : "";
}

int main(int argc, char** argv) {
    if (argc < 2) { fprintf(stderr, "usage: %s REC [+VCD=..]\n", argv[0]); return 2; }
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);
    FILE* f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    uint32_t hdr[4];
    if (fread(hdr, 4, 4, f) != 4 || hdr[0] != 0x4f54524cu) { fprintf(stderr, "bad header\n"); return 2; }
    Vtile* x = new Vtile;
    uint32_t in_sz = 0, out_sz = 0;
#define OT_SZ(n) in_sz += sizeof(x->n);
    OT_TILE_INPUTS(OT_SZ)
#undef OT_SZ
#define OT_SZ(n) out_sz += sizeof(x->n);
    OT_TILE_OUTPUTS(OT_SZ)
#undef OT_SZ
    if (hdr[1] != in_sz || hdr[2] != out_sz) {
        fprintf(stderr, "record layout %u/%u != model %u/%u (tile parameters differ)\n", hdr[1], hdr[2], in_sz, out_sz);
        return 2;
    }
    const std::string vcd = plus_s("VCD"), stats = plus_s("STATS");
    const unsigned long long vb = plus("BEGIN", 0), ve = plus("END", ~0ULL), hp = plus("HALF_PS", 417);
    const unsigned long long flip = plus("FLIP", ~0ULL);
    bool flipped = false;
    VerilatedVcdC* tfp = nullptr;
    std::vector<uint8_t> out(out_sz), mine(out_sz);
    unsigned long long rec = 0, mism = 0, first_bad = ~0ULL, traced = 0;
    uint32_t cyc = 0, cyc0 = 0, cyc_last = 0;
    FILE* st = stats.empty() ? nullptr : fopen(stats.c_str(), "w");
    if (st) fprintf(st, "rec cyc rom_ce rom_addr kv_re\n");
    x->clk = 1;            // the host's tiles sit with clk high between edges
    x->eval();
    while (fread(&cyc, 4, 1, f) == 1) {
        if (rec == 0) cyc0 = cyc;
        cyc_last = cyc;
#define OT_R(n) if (fread(&x->n, sizeof(x->n), 1, f) != 1) { fprintf(stderr, "short record\n"); return 2; }
        OT_TILE_INPUTS(OT_R)
#undef OT_R
        if (!flipped && rec >= flip && x->ib_go) {   // negative control: corrupt the first issued instruction word
            for (auto& w : x->ib.m_storage) w = ~w;
            flipped = true;
        }
        if (fread(out.data(), 1, out_sz, f) != out_sz) { fprintf(stderr, "short record\n"); return 2; }
        const bool in = !vcd.empty() && rec >= vb && rec < ve;
        if (in && !tfp) {
            tfp = new VerilatedVcdC;
            x->trace(tfp, 99);
            tfp->open(vcd.c_str());
        }
        if (tfp && !in) { tfp->close(); delete tfp; tfp = nullptr; }
        x->clk = 0; x->eval();
        if (tfp) tfp->dump(static_cast<uint64_t>((2 * traced) * hp));
        x->clk = 1; x->eval();
        if (tfp) { tfp->dump(static_cast<uint64_t>((2 * traced + 1) * hp)); traced++; }
        size_t o = 0;
#define OT_C(n) memcpy(mine.data() + o, &x->n, sizeof(x->n)); o += sizeof(x->n);
        OT_TILE_OUTPUTS(OT_C)
#undef OT_C
        if (memcmp(mine.data(), out.data(), out_sz)) { mism++; if (first_bad == ~0ULL) first_bad = rec; }
        if (st) fprintf(st, "%llu %u %u %u %u\n", rec, cyc, unsigned(x->rom_ce), unsigned(x->rom_addr), unsigned(x->kv_re));
        rec++;
    }
    if (tfp) { tfp->dump(static_cast<uint64_t>((2 * traced) * hp)); tfp->close(); delete tfp; }
    if (st) fclose(st);
    x->final();
    printf("TILE_REPLAY tile=%u records=%llu first_cyc=%u last_cyc=%u traced=%llu mismatches=%llu first_bad=%lld\n",
           hdr[3], rec, cyc0, cyc_last, traced, mism, first_bad == ~0ULL ? -1LL : (long long)first_bad);
    delete x;
    return mism ? 3 : 0;
}
