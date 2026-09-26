// Host binary32 arithmetic for rtl/test/sim_hdc_v41x_fastfp_dpi.sv (simulation only).
// x86-64 SSE float: IEEE RNE, gradual underflow (no FTZ/DAZ is ever set here).
#include <cmath>
#include <cstdint>
#include <cstring>
#include "svdpi.h"

static inline float f_of(uint32_t u) { float f; std::memcpy(&f, &u, 4); return f; }
static inline uint32_t u_of(float f) { uint32_t u; std::memcpy(&u, &f, 4); return u; }
static inline bool nonfinite(uint32_t u) { return ((u >> 23) & 0xFF) == 0xFF; }

static uint32_t finish(float r, int* err) {
    if (std::isinf(r) || std::isnan(r)) { *err = 2; return 0; }
    *err = 0;
    uint32_t u = u_of(r);
    return (u & 0x7FFFFFFFu) == 0 ? 0u : u;          // every zero result +0
}

extern "C" unsigned int ot_v41x_fadd(unsigned int a, unsigned int b, int* err) {
    if (nonfinite(a) || nonfinite(b)) { *err = 1; return 0; }
    volatile float r = f_of(a) + f_of(b);
    return finish(r, err);
}

extern "C" unsigned int ot_v41x_fmul(unsigned int a, unsigned int b, int* err) {
    if (nonfinite(a) || nonfinite(b)) { *err = 1; return 0; }
    volatile float r = f_of(a) * f_of(b);
    return finish(r, err);
}
