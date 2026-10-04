// DS-ROM 1M ROM-field region vehicle driver (tools/dsrom_1m_field.py).  Bench only: no hardware.
//
// Model: Vflat = the pinned ot_v41_fieldtop_w17w10 (spine + vector-memory model + ot_v41_field_w17w10), built at one
// return region's full shape (NP pair slots, R = 1, the 1.2 GHz FAST/PP W10 element).  ROM / configuration / spine
// images come from +OT_ROM_DIR=DIR (tools/v41_die_images_w17w10.write_field).
//
// Usage: tb DIR OPS     OPS lines: "ph np xbase xps obase ops" (the spine op ports).
// Ops are issued back to back: `go` on the first cycle `ready` is high.  Prints, per cycle of a VM row write,
// "W <cycle> <addr> <data>", and per op "OP <k> go=<cycle> first_w=<cycle> last_w=<cycle> idle=<cycle>
// phase_cycles=<spine counter> writes=<n> fault=<0|1>".  Cycle = rising edges since reset release.
#include "Vflat.h"
#include "verilated.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

template <class V> static uint64_t getb(const V& v, size_t pos, int n) {
    if constexpr (std::is_integral_v<V>) {
        return (uint64_t(v) >> pos) & (n >= 64 ? ~0ull : ((1ull << n) - 1));
    } else {
        uint64_t r = 0;
        for (int b = 0; b < n; b++) r |= uint64_t((v[(pos + b) / 32] >> ((pos + b) % 32)) & 1) << b;
        return r;
    }
}

struct Op { int ph, np, xbase, xps, obase, ops; };

int main(int argc, char** argv) {
    if (argc < 3) { printf("usage: tb DIR OPS\n"); return 2; }
    std::string dir = argv[1];
    std::vector<Op> ops;
    {
        std::ifstream f(argv[2]);
        std::string line;
        while (std::getline(f, line)) {
            std::istringstream is(line);
            Op o;
            if (is >> o.ph >> o.np >> o.xbase >> o.xps >> o.obase >> o.ops) ops.push_back(o);
        }
    }
    std::string plus = "+OT_ROM_DIR=" + dir;
    const char* av[] = {"tb", plus.c_str()};
    VerilatedContext ctx;
    ctx.randReset(0);
    ctx.commandArgs(2, av);
    Vflat top(&ctx, "flat");
    long cyc = 0;
    long nw = 0, first_w = -1, last_w = -1;
    auto tick = [&](const Op* o, bool go, uint8_t rst) {
        top.go = go;
        top.rst_n = rst;
        if (o) { top.i_ph = o->ph; top.i_np = o->np; top.i_xbase = o->xbase; top.i_xps = o->xps;
                 top.i_obase = o->obase; top.i_ops = o->ops; }
        top.clk = 1; top.eval();
        top.clk = 0; top.eval();
        cyc++;
        for (int k = 0; k < NR; k++)
            if ((uint64_t(top.o_we) >> k) & 1) {
                printf("W %ld %lu %08lx\n", cyc, (unsigned long)getb(top.o_addr, VAW * k, VAW),
                       (unsigned long)getb(top.o_data, 32 * k, 32));
                nw++;
                if (first_w < 0) first_w = cyc;
                last_w = cyc;
            }
    };
    for (int i = 0; i < 6; i++) tick(nullptr, false, 0);
    for (int i = 0; i < 4; i++) tick(nullptr, false, 1);
    cyc = 0;
    const long LIMIT = 2000000;
    for (size_t k = 0; k < ops.size(); k++) {
        while (!top.ready) { tick(nullptr, false, 1); if (cyc > LIMIT) { printf("FAIL timeout\n"); return 1; } }
        nw = 0; first_w = -1; last_w = -1;
        tick(&ops[k], true, 1);
        long g = cyc;                       // the edge that samples go
        do { tick(&ops[k], false, 1); if (cyc > LIMIT) { printf("FAIL timeout\n"); return 1; } } while (!top.idle);
        printf("OP %zu go=%ld first_w=%ld last_w=%ld idle=%ld phase_cycles=%u writes=%ld fault=%d\n", k, g, first_w,
               last_w, cyc, top.phase_cycles, nw, int(top.fault));
        if (top.fault) { printf("FAIL fault op=%zu\n", k); return 1; }
    }
    for (int i = 0; i < 16; i++) tick(nullptr, false, 1);
    printf("PASS cycles=%ld\n", cyc);
    return 0;
}
