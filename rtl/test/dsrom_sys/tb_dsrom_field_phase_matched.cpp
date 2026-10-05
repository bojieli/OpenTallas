// DS-ROM recovery lever "field": PQ (pipelined-phase) region vehicle driver (tools/dsrom_recovery_field.py).
// Bench only: no hardware.
//
// Model: Vpq = ot_v41_fieldtop_pq_w17w10 (spine_pq + vector-memory model + field_pq), built at one return region's
// full shape (NP pair slots, R = 1, the 1.2 GHz FAST/PP W10 element as PQ successor).  Images from +OT_ROM_DIR=DIR
// (tools/v41_die_images_w17w10.write_field).
//
// Diagnostic matched control: optional --serial-offer waits actual idle before the next offer.
// Same RTL/archive, geometry, clocks, input bytes, arithmetic and output checks in both modes.
// XR is the actual preedge VM read; VMW is the actual preedge-to-posedge VM commit.
// This isolates scheduling overlap, not the area or speed of a historical bare PQ0 implementation.
// Usage: tb DIR OPS     OPS lines: "ph np xbase xps obase ops".  All ops of the file are ONE node: each is offered
// on the first cycle `ready` is high (back to back, the spine pipelines them).  Prints "W <cycle> <addr> <data>"
// per VM row write, "G <cycle> <tag>" when an op's go is broadcast, "E <cycle> <tag>" when its last beat is sent,
// "A <k> <cycle>" when op k is accepted, then "NODE go=<first accept> first_w= last_w= idle= fault=".
#include "Vpq.h"
#include "Vpq___024root.h"
#include "verilated.h"
#include <cstdio>
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
    Vpq top(&ctx, "pq");
    const bool serial_offer = argc == 4 && std::string(argv[3]) == "--serial-offer";
    long cyc = 0, first_w = -1, last_w = -1, g0 = -1;
    uint64_t input_read_beats = 0;
    long last_vm_commit = -1;
    auto tick = [&](const Op* o, bool go, uint8_t rst) {
        top.go = go;
        top.rst_n = rst;
        if (o) { top.i_ph = o->ph; top.i_np = o->np; top.i_xbase = o->xbase; top.i_xps = o->xps;
                 top.i_obase = o->obase; top.i_ops = o->ops; }
        top.clk = 0; top.eval();
        if (rst && top.rootp->ot_v41_fieldtop_pq_w17w10__DOT__x_re) {
            input_read_beats++;
            printf("XR %ld %u\n", cyc + 1, top.rootp->ot_v41_fieldtop_pq_w17w10__DOT__x_addr);
        }
        std::vector<unsigned> commits;
        if (rst) for (int port = 0; port < NR; port++)
            if ((uint64_t(top.o_we) >> port) & 1) {
                printf("VMW %ld %lu %08lx\n", cyc + 1,
                       (unsigned long)getb(top.o_addr, VAW * port, VAW),
                       (unsigned long)getb(top.o_data, 32 * port, 32));
                last_vm_commit = cyc + 1;
                commits.push_back(getb(top.o_addr, VAW * port, VAW));
            }
        top.clk = 1; top.eval();
        for (auto address : commits)
            printf("VMS %ld %u %08x\n", cyc + 1, address,
                   top.rootp->ot_v41_fieldtop_pq_w17w10__DOT__vm[address]);
        top.clk = 0; top.eval();
        cyc++;
        for (int k = 0; k < NR; k++)
            if ((uint64_t(top.o_we) >> k) & 1) {
                printf("W %ld %lu %08lx\n", cyc, (unsigned long)getb(top.o_addr, VAW * k, VAW),
                       (unsigned long)getb(top.o_data, 32 * k, 32));
                if (first_w < 0) first_w = cyc;
                last_w = cyc;
            }
        if (top.ev_go) printf("G %ld %d\n", cyc, int(top.ev_tag));
        if (top.ev_end) printf("E %ld %d\n", cyc, int(top.ev_tag));
    };
    for (int i = 0; i < 6; i++) tick(nullptr, false, 0);
    for (int i = 0; i < 4; i++) tick(nullptr, false, 1);
    cyc = 0;
    const long LIMIT = 2000000;
    size_t k = 0;
    while (k < ops.size()) {
        if (top.ready && (!serial_offer || top.idle)) {
            tick(&ops[k], true, 1);
            if (g0 < 0) g0 = cyc;
            printf("A %zu %ld\n", k, cyc);
            k++;
        } else tick(nullptr, false, 1);
        if (cyc > LIMIT) { printf("FAIL timeout\n"); return 1; }
        if (top.fault) { printf("FAIL fault\n"); return 1; }
    }
    do { tick(nullptr, false, 1); if (cyc > LIMIT) { printf("FAIL timeout\n"); return 1; } } while (!top.idle);
    long idle = cyc;
    for (int i = 0; i < 16; i++) tick(nullptr, false, 1);
    printf("NODE go=%ld first_w=%ld last_w=%ld idle=%ld fault=%d\n", g0, first_w, last_w, idle, int(top.fault));
    if (top.fault) { printf("FAIL fault\n"); return 1; }
    printf("PROFILE serial_offer=%d input_read_beats=%lu input_bytes=%lu last_write=%ld idle=%ld drain_after_write=%ld last_vm_commit=%ld drain_after_vm_commit=%ld\n",
           int(serial_offer), (unsigned long)input_read_beats, (unsigned long)(input_read_beats * 64 * 4), last_w, idle, idle-last_w, last_vm_commit, idle-last_vm_commit);
    printf("PASS cycles=%ld\n", cyc);
    return 0;
}
