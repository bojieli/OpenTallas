// Exhaustive check of ot_dsrom_divc (rtl/hdc/v41x/ot_dsrom_divc.sv) for one divisor D = F * 2^K (Verilator
// -GF -GK): EVERY binary32 bit pattern x in [lo, hi) (default: all positive finite values, 0 .. 0x7F7FFFFF) plus
// the negative values of a stride, against the C++ float division x / (float)D (IEEE RNE, default environment)
// with zero results canonicalised to +0 (tools/hdc_golden_v41.div); nonfinite inputs must raise fault.
// Usage: Vot_dsrom_divc <D> [lo hi neg_stride].  Prints DIVC D=.. checked=.. errors=.. faults_ok=.. and PASS/FAIL.
#include "Vot_dsrom_divc.h"
#include "verilated.h"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cmath>

static uint32_t f2u(float f) { uint32_t u; std::memcpy(&u, &f, 4); return u; }
static float u2f(uint32_t u) { float f; std::memcpy(&f, &u, 4); return f; }

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "usage: %s D [lo hi neg_stride]\n", argv[0]); return 2; }
    const double D = std::atof(argv[1]);
    uint64_t lo = argc > 2 ? std::strtoull(argv[2], nullptr, 0) : 0;
    uint64_t hi = argc > 3 ? std::strtoull(argv[3], nullptr, 0) : 0x7F800000ull;
    uint64_t ns = argc > 4 ? std::strtoull(argv[4], nullptr, 0) : 4099;
    const float fd = (float)D;
    Verilated::commandArgs(argc, argv);
    Vot_dsrom_divc* m = new Vot_dsrom_divc;
    const int LAT = 9;
    uint32_t pipe[LAT + 1];
    bool pv[LAT + 1];
    std::memset(pv, 0, sizeof pv);
    m->clk = 0; m->rst_n = 0; m->v = 0; m->x = 0; m->eval();
    for (int i = 0; i < 4; i++) { m->clk = 1; m->eval(); m->clk = 0; m->eval(); }
    m->rst_n = 1; m->eval();
    uint64_t checked = 0, errors = 0, fault_ok = 0, fault_bad = 0;
    // input sequence: [lo, hi) then negatives (stride ns), then +inf, -inf, a NaN, then drain
    uint64_t nneg = (hi - lo + ns - 1) / ns;
    uint64_t total = (hi - lo) + nneg + 3;
    for (uint64_t k = 0; k < total + LAT + 1; k++) {
        bool v = k < total;
        uint32_t x = 0;
        if (v) {
            if (k < hi - lo) x = (uint32_t)(lo + k);
            else if (k < hi - lo + nneg) x = 0x80000000u | (uint32_t)(lo + (k - (hi - lo)) * ns);
            else x = (k == total - 3) ? 0x7F800000u : (k == total - 2) ? 0xFF800000u : 0x7FC00001u;
        }
        m->v = v; m->x = x;
        m->clk = 1; m->eval();
        m->clk = 0; m->eval();
        for (int j = LAT; j > 0; j--) { pipe[j] = pipe[j - 1]; pv[j] = pv[j - 1]; }
        pipe[0] = x; pv[0] = v;
        // after this edge the output belongs to the input issued LAT edges ago: pipe[LAT - 1]
        if (m->vo) {
            uint32_t xi = pipe[LAT - 1];
            if (!pv[LAT - 1]) { errors++; continue; }
            float xf = u2f(xi);
            if (!std::isfinite(xf)) {
                if (m->fault) fault_ok++; else fault_bad++;
                continue;
            }
            float q = xf / fd;
            uint32_t want = (q == 0.0f) ? 0u : f2u(q);
            checked++;
            if (m->y != want || m->fault) {
                if (errors < 10) std::printf("MISMATCH x=%08x got=%08x want=%08x fault=%d\n", xi, (unsigned)m->y, want, (int)m->fault);
                errors++;
            }
        }
    }
    std::printf("DIVC D=%g lo=%#llx hi=%#llx checked=%llu errors=%llu faults_ok=%llu faults_bad=%llu\n", D,
                (unsigned long long)lo, (unsigned long long)hi, (unsigned long long)checked,
                (unsigned long long)errors, (unsigned long long)fault_ok, (unsigned long long)fault_bad);
    bool pass = errors == 0 && fault_bad == 0 && fault_ok == 3 && checked == (hi - lo) + nneg;
    std::printf("%s\n", pass ? "PASS" : "FAIL");
    delete m;
    return pass ? 0 : 1;
}
