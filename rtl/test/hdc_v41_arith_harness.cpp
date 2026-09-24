// Verilator driver that checks the V4.1 decode core's correctly rounded
// binary32 pipes against the host's IEEE arithmetic, operand by operand.
//
//   -DDUT_DIV : top ot_hdc_fdiv   (y = a / b)
//   -DDUT_SQRT: top ot_hdc_fsqrt  (y = sqrt(a)), and the qualified
//               rtl/abi3/ot_a3_engram_fp32_sqrt_rne_pipe is checked by
//               tb_hdc_fsqrt_equiv instead.
//
// Reference: the host's binary32 division / square root (SSE, round to nearest
// even, gradual underflow; compiled without fast-math), with every zero result
// canonical +0.  A nonfinite operand, a zero divisor, a negative radicand or an
// overflowing quotient must raise `fault` with y = +0.  Operands are drawn
// from an edge-biased generator (subnormals, zeros, extreme and colliding
// exponents, short significands that make exact and tie quotients likely);
// the input valid is dropped at random (bubbles).  +N=<count> sets the number.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <deque>
#include "verilated.h"
#if defined(DUT_DIV)
#include "Vot_hdc_fdiv.h"
typedef Vot_hdc_fdiv Top;
#elif defined(DUT_SQRT)
#include "Vot_hdc_fsqrt.h"
typedef Vot_hdc_fsqrt Top;
#else
#error "define DUT_DIV or DUT_SQRT"
#endif

static uint64_t s = 0x9E3779B97F4A7C15ull;
static uint32_t rnd() {
    s ^= s << 13; s ^= s >> 7; s ^= s << 17;
    return (uint32_t)(s >> 16);
}
static float f_of(uint32_t u) { float f; std::memcpy(&f, &u, 4); return f; }
static uint32_t u_of(float f) { uint32_t u; std::memcpy(&u, &f, 4); return u; }

static uint32_t operand(uint32_t near_exp) {
    uint32_t r = rnd(), m = rnd() & 0x7FFFFF, sgn = rnd() & 0x80000000u;
    switch (r & 15) {
    case 0: return rnd();                                            // anything, incl. nonfinite
    case 1: return sgn | (m >> (rnd() % 24));                        // subnormal (or zero)
    case 2: return sgn;                                              // +-0
    case 3: return sgn | ((1 + rnd() % 8) << 23) | m;                // tiny normal
    case 4: return sgn | ((246 + rnd() % 9) << 23) | m;              // huge normal
    case 5: return sgn | (0xFFu << 23) | ((rnd() & 1) ? m : 0);      // inf / NaN
    case 6: return sgn | (((near_exp + rnd() % 5 - 2) & 0xFF) << 23) | (m & ~((1u << (rnd() % 23)) - 1));
    case 7: return sgn | (((near_exp + rnd() % 3 - 1) & 0xFF) << 23) | (m & 0x7FF000);  // short significands
    case 8: return 0x7F7FFFFFu | sgn;                                // max finite
    case 9: return sgn | 0x00800000u | (m & 0xF);                    // min normal-ish
    default: return sgn | ((1 + rnd() % 254) << 23) | m;             // normal
    }
}

int main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    long n = 1000000;
    const char* arg = Verilated::commandArgsPlusMatch("N=");
    if (arg && arg[0]) n = std::atol(arg + 3);
    Top* top = new Top;
    struct Exp { uint32_t y; bool fault; uint32_t a, b; };
    std::deque<Exp> q;
    long sent = 0, checked = 0, bad = 0, faults = 0, subnormal_out = 0, cyc = 0, quiet = 0;
    top->clk = 0; top->rst_n = 0; top->v = 0; top->a = 0;
#if defined(DUT_DIV)
    top->b = 0;
#endif
    for (int i = 0; i < 4; i++) { top->clk = 0; top->eval(); top->clk = 1; top->eval(); }
    top->rst_n = 1;
    while (true) {
        top->clk = 0;
        bool fire = sent < n && (rnd() & 7) != 0;
        top->v = fire;
        if (fire) {
            uint32_t a = operand(127 + (int)(rnd() % 9) - 4), b = 0;
            float fa = f_of(a), r;
            Exp e;
#if defined(DUT_DIV)
            b = operand((a >> 23) & 0xFF);
            if (rnd() % 16 == 0) b = a ^ (rnd() & 0x80000000u);      // quotient exactly +-1
            // a power-of-two divisor makes the quotient exact, so a subnormal
            // result lands on rounding ties (a normal quotient never ties)
            if (rnd() % 16 == 1) b = (rnd() & 0x80000000u) | ((127 + rnd() % 30) << 23);
            if (rnd() % 16 == 2) b = (rnd() & 0x80000000u) | ((127 + rnd() % 30) << 23) | ((rnd() & 7) << 20);
            fa = f_of(a);
            float fb = f_of(b);
            r = fa / fb;
            e.fault = !std::isfinite(fa) || !std::isfinite(fb) || fb == 0.0f || !std::isfinite(r);
            top->b = b;
#else
            if (rnd() & 1) a &= 0x7FFFFFFFu;                           // mostly nonnegative
            fa = f_of(a);
            r = std::sqrt(fa);
            e.fault = !std::isfinite(fa) || (fa < 0.0f);
#endif
            top->a = a;
            e.y = e.fault ? 0u : (r == 0.0f ? 0u : u_of(r));
            e.a = a; e.b = b;
            q.push_back(e);
            sent++;
        }
        top->eval();
        top->clk = 1;
        top->eval();
        cyc++;
        if (top->vo) {
            if (q.empty()) { std::printf("SPURIOUS vo at cycle %ld\n", cyc); bad++; }
            else {
                Exp e = q.front(); q.pop_front();
                bool f = top->fault;
                if (f != e.fault || (!e.fault && top->y != e.y)) {
                    if (bad < 10)
                        std::printf("MISMATCH a=%08x b=%08x got=%08x/%d exp=%08x/%d\n", e.a, e.b,
                                    (unsigned)top->y, (int)f, e.y, (int)e.fault);
                    bad++;
                }
                if (e.fault) faults++;
                else if (e.y != 0 && ((e.y >> 23) & 0xFF) == 0) subnormal_out++;
                checked++;
            }
        }
        quiet = (sent >= n && q.empty()) ? quiet + 1 : 0;
        if (quiet > 4 || cyc > 4 * n + 1000) break;
    }
    std::printf("ARITH checked=%ld mismatches=%ld faults=%ld subnormal_results=%ld pending=%zu\n",
                checked, bad, faults, subnormal_out, q.size());
    std::printf("%s\n", (bad == 0 && checked == n && q.empty()) ? "PASS" : "FAIL");
    top->final();
    delete top;
    return 0;
}
