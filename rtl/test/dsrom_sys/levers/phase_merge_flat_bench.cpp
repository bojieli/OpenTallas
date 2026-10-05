// Copied verbatim from origin/claude/free-levers-audit-20261003:results/uarch/free_levers_audit_20261003/bench/flat_bench.cpp
// Flat-RTL phase timer for the phase-merge A/B: drives rtl/w17_runtime/v41die/ot_v41_fieldtop (spine + vector memory
// + ot_v41_field, the reference of tools/w17_runtime_v41_field_rt_gate.py) through the ops file, one phase after
// another exactly as that gate's host drives it (reset 6+4 ticks, wait ready, go one tick, run until idle), and
// prints every vector-memory write and each op's spine phase_cycles and wall cycles.
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>
#include "verilated.h"
#include "Vflat.h"
template <class V> static uint64_t getb(const V& v, size_t pos, int n) {
    if constexpr (std::is_integral_v<V>) return (uint64_t(v) >> pos) & (n >= 64 ? ~0ull : ((1ull << n) - 1));
    else { uint64_t r = 0; for (int b = 0; b < n; b++) r |= uint64_t((v[(pos + b) / 32] >> ((pos + b) % 32)) & 1) << b; return r; }
}
struct Op { int ph, np, xbase, xps, obase, ops; };
int main(int argc, char** argv) {
    if (argc < 3) { printf("usage: flat DIR OPS\n"); return 2; }
    std::string plus = std::string("+OT_ROM_DIR=") + argv[1];
    const char* av[] = {"flat", plus.c_str()};
    std::vector<Op> ops;
    { std::ifstream f(argv[2]); std::string line;
      while (std::getline(f, line)) { std::istringstream is(line); Op o; if (is >> o.ph >> o.np >> o.xbase >> o.xps >> o.obase >> o.ops) ops.push_back(o); } }
    VerilatedContext ctx; ctx.randReset(0); ctx.commandArgs(2, av);
    Vflat m(&ctx, "flat");
    uint8_t rst = 0; long cyc = 0, writes = 0;
    auto tick = [&](const Op* o, bool go) {
        m.go = go; m.rst_n = rst;
        if (o) { m.i_ph = o->ph; m.i_np = o->np; m.i_xbase = o->xbase; m.i_xps = o->xps; m.i_obase = o->obase; m.i_ops = o->ops; }
        m.clk = 1; m.eval(); m.clk = 0; m.eval(); cyc++;
        for (int k = 0; k < NR; k++)
            if ((uint64_t(m.o_we) >> k) & 1) {
                printf("W %lu %08lx\n", (unsigned long)getb(m.o_addr, VAW * k, VAW), (unsigned long)getb(m.o_data, 32 * k, 32));
                writes++;
            }
    };
    for (int i = 0; i < 6; i++) tick(nullptr, false);
    rst = 1;
    for (int i = 0; i < 4; i++) tick(nullptr, false);
    const long LIMIT = 4000000;
    for (size_t k = 0; k < ops.size(); k++) {
        long w0 = cyc;
        while (!m.ready) { tick(nullptr, false); if (cyc > LIMIT) { printf("FAIL timeout\n"); return 1; } }
        tick(&ops[k], true);
        long t0 = cyc;
        do { tick(&ops[k], false); if (cyc > LIMIT) { printf("FAIL timeout\n"); return 1; } } while (!m.idle);
        printf("OP %zu ph=%d cycles=%u wall=%ld wait_ready=%ld fault=%d\n", k, ops[k].ph, m.phase_cycles, cyc - t0 + 1,
               t0 - 1 - w0, m.fault);
        if (m.fault) { printf("FAIL fault op=%zu\n", k); return 1; }
    }
    for (int i = 0; i < 32; i++) tick(nullptr, false);
    printf("PASS cycles=%ld writes=%ld\n", cyc, writes);
    return 0;
}
