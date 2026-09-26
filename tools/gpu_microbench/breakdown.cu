// breakdown.cu -- WHY the all-SM dependency costs what gather_designs.cu measured on the
// RTX PRO 6000 Blackwell (sm_120, 188 SMs). Decomposition experiments, each small and short
// (~1 ms per trial: the GPU is time-shared with another tenant):
//   A  counter barrier vs participant count N (fit fixed latency + per-arrival slope), and with
//      arrivals spread over 8 / 32 counters
//   B  atomic throughput to one word vs distinct words; single-thread atomic / ld.cg /
//      ld.acquire round-trip latency on 64 lines (near vs far L2)
//   C  one-way latency components: fence after store, st.release, flag ping-pong with
//      volatile+fence / release-acquire / bare volatile / poll delay, pollers hammering the
//      flag line, and the cost of reading a line another SM just wrote
//   D  L2 hot spot: 188 SMs chasing the SAME 128 B line vs 8 replicas vs private lines
//   E  request counting for the counter, LL8, LL16x8 and per-producer-flag gathers
//   F  Megatron all-reduce: red.add phase alone (shared vs private target), phase timing of
//      red + fence + barrier + readback, and an explicit reduce-scatter + all-gather
//   G  DSMEM: cluster.sync, remote ld.shared::cluster latency, DSMEM vs smem vs L2 bandwidth
// All phase timings are clock64 cycles inside the kernel (SM clock measured with %globaltimer).
// Build: /usr/local/cuda-12.8/bin/nvcc -O3 -arch=sm_120 -rdc=true breakdown.cu -o breakdown
// Run:   ./breakdown [steps=1000] [trials=11]     -> JSON on stdout
// Results: results/gpu/blackwell_sync_breakdown.json
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <vector>
#include <string>
#include <algorithm>
#include <cuda_runtime.h>
#include <cooperative_groups.h>
namespace cg = cooperative_groups;
#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { fprintf(stderr, "%s:%d %s\n", __FILE__, __LINE__, cudaGetErrorString(e_)); exit(1); } } while (0)

constexpr int V = 4096, NT = 256;
constexpr unsigned SPIN = 1u << 22;
typedef unsigned long long u64;

__device__ __forceinline__ unsigned long long gtimer() { u64 t; asm volatile("mov.u64 %0, %%globaltimer;" : "=l"(t)); return t; }
__device__ __forceinline__ unsigned smid() { unsigned r; asm volatile("mov.u32 %0, %%smid;" : "=r"(r)); return r; }
__device__ __forceinline__ unsigned ld_acq(const unsigned *p) { unsigned v; asm volatile("ld.acquire.gpu.global.u32 %0, [%1];" : "=r"(v) : "l"(p) : "memory"); return v; }
__device__ __forceinline__ unsigned ld_vol(const unsigned *p) { unsigned v; asm volatile("ld.volatile.global.u32 %0, [%1];" : "=r"(v) : "l"(p) : "memory"); return v; }
__device__ __forceinline__ unsigned ld_rlx(const unsigned *p) { unsigned v; asm volatile("ld.relaxed.gpu.global.u32 %0, [%1];" : "=r"(v) : "l"(p) : "memory"); return v; }
__device__ __forceinline__ unsigned ld_cg(const unsigned *p) { unsigned v; asm volatile("ld.global.cg.u32 %0, [%1];" : "=r"(v) : "l"(p) : "memory"); return v; }
__device__ __forceinline__ void st_vol(unsigned *p, unsigned v) { asm volatile("st.volatile.global.u32 [%0], %1;" :: "l"(p), "r"(v) : "memory"); }
__device__ __forceinline__ void st_rel(unsigned *p, unsigned v) { asm volatile("st.release.gpu.global.u32 [%0], %1;" :: "l"(p), "r"(v) : "memory"); }
__device__ __forceinline__ void st_rlx(unsigned *p, unsigned v) { asm volatile("st.relaxed.gpu.global.u32 [%0], %1;" :: "l"(p), "r"(v) : "memory"); }
__device__ __forceinline__ void red_u32(unsigned *p, unsigned v) { asm volatile("red.relaxed.gpu.global.add.u32 [%0], %1;" :: "l"(p), "r"(v) : "memory"); }
__device__ __forceinline__ void red_v4(float *p, float4 v) { asm volatile("red.relaxed.gpu.global.add.v4.f32 [%0], {%1,%2,%3,%4};" :: "l"(p), "f"(v.x), "f"(v.y), "f"(v.z), "f"(v.w) : "memory"); }
__device__ __forceinline__ uint4 ld_vol_v4(const uint4 *p) { uint4 r; asm volatile("ld.volatile.global.v4.u32 {%0,%1,%2,%3}, [%4];" : "=r"(r.x), "=r"(r.y), "=r"(r.z), "=r"(r.w) : "l"(p) : "memory"); return r; }
__device__ __forceinline__ void st_vol_v4(uint4 *p, uint4 v) { asm volatile("st.volatile.global.v4.u32 [%0], {%1,%2,%3,%4};" :: "l"(p), "r"(v.x), "r"(v.y), "r"(v.z), "r"(v.w) : "memory"); }
__device__ __forceinline__ void st_vol_v2(uint2 *p, uint2 v) { asm volatile("st.volatile.global.v2.u32 [%0], {%1,%2};" :: "l"(p), "r"(v.x), "r"(v.y) : "memory"); }
__device__ __forceinline__ unsigned smem_u32(const void *p) { return (unsigned)__cvta_generic_to_shared(p); }
__device__ __forceinline__ int slo(int b, int nb) { return (int)((unsigned)(b * V) / (unsigned)nb); }
__host__ __device__ __forceinline__ float fval(unsigned s, unsigned i) { return (float)((s * 131u + i * 7u) & 0xFFFFu); }

struct P {
    unsigned *ctr, *flags, *stop, *err, *tmo;
    float *buf, *acc;          // buf: 8 MiB scratch; acc: 3 x V
    uint2 *ll8; uint4 *ll16;
    u64 *stat;                 // accumulators, reset once per experiment
    int a0, a1, a2, a3;
};
#define SPINCHK(cond) { unsigned sp_ = 0; while (cond) if (++sp_ > SPIN) { atomicExch(p.tmo, 1u); break; } }
#define CLUSTER_PAD 0

// ================================================================ A. counter vs participants
// ATOM: arrive atomicAdd + poll atomicAdd(ctr,0) with fences (dep_latency.cu); else K shards,
// fence + atomicAdd arrive on shard b % K, lanes 0..K-1 poll one shard each with ld.acquire.
template <int K, bool ATOM> __global__ void kA(int steps, P p) {
    const int nb = gridDim.x, b = blockIdx.x, t = threadIdx.x;
    const unsigned mine = K == 1 ? nb : (t < K ? (unsigned)((nb - t + K - 1) / K) : 0u);
    for (int s = 1; s <= steps; ++s) {
        __syncthreads();
        if (ATOM) {
            if (t == 0) { __threadfence(); atomicAdd(p.ctr, 1u); SPINCHK(atomicAdd(p.ctr, 0u) < nb * (unsigned)s); __threadfence(); }
        } else {
            if (t == 0) { __threadfence(); atomicAdd(p.flags + (b % K) * 32, 1u); }
            if (t < K) SPINCHK(ld_acq(p.flags + t * 32) < mine * (unsigned)s);
        }
        __syncthreads();
    }
}
// ================================================================ B. atomics
// a0: 0 = thread 0 of every block reds one word; 1 = thread 0 reds its own line;
//     2 = every thread reds one shared word; 3 = every thread reds its own word (coalesced lines);
//     4 = every thread red.v4.f32 into its own 16 B
__global__ void kB_thru(int steps, P p) {
    const int b = blockIdx.x, t = threadIdx.x;
    unsigned *w = (unsigned *)p.buf;
    if (p.a0 == 0) { if (t == 0) for (int i = 0; i < steps; ++i) red_u32(p.ctr, 1u); }
    else if (p.a0 == 1) { if (t == 0) for (int i = 0; i < steps; ++i) red_u32(p.flags + b * 32, 1u); }
    else if (p.a0 == 2) { for (int i = 0; i < steps; ++i) red_u32(p.ctr, 1u); }
    else if (p.a0 == 3) { for (int i = 0; i < steps; ++i) red_u32(w + b * NT + t, 1u); }
    else { for (int i = 0; i < steps; ++i) red_v4(p.buf + (b * NT + t) * 4, make_float4(1, 1, 1, 1)); }
    __threadfence();
}
// single thread, 64 lines 64 KiB apart (spread over L2 slices): dependent chains of R ops
__global__ void kB_lat(int R, P p) {
    if (threadIdx.x) return;
    unsigned *w = (unsigned *)p.buf;
    p.stat[300] = smid();
    for (int li = 0; li < 64; ++li) {
        unsigned *a = w + li * 16384;
        unsigned v = 0; u64 c0 = clock64();
        for (int i = 0; i < R; ++i) v = atomicAdd(a + (v >> 31), 0u);
        u64 c1 = clock64();
        for (int i = 0; i < R; ++i) v = ld_cg(a + (v >> 31));
        u64 c2 = clock64();
        for (int i = 0; i < R; ++i) v = ld_acq(a + (v >> 31));
        u64 c3 = clock64();
        for (int i = 0; i < R; ++i) v = ld_vol(a + (v >> 31));
        u64 c4 = clock64();
        p.stat[li] = (c1 - c0) / R; p.stat[64 + li] = (c2 - c1) / R; p.stat[128 + li] = (c3 - c2) / R; p.stat[192 + li] = (c4 - c3) / R;
        if (v == 12345) p.err[0] = v;
    }
}
// ================================================================ C. one-way components
// single-thread cost per iteration: a0 = 0 st+membar.gl, 1 st.release.gpu, 2 membar.gl alone,
// 3 st.volatile alone, 4 fence.acq_rel.gpu alone, 5 red+membar.gl, 6 fence.acq_rel after st
__global__ void kC_fence(int R, P p) {
    if (threadIdx.x) return;
    unsigned *f = p.flags;
    u64 c0 = clock64();
    for (int i = 0; i < R; ++i) {
        switch (p.a0) {
            case 0: st_vol(f, i); __threadfence(); break;
            case 1: st_rel(f, i); break;
            case 2: __threadfence(); break;
            case 3: st_vol(f, i); break;
            case 4: asm volatile("fence.acq_rel.gpu;" ::: "memory"); break;
            case 5: red_u32(f, 1u); __threadfence(); break;
            default: st_vol(f, i); asm volatile("fence.acq_rel.gpu;" ::: "memory"); break;
        }
    }
    p.stat[p.a0] = (clock64() - c0) / R;
}
// ping-pong between block 0 and block a0 through flag line a1 (thread 0 of each).
// MODE 0 st.volatile+__threadfence / ld.volatile; 1 st.release / ld.acquire; 2 st.volatile /
// ld.volatile (no fence: the flag-in-data minimum); 3 st.relaxed / ld.relaxed with a2 cycles
// of delay between polls; 4 = MODE 1 plus a data line written before the release and read with
// ld.cg after the acquire (cycles of that read -> stat[2]; a line not written -> stat[3]).
// Blocks 2 .. 2+a3-1 (a3 > 0) hammer the flag line with ld.volatile; a3 < 0: hammer another line.
template <int MODE> __global__ void kC_pp(int steps, P p) {
    const int b = blockIdx.x, partner = p.a0;
    unsigned *flag = p.flags + p.a1 * 32;
    const int np = abs(p.a3);
    if (b != 0 && b != partner) {
        if (b >= 2 && b < 2 + np && b != partner && threadIdx.x < 32) {   // one warp polls (one request per poll)
            const unsigned *tgt = p.a3 > 0 ? flag : p.flags + 200 * 32;
            unsigned x = 0; while (ld_vol(p.stop) == 0) x += ld_vol(tgt + (threadIdx.x & 0));
            if (x == 0xdeadbeef) p.err[0] = x;
        }
        return;
    }
    if (threadIdx.x) return;
    const unsigned me = b == 0 ? 0 : 1;
    unsigned *data = p.flags + 100 * 32, *cold = p.flags + 150 * 32;
    u64 c0 = clock64(), rd = 0, rc = 0;
    for (int s = 0; s < steps; ++s) {
        const unsigned want = 2u * s + me;
        if (MODE == 0 || MODE == 2) SPINCHK(ld_vol(flag) != want)
        else if (MODE == 1 || MODE == 4) SPINCHK(ld_acq(flag) != want)
        else { unsigned sp = 0; while (ld_rlx(flag) != want) { u64 d0 = clock64(); while (clock64() - d0 < (u64)p.a2) { } if (++sp > SPIN) { atomicExch(p.tmo, 1u); break; } } }
        if (MODE == 4) {
            u64 d0 = clock64(), d1, d2; unsigned v = ld_cg(data);
            asm volatile("{\n .reg .pred q;\n setp.eq.u32 q, %1, 0xdeadbeef;\n @q trap;\n mov.u64 %0, %%clock64;\n}" : "=l"(d1) : "r"(v) : "memory");
            unsigned c = ld_cg(cold + (v >> 31));
            asm volatile("{\n .reg .pred q;\n setp.eq.u32 q, %1, 0xdeadbeef;\n @q trap;\n mov.u64 %0, %%clock64;\n}" : "=l"(d2) : "r"(c) : "memory");
            rd += d1 - d0; rc += d2 - d1;
            if (s > 0 && v != want - 1) atomicAdd(p.err, 1u);
            st_vol(data, want);
        }
        if (MODE == 0) { __threadfence(); st_vol(flag, want + 1); }
        else if (MODE == 1 || MODE == 4) st_rel(flag, want + 1);
        else if (MODE == 2) st_vol(flag, want + 1);
        else st_rlx(flag, want + 1);
    }
    if (b == 0) { p.stat[0] += clock64() - c0; p.stat[1] += steps; p.stat[4] = smid(); st_vol(p.stop, 1u); }
    else p.stat[5] = smid();
    if (MODE == 4) { atomicAdd(&p.stat[2], rd); atomicAdd(&p.stat[3], rc); atomicAdd(&p.stat[6], (u64)steps); }
}
// ================================================================ D. L2 hot spot
// every block: a1 warps each run a dependent chain of 128 B loads (one request per load) on
// a0 = 0 the same line for all SMs, 1 one of 8 replicas (b % 8), 2 a private line per SM.
__global__ void kD_hot(int steps, P p) {
    const int b = blockIdx.x, w = threadIdx.x >> 5, lane = threadIdx.x & 31;
    if (w >= p.a1) return;
    const unsigned *base = (const unsigned *)p.buf;
    const int line = p.a0 == 0 ? 0 : p.a0 == 1 ? (b % 8) : b;
    const unsigned *a = base + line * 32 * 33 + lane;   // lines 33*128 B apart
    unsigned v = 0; u64 c0 = clock64();
    for (int i = 0; i < steps; ++i) v = ld_cg(a + (v >> 31));
    u64 c = clock64() - c0;
    if (lane == 0) { atomicAdd(&p.stat[0], c); atomicAdd(&p.stat[1], (u64)steps); }
    if (v == 12345) p.err[0] = v;
}
// ================================================================ E. request counting
// stat: [0] counter poll iterations (thread 0), [1..3] LL8 rounds sum / 16 B loads / max rounds,
// [4..6] LL16x8 same, [7..9] flags rounds sum / flag loads / max rounds
__global__ void kE_counter(int steps, P p) {
    const int nb = gridDim.x, b = blockIdx.x, lo = slo(b, nb), hi = slo(b + 1, nb), t = threadIdx.x;
    unsigned bad = 0; u64 polls = 0;
    for (int s = 1; s <= steps; ++s) {
        float *v = p.buf + (s & 1) * V;
        if (lo + t < hi) v[lo + t] = fval(s, lo + t);
        __syncthreads();
        if (t == 0) { __threadfence(); atomicAdd(p.ctr, 1u); unsigned sp = 0; while (atomicAdd(p.ctr, 0u) < nb * (unsigned)s) { ++polls; if (++sp > SPIN) { atomicExch(p.tmo, 1u); break; } } ++polls; __threadfence(); }
        __syncthreads();
        for (int m = 0; m < 4; ++m) { int q = t + NT * m; float4 x = __ldcg((const float4 *)v + q); bad += (x.x != fval(s, 4 * q)) + (x.w != fval(s, 4 * q + 3)); }
        __syncthreads();
    }
    if (bad) atomicAdd(p.err, bad);
    if (t == 0) atomicAdd(&p.stat[0], polls);
}
__global__ void kE_ll8(int steps, P p) {
    const int nb = gridDim.x, b = blockIdx.x, lo = slo(b, nb), hi = slo(b + 1, nb), t = threadIdx.x;
    unsigned bad = 0; u64 rounds = 0, loads = 0, mx = 0;
    for (int s = 1; s <= steps; ++s) {
        uint2 *L = p.ll8 + (s & 1) * V;
        if (lo + t < hi) st_vol_v2(L + lo + t, make_uint2(__float_as_uint(fval(s, lo + t)), (unsigned)s));
        uint4 r[8]; unsigned need = 0xFF, sp = 0; u64 rr = 0;
        while (need) {
            ++rr; loads += __popc(need);
#pragma unroll
            for (int m = 0; m < 8; ++m) if (need >> m & 1) r[m] = ld_vol_v4((const uint4 *)L + t + NT * m);
#pragma unroll
            for (int m = 0; m < 8; ++m) if ((need >> m & 1) && r[m].y == (unsigned)s && r[m].w == (unsigned)s) need &= ~(1u << m);
            if (++sp > SPIN) { atomicExch(p.tmo, 1u); break; }
        }
        rounds += rr; mx = max(mx, rr);
#pragma unroll
        for (int m = 0; m < 8; ++m) { int i = 2 * (t + NT * m); bad += (__uint_as_float(r[m].x) != fval(s, i)) + (__uint_as_float(r[m].z) != fval(s, i + 1)); }
        __syncthreads();
    }
    if (bad) atomicAdd(p.err, bad);
    atomicAdd(&p.stat[1], rounds); atomicAdd(&p.stat[2], loads); atomicMax(&p.stat[3], mx);
}
// LL16 with 8 replicas: producer b writes its 128 B line into 8 copies, consumer reads copy b % 8
__global__ void kE_ll16(int steps, P p) {
    const int nb = gridDim.x, b = blockIdx.x, t = threadIdx.x, R = 8, LS = 256 * 8;
    unsigned bad = 0; u64 rounds = 0, loads = 0, mx = 0;
    for (int s = 1; s <= steps; ++s) {
        uint4 *L0 = p.ll16 + (s & 1) * R * LS, *L = L0 + (b % R) * LS;
        if (t < 8 * R) {
            int c = t >> 3, k = t & 7, lo = slo(b, nb), hi = slo(b + 1, nb), i = lo + 3 * k;
            float x0 = i < hi ? fval(s, i) : 0.f, x1 = i + 1 < hi ? fval(s, i + 1) : 0.f, x2 = i + 2 < hi ? fval(s, i + 2) : 0.f;
            st_vol_v4(L0 + c * LS + b * 8 + k, make_uint4(__float_as_uint(x0), __float_as_uint(x1), __float_as_uint(x2), (unsigned)s));
        }
        uint4 r[6]; unsigned need = 0, sp = 0; u64 rr = 0;
        for (int m = 0; m < 6; ++m) { r[m] = make_uint4(0, 0, 0, 0); if (t + NT * m < nb * 8) need |= 1u << m; }
        while (need) {
            ++rr; loads += __popc(need);
#pragma unroll
            for (int m = 0; m < 6; ++m) if (need >> m & 1) r[m] = ld_vol_v4(L + t + NT * m);
#pragma unroll
            for (int m = 0; m < 6; ++m) if ((need >> m & 1) && r[m].w == (unsigned)s) need &= ~(1u << m);
            if (++sp > SPIN) { atomicExch(p.tmo, 1u); break; }
        }
        rounds += rr; mx = max(mx, rr);
        bad += (t < nb * 8) && r[0].w != (unsigned)s;
        __syncthreads();
    }
    if (bad) atomicAdd(p.err, bad);
    atomicAdd(&p.stat[4], rounds); atomicAdd(&p.stat[5], loads); atomicMax(&p.stat[6], mx);
}
// per-producer flags (3a): fence + flag; warp 0 lanes poll 6 packed flags each (volatile), fence, read data
__global__ void kE_flags(int steps, P p) {
    const int nb = gridDim.x, b = blockIdx.x, lo = slo(b, nb), hi = slo(b + 1, nb), t = threadIdx.x;
    unsigned bad = 0; u64 rounds = 0, loads = 0, mx = 0;
    for (int s = 1; s <= steps; ++s) {
        float *v = p.buf + (s & 1) * V;
        if (lo + t < hi) v[lo + t] = fval(s, lo + t);
        __syncthreads();
        if (t == 0) { __threadfence(); st_vol(p.flags + b, (unsigned)s); }
        if (t < 32) {
            unsigned need = 0, sp = 0; u64 rr = 0;
            for (int m = 0; m < 6; ++m) if (t + 32 * m < nb) need |= 1u << m;
            while (need) {
                ++rr; loads += __popc(need); unsigned f[6];
#pragma unroll
                for (int m = 0; m < 6; ++m) f[m] = (need >> m & 1) ? ld_vol(p.flags + t + 32 * m) : 0u;
#pragma unroll
                for (int m = 0; m < 6; ++m) if ((need >> m & 1) && f[m] >= (unsigned)s) need &= ~(1u << m);
                if (++sp > SPIN) { atomicExch(p.tmo, 1u); break; }
            }
            asm volatile("fence.acq_rel.gpu;" ::: "memory");
            rounds += rr; mx = max(mx, rr);
        }
        __syncthreads();
        for (int m = 0; m < 4; ++m) { int q = t + NT * m; float4 x = __ldcg((const float4 *)v + q); bad += (x.x != fval(s, 4 * q)) + (x.w != fval(s, 4 * q + 3)); }
        __syncthreads();
    }
    if (bad) atomicAdd(p.err, bad);
    if (t < 32) { atomicAdd(&p.stat[7], rounds); atomicAdd(&p.stat[8], loads); atomicMax(&p.stat[9], mx); }
}
// ================================================================ F. all-reduce
// red phase alone: every thread 4 red.v4 per step into a0 = 0 the shared 4096 floats (all 188
// SMs hit the same 128 lines) or 1 a private 4096-float region per SM; fence; no inter-SM sync.
__global__ void kF_red(int steps, P p) {
    const int b = blockIdx.x, t = threadIdx.x;
    float *A = p.a0 == 0 ? p.acc : p.buf + (size_t)b * V;
    for (int s = 0; s < steps; ++s) {
#pragma unroll
        for (int m = 0; m < 4; ++m) red_v4(A + 4 * (t + NT * m), make_float4(1, 1, 1, 1));
        __syncthreads();
        if (t == 0) __threadfence();
        __syncthreads();
    }
}
// Design 5a with per-phase cycles (thread 0): [10] zero + red issue, [11] fence (waits until this
// SM's reds are performed at L2), [12] arrive + wait for all SMs, [13] 16 KiB readback.
__global__ void kF_ar(int steps, P p) {
    const int nb = gridDim.x, b = blockIdx.x, lo = slo(b, nb), hi = slo(b + 1, nb), t = threadIdx.x;
    const int S0 = (nb / 4) * 6 + ((nb & 3) > 1 ? 1 : 0) + ((nb & 3) > 2 ? 2 : 0);
    unsigned bad = 0; u64 ph[4] = {0, 0, 0, 0};
    for (int s = 1; s <= steps; ++s) {
        __syncthreads();
        u64 c0 = clock64();
        float *A = p.acc + (s % 3) * V, *Z = p.acc + ((s + 1) % 3) * V;
        if (lo + t < hi) Z[lo + t] = 0.f;
#pragma unroll
        for (int m = 0; m < 4; ++m) { int i = 4 * (t + NT * m); float4 v; v.x = (b & 3) + ((i + s) & 3); v.y = (b & 3) + ((i + 1 + s) & 3); v.z = (b & 3) + ((i + 2 + s) & 3); v.w = (b & 3) + ((i + 3 + s) & 3); red_v4(A + i, v); }
        __syncthreads();
        u64 c1 = clock64(), c2 = c1;
        if (t == 0) { __threadfence(); c2 = clock64(); atomicAdd(p.ctr, 1u); SPINCHK(atomicAdd(p.ctr, 0u) < nb * (unsigned)s); __threadfence(); }
        __syncthreads();
        u64 c3 = clock64();
#pragma unroll
        for (int m = 0; m < 4; ++m) { int i = 4 * (t + NT * m); float4 x = __ldcg((const float4 *)(A + i)); bad += (x.x != (float)(S0 + nb * ((i + s) & 3))) + (x.w != (float)(S0 + nb * ((i + 3 + s) & 3))); }
        __syncthreads();
        u64 c4 = clock64();
        ph[0] += c1 - c0; ph[1] += c2 - c1; ph[2] += c3 - c2; ph[3] += c4 - c3;
    }
    if (bad) atomicAdd(p.err, bad);
    if (t == 0) for (int k = 0; k < 4; ++k) atomicAdd(&p.stat[10 + k], ph[k]);
}
// explicit reduce-scatter + all-gather with two counter barriers; per-phase cycles (thread 0):
// [20] write my 4096-float partial, [21] barrier 1, [22] read my ~22-float slice of all 188
// partials + sum, [23] write my reduced slice, [24] barrier 2, [25] 16 KiB all-gather read.
__global__ void kF_rsag(int steps, P p) {
    __shared__ float part[8][32];
    const int nb = gridDim.x, b = blockIdx.x, lo = slo(b, nb), hi = slo(b + 1, nb), n = hi - lo, t = threadIdx.x;
    const int S0 = (nb / 4) * 6 + ((nb & 3) > 1 ? 1 : 0) + ((nb & 3) > 2 ? 2 : 0);
    float *G = p.acc;                                      // 2 parities x V
    unsigned bad = 0; u64 ph[6] = {0, 0, 0, 0, 0, 0};
    for (int s = 1; s <= steps; ++s) {
        float *Pb = p.buf + (size_t)(s & 1) * nb * V;      // partials [nb][V]
        __syncthreads();
        u64 c0 = clock64();
#pragma unroll
        for (int m = 0; m < 4; ++m) { int i = 4 * (t + NT * m); float4 v; v.x = (b & 3) + ((i + s) & 3); v.y = (b & 3) + ((i + 1 + s) & 3); v.z = (b & 3) + ((i + 2 + s) & 3); v.w = (b & 3) + ((i + 3 + s) & 3); __stcg((float4 *)(Pb + (size_t)b * V + i), v); }
        __syncthreads();
        u64 c1 = clock64();
        if (t == 0) { __threadfence(); atomicAdd(p.ctr, 1u); SPINCHK(atomicAdd(p.ctr, 0u) < nb * (2u * s - 1)); __threadfence(); }
        __syncthreads();
        u64 c2 = clock64();
        {   // warp w reads producers q = w, w+8, ...: lanes 0..n-1 read the slice (1-2 lines per producer)
            const int w = t >> 5, lane = t & 31; float x = 0;
            if (lane < n) {
                float xs[24];
#pragma unroll
                for (int j = 0; j < 24; ++j) { int q = w + 8 * j; xs[j] = q < nb ? __ldcg(Pb + (size_t)q * V + lo + lane) : 0.f; }
#pragma unroll
                for (int j = 0; j < 24; ++j) x += xs[j];
            }
            part[w][lane] = x;
        }
        __syncthreads();
        float y = 0; if (t < n) for (int q = 0; q < 8; ++q) y += part[q][t];
        u64 c3 = clock64();
        if (t < n) __stcg(G + (s & 1) * V + lo + t, y);
        __syncthreads();
        u64 c4 = clock64();
        if (t == 0) { __threadfence(); atomicAdd(p.ctr, 1u); SPINCHK(atomicAdd(p.ctr, 0u) < nb * (2u * s)); __threadfence(); }
        __syncthreads();
        u64 c5 = clock64();
#pragma unroll
        for (int m = 0; m < 4; ++m) { int i = 4 * (t + NT * m); float4 x = __ldcg((const float4 *)(G + (s & 1) * V + i)); bad += (x.x != (float)(S0 + nb * ((i + s) & 3))) + (x.w != (float)(S0 + nb * ((i + 3 + s) & 3))); }
        __syncthreads();
        u64 c6 = clock64();
        ph[0] += c1 - c0; ph[1] += c2 - c1; ph[2] += c3 - c2; ph[3] += c4 - c3; ph[4] += c5 - c4; ph[5] += c6 - c5;
    }
    if (bad) atomicAdd(p.err, bad);
    if (t == 0) for (int k = 0; k < 6; ++k) atomicAdd(&p.stat[20 + k], ph[k]);
}
// ================================================================ G. DSMEM (cluster of 8)
__global__ void kG_sync(int steps, P p) { cg::cluster_group c = cg::this_cluster(); for (int s = 0; s < steps; ++s) c.sync(); }
// rank 0 thread 0: dependent chains -- remote ld.shared::cluster (rank 1), local ld.shared, L2 ld.cg
__global__ void kG_lat(int R, P p) {
    __shared__ unsigned sm[1024];
    cg::cluster_group c = cg::this_cluster();
    for (int i = threadIdx.x; i < 1024; i += NT) sm[i] = 0;
    c.sync();
    if (c.block_rank() == 0 && threadIdx.x == 0 && blockIdx.x == 0) {
        unsigned ra; asm volatile("mapa.shared::cluster.u32 %0, %1, %2;" : "=r"(ra) : "r"(smem_u32(sm)), "r"(1));
        unsigned la = smem_u32(sm), v = 0;
        u64 c0 = clock64();
        for (int i = 0; i < R; ++i) asm volatile("ld.shared::cluster.u32 %0, [%1];" : "=r"(v) : "r"(ra + (v >> 31)) : "memory");
        u64 c1 = clock64();
        for (int i = 0; i < R; ++i) asm volatile("ld.shared.u32 %0, [%1];" : "=r"(v) : "r"(la + (v >> 31)) : "memory");
        u64 c2 = clock64();
        for (int i = 0; i < R; ++i) v = ld_cg(p.flags + (v >> 31));
        u64 c3 = clock64();
        p.stat[30] = (c1 - c0) / R; p.stat[31] = (c2 - c1) / R; p.stat[32] = (c3 - c2) / R;
        if (v == 12345) p.err[0] = v;
    }
    c.sync();
}
// 16 KiB per step per block, a1 warps active, a0: 0 DSMEM from rank+1, 1 local smem, 2 L2 private copy
template <int SRC> __global__ void kG_bw(int steps, P p) {
    __shared__ float4 buf[V / 4];
    cg::cluster_group c = cg::this_cluster();
    const int t = threadIdx.x, rk = c.block_rank(), cs = c.num_blocks();
    for (int i = t; i < V / 4; i += NT) buf[i] = make_float4(1, 1, 1, 1);
    c.sync();
    unsigned ra; asm volatile("mapa.shared::cluster.u32 %0, %1, %2;" : "=r"(ra) : "r"(smem_u32(buf)), "r"((rk + 1) % cs));
    const unsigned la = smem_u32(buf);
    const float4 *g = (const float4 *)(p.buf + (size_t)blockIdx.x * V);
    const int nthr = 32 * p.a1, per = (V / 4) / nthr;          // float4 per active thread
    float acc = 0;
    if (t < nthr) {
        for (int s = 0; s < steps; ++s) {
            for (int j0 = 0; j0 < per; j0 += 4) {
                float4 x[4];
#pragma unroll
                for (int j = 0; j < 4; ++j) {
                    int q = t + nthr * (j0 + j);
                    if (SRC == 0) asm volatile("ld.shared::cluster.v4.f32 {%0,%1,%2,%3}, [%4];" : "=f"(x[j].x), "=f"(x[j].y), "=f"(x[j].z), "=f"(x[j].w) : "r"(ra + 16u * q) : "memory");
                    else if (SRC == 1) asm volatile("ld.shared.v4.f32 {%0,%1,%2,%3}, [%4];" : "=f"(x[j].x), "=f"(x[j].y), "=f"(x[j].z), "=f"(x[j].w) : "r"(la + 16u * q) : "memory");
                    else x[j] = __ldcg(g + q);
                }
#pragma unroll
                for (int j = 0; j < 4; ++j) acc += x[j].x + x[j].w;
            }
            asm volatile("bar.sync 1, %0;" :: "r"(nthr));
        }
    }
    if (acc == -1.f) p.err[0] = 1;
    c.sync();
}

// ================================================================ host
__global__ void kclock(u64 *out) {
    u64 c0 = clock64(), t0 = gtimer();
    while (gtimer() - t0 < 2000000ull) { }
    out[0] = clock64() - c0; out[1] = gtimer() - t0;
}

static cudaStream_t st;
static cudaEvent_t e0, e1;
static int TR = 11, NSM = 0;
static const int PAD = 64 << 10;
static P hp;
static void reset() {
    CK(cudaMemsetAsync(hp.ctr, 0, 256, st)); CK(cudaMemsetAsync(hp.flags, 0, 64 << 10, st)); CK(cudaMemsetAsync(hp.stop, 0, 128, st));
    CK(cudaMemsetAsync(hp.err, 0, 4, st)); CK(cudaMemsetAsync(hp.tmo, 0, 4, st)); CK(cudaMemsetAsync(hp.acc, 0, 3 * V * 4, st));
    CK(cudaMemsetAsync(hp.ll8, 0, 2 * V * 8, st)); CK(cudaMemsetAsync(hp.ll16, 0, (size_t)2 * 8 * 256 * 8 * 16, st));
}
static void reset_buf() { CK(cudaMemsetAsync(hp.buf, 0, (size_t)8 << 20, st)); }
static void reset_stat() { CK(cudaMemsetAsync(hp.stat, 0, 512 * 8, st)); }
struct R { double mn, md; unsigned err, tmo; };
static std::vector<u64> bstat(512);   // stat accumulators of the fastest trial of the last timed() call
// times kernel k over TR trials; returns ns per `per` units. cs > 0: cluster launch.
static R timed(void (*k)(int, P), int nb, int steps, double per, int cs = 0, bool rbuf = false) {
    CK(cudaFuncSetAttribute((const void *)k, cudaFuncAttributeMaxDynamicSharedMemorySize, PAD));
    std::vector<double> v; unsigned errs = 0, tmo = 0; double best = 1e30;
    for (int tr = 0; tr < TR; ++tr) {
        reset(); reset_stat(); if (rbuf) reset_buf();
        CK(cudaEventRecord(e0, st));
        if (cs) {
            cudaLaunchConfig_t cfg = {}; cfg.gridDim = nb; cfg.blockDim = NT; cfg.stream = st; cfg.dynamicSmemBytes = PAD;
            cudaLaunchAttribute at[1]; at[0].id = cudaLaunchAttributeClusterDimension; at[0].val.clusterDim.x = cs; at[0].val.clusterDim.y = 1; at[0].val.clusterDim.z = 1;
            cfg.attrs = at; cfg.numAttrs = 1;
            CK(cudaLaunchKernelEx(&cfg, k, steps, hp));
        } else {
            void *args[] = {&steps, &hp}; CK(cudaLaunchCooperativeKernel((const void *)k, nb, NT, args, PAD, st));
        }
        CK(cudaEventRecord(e1, st)); CK(cudaEventSynchronize(e1)); CK(cudaGetLastError());
        float ms; CK(cudaEventElapsedTime(&ms, e0, e1)); v.push_back(ms * 1e6 / per);
        unsigned h[2]; CK(cudaMemcpy(&h[0], hp.err, 4, cudaMemcpyDeviceToHost)); CK(cudaMemcpy(&h[1], hp.tmo, 4, cudaMemcpyDeviceToHost));
        errs += h[0]; tmo += h[1];
        if (v.back() < best) { best = v.back(); CK(cudaMemcpy(bstat.data(), hp.stat, 512 * 8, cudaMemcpyDeviceToHost)); }
    }
    std::sort(v.begin(), v.end());
    return {v.front(), v[v.size() / 2], errs, tmo};
}
static std::vector<u64> stat() { std::vector<u64> s(512); CK(cudaMemcpy(s.data(), hp.stat, 512 * 8, cudaMemcpyDeviceToHost)); return s; }
static bool first = true;
static void key(const char *k) { printf("%s\n \"%s\": ", first ? "" : ",", k); first = false; }
static void pr(const char *name, R r, bool last = false) { printf("\"%s\": {\"min_ns\": %.3f, \"median_ns\": %.3f, \"errors\": %u, \"timeouts\": %u}%s", name, r.mn, r.md, r.err, r.tmo, last ? "" : ", "); }

int main(int argc, char **argv) {
    const int N = argc > 1 ? atoi(argv[1]) : 1000; TR = argc > 2 ? atoi(argv[2]) : 11;
    cudaDeviceProp dp; CK(cudaGetDeviceProperties(&dp, 0)); NSM = dp.multiProcessorCount;
    CK(cudaStreamCreateWithFlags(&st, cudaStreamNonBlocking)); CK(cudaEventCreate(&e0)); CK(cudaEventCreate(&e1));
    CK(cudaMalloc(&hp.ctr, 256)); CK(cudaMalloc(&hp.flags, 64 << 10)); CK(cudaMalloc(&hp.stop, 128)); CK(cudaMalloc(&hp.err, 4)); CK(cudaMalloc(&hp.tmo, 4));
    CK(cudaMalloc(&hp.buf, (size_t)8 << 20)); CK(cudaMalloc(&hp.acc, 3 * V * 4)); CK(cudaMalloc(&hp.ll8, 2 * V * 8));
    CK(cudaMalloc(&hp.ll16, (size_t)2 * 8 * 256 * 8 * 16)); CK(cudaMalloc(&hp.stat, 512 * 8));
    // clock
    double ghz;
    {
        reset_stat(); kclock<<<1, 1, 0, st>>>(hp.stat); CK(cudaStreamSynchronize(st));
        auto s = stat(); ghz = (double)s[0] / (double)s[1];
    }
    printf("{\"device\": \"%s\", \"sms\": %d, \"sm_clock_ghz\": %.3f, \"steps\": %d, \"trials\": %d", dp.name, NSM, ghz, N, TR);
    first = false;

    // ---------------- A
    key("A_counter_vs_participants");
    printf("{\"cycles_per_ns\": %.3f, \"rows\": [", ghz);
    const int Ns[] = {1, 2, 4, 8, 16, 32, 64, 128, 188};
    for (int i = 0; i < 9; ++i) {
        int n = std::min(Ns[i], NSM);
        R a = timed(kA<1, true>, n, N, N), b1 = timed(kA<1, false>, n, N, N), b8 = timed(kA<8, false>, n, N, N), b32 = timed(kA<32, false>, n, N, N);
        printf("%s\n  {\"n\": %d, ", i ? "," : "", n); pr("atomic_counter", a); pr("acquire_counter", b1); pr("shards8", b8); pr("shards32", b32, true); printf("}");
    }
    printf("]}");

    // ---------------- B
    key("B_atomics");
    printf("{");
    {
        const int RR = 2000;
        hp.a0 = 0; R r0 = timed(kB_thru, NSM, RR, (double)NSM * RR); pr("same_word_1thread_per_SM_ns_per_op", r0);
        hp.a0 = 0; R r0b = timed(kB_thru, 1, RR, (double)RR); pr("same_word_single_SM_ns_per_op", r0b);
        hp.a0 = 1; R r1 = timed(kB_thru, NSM, RR, (double)NSM * RR); pr("own_line_1thread_per_SM_ns_per_op", r1);
        hp.a0 = 2; R r2 = timed(kB_thru, NSM, 200, (double)NSM * NT * 200); pr("same_word_all_threads_ns_per_op", r2);
        hp.a0 = 3; R r3 = timed(kB_thru, NSM, 200, (double)NSM * NT * 200, 0, true); pr("own_word_all_threads_ns_per_op", r3);
        hp.a0 = 4; R r4 = timed(kB_thru, NSM, 200, (double)NSM * NT * 200, 0, true); pr("own_16B_red_v4_all_threads_ns_per_op", r4);
        reset_stat(); reset_buf();
        kB_lat<<<1, 32, 0, st>>>(256, hp); CK(cudaStreamSynchronize(st)); auto s = stat();
        printf("\"latency_smid\": %llu, ", s[300]);
        const char *nm[4] = {"atomicAdd_return_cycles", "ld_cg_cycles", "ld_acquire_cycles", "ld_volatile_cycles"};
        for (int k = 0; k < 4; ++k) { printf("\"%s\": [", nm[k]); for (int li = 0; li < 64; ++li) printf("%s%llu", li ? "," : "", s[64 * k + li]); printf("]%s", k < 3 ? ", " : ""); }
    }
    printf("}");

    // ---------------- C
    key("C_one_way");
    printf("{\"single_thread_cycles_per_iteration\": {");
    {
        const char *nm[7] = {"store_then_membar_gl", "st_release_gpu", "membar_gl_alone", "store_alone", "fence_acq_rel_alone", "red_then_membar_gl", "store_then_fence_acq_rel"};
        for (int m = 0; m < 7; ++m) { reset_stat(); hp.a0 = m; kC_fence<<<1, 32, 0, st>>>(2000, hp); CK(cudaStreamSynchronize(st)); auto s = stat(); printf("%s\"%s\": %llu", m ? ", " : "", nm[m], s[m]); }
    }
    printf("}, \"pingpong\": [");
    auto pp = [&](const char *name, void (*k)(int, P), int partner, int line, int delay, int pollers, bool comma) {
        hp.a0 = partner; hp.a1 = line; hp.a2 = delay; hp.a3 = pollers;
        R r = timed(k, NSM, N, 2.0 * N); auto s = bstat;
        double oneway_cyc = (double)s[0] / (double)s[1] / 2.0;
        printf("%s\n  {\"mode\": \"%s\", \"partner_block\": %d, \"flag_line\": %d, \"poll_delay_cycles\": %d, \"hammer_pollers\": %d, \"smid_a\": %llu, \"smid_b\": %llu, ", comma ? "," : "", name, partner, line, delay, pollers, s[4], s[5]);
        pr("oneway", r); printf("\"oneway_cycles_in_kernel\": %.0f", oneway_cyc);
        if (s[6]) printf(", \"fresh_line_ldcg_cycles\": %.0f, \"untouched_line_ldcg_cycles\": %.0f", (double)s[2] / s[6], (double)s[3] / s[6]);
        printf("}");
    };
    bool cm = false;
    for (int line = 0; line < 8; ++line) { pp("vol_fence", kC_pp<0>, 1, line * 7 + 1, 0, 0, cm); cm = true; }
    for (int line = 0; line < 8; ++line) pp("rel_acq", kC_pp<1>, 1, line * 7 + 1, 0, 0, true);
    for (int line = 0; line < 8; ++line) pp("vol_nofence", kC_pp<2>, 1, line * 7 + 1, 0, 0, true);
    for (int pt : {47, 94, 187}) pp("rel_acq", kC_pp<1>, pt, 1, 0, 0, true);
    for (int d : {0, 200, 500, 1000, 2000, 4000}) pp("relaxed_poll_delay", kC_pp<3>, 1, 1, d, 0, true);
    for (int np : {16, 64, 186}) { pp("vol_nofence", kC_pp<2>, 1, 1, 0, np, true); pp("vol_nofence", kC_pp<2>, 1, 1, 0, -np, true); }
    for (int line = 0; line < 4; ++line) pp("rel_acq_with_data", kC_pp<4>, 1, line * 7 + 1, 0, 0, true);
    printf("]}");

    // ---------------- D
    key("D_hot_line");
    printf("[");
    {
        const char *nm[3] = {"same_line", "8_replicas", "private_lines"};
        bool c = false;
        for (int w : {1, 8}) for (int m = 0; m < 3; ++m) {
            hp.a0 = m; hp.a1 = w;
            R r = timed(kD_hot, NSM, N, N, 0, true); auto s = bstat;
            double cyc = (double)s[0] / s[1];
            printf("%s\n  {\"pattern\": \"%s\", \"warps_per_SM\": %d, \"requests_in_flight\": %d, ", c ? "," : "", nm[m], w, NSM * w);
            pr("per_dependent_load", r); printf("\"cycles_per_load_in_kernel\": %.0f, \"requests_per_ns\": %.2f}", cyc, NSM * w / (cyc / ghz));
            c = true;
        }
    }
    printf("]");

    // ---------------- E
    key("E_request_counts");
    {
        std::vector<u64> s(512);
        R rc = timed(kE_counter, NSM, N, N); s[0] = bstat[0];
        R rl8 = timed(kE_ll8, NSM, N, N); for (int k = 1; k <= 3; ++k) s[k] = bstat[k];
        R rl16 = timed(kE_ll16, NSM, N, N); for (int k = 4; k <= 6; ++k) s[k] = bstat[k];
        R rf = timed(kE_flags, NSM, N, N); for (int k = 7; k <= 9; ++k) s[k] = bstat[k];
        const double bs = (double)N * NSM;   // block-steps of one trial
        printf("{\"counter\": {\"ns\": %.1f, \"errors\": %u, \"counter_polls_per_SM_per_boundary\": %.2f, \"data_bytes_per_SM\": %d},\n", rc.mn, rc.err, s[0] / bs, V * 4);
        printf("  \"ll8\": {\"ns\": %.1f, \"errors\": %u, \"poll_rounds_per_thread_mean\": %.2f, \"poll_rounds_max\": %llu, \"loads_16B_per_SM\": %.1f, \"bytes_per_SM\": %.0f, \"useful_bytes_per_SM\": %d},\n",
               rl8.mn, rl8.err, s[1] / (bs * NT), s[3], s[2] / bs, s[2] / bs * 16, V * 4);
        printf("  \"ll16_rep8\": {\"ns\": %.1f, \"errors\": %u, \"poll_rounds_per_thread_mean\": %.2f, \"poll_rounds_max\": %llu, \"loads_16B_per_SM\": %.1f, \"bytes_per_SM\": %.0f, \"useful_bytes_per_SM\": %d},\n",
               rl16.mn, rl16.err, s[4] / (bs * NT), s[6], s[5] / bs, s[5] / bs * 16, V * 4);
        printf("  \"flags\": {\"ns\": %.1f, \"errors\": %u, \"poll_rounds_per_lane_mean\": %.2f, \"poll_rounds_max\": %llu, \"flag_loads_per_SM\": %.1f, \"flag_lines_per_round\": 6, \"data_bytes_per_SM\": %d}}",
               rf.mn, rf.err, s[7] / (bs * 32), s[9], s[8] / bs, V * 4);
    }

    // ---------------- F
    key("F_allreduce");
    {
        hp.a0 = 0; R rs = timed(kF_red, NSM, N, N); hp.a0 = 1; R rp = timed(kF_red, NSM, N, N, 0, true);
        printf("{"); pr("red_phase_shared_target_ns_per_step", rs); pr("red_phase_private_target_ns_per_step", rp);
        printf("\"bytes_per_step\": %d, ", NSM * V * 4);
        R ra = timed(kF_ar, NSM, N, N); auto s = bstat; double bs = (double)N * NSM;
        pr("allreduce_red_total", ra);
        printf("\"allreduce_red_phases_ns\": {\"zero_and_red_issue\": %.1f, \"fence_wait_own_reds\": %.1f, \"arrive_and_wait_all\": %.1f, \"readback_16KiB\": %.1f}, ",
               s[10] / bs / ghz, s[11] / bs / ghz, s[12] / bs / ghz, s[13] / bs / ghz);
        R rr = timed(kF_rsag, NSM, N, N, 0, true); s = bstat;
        pr("rs_ag_total", rr);
        printf("\"rs_ag_phases_ns\": {\"write_partial_16KiB\": %.1f, \"barrier1\": %.1f, \"read_188_slices_and_sum\": %.1f, \"write_slice\": %.1f, \"barrier2\": %.1f, \"allgather_read_16KiB\": %.1f}}",
               s[20] / bs / ghz, s[21] / bs / ghz, s[22] / bs / ghz, s[23] / bs / ghz, s[24] / bs / ghz, s[25] / bs / ghz);
    }

    // ---------------- G
    key("G_dsmem");
    {
        const int CS = 8, nbc = 176;
        printf("{"); R rsync = timed(kG_sync, nbc, N, N, CS); pr("cluster8_sync", rsync);
        reset_stat();
        {
            cudaLaunchConfig_t cfg = {}; cfg.gridDim = CS; cfg.blockDim = NT; cfg.stream = st;
            cudaLaunchAttribute at[1]; at[0].id = cudaLaunchAttributeClusterDimension; at[0].val.clusterDim.x = CS; at[0].val.clusterDim.y = 1; at[0].val.clusterDim.z = 1;
            cfg.attrs = at; cfg.numAttrs = 1; int R0 = 1000;
            CK(cudaLaunchKernelEx(&cfg, kG_lat, R0, hp)); CK(cudaStreamSynchronize(st));
        }
        auto s = stat();
        printf("\"remote_ld_shared_cluster_cycles\": %llu, \"local_ld_shared_cycles\": %llu, \"l2_ld_cg_cycles\": %llu, \"bandwidth\": [", s[30], s[31], s[32]);
        const char *nm[3] = {"dsmem_peer", "local_smem", "l2_private_copy"};
        bool c = false;
        for (int w : {1, 8}) for (int m = 0; m < 3; ++m) {
            hp.a0 = m; hp.a1 = w; R r = timed(m == 0 ? kG_bw<0> : m == 1 ? kG_bw<1> : kG_bw<2>, nbc, N, N, CS);
            printf("%s\n  {\"source\": \"%s\", \"warps\": %d, \"ns_per_16KiB\": %.1f, \"median_ns\": %.1f, \"bytes_per_ns_per_SM\": %.2f, \"bytes_per_cycle_per_SM\": %.2f}", c ? "," : "", nm[m], w, r.mn, r.md, 16384.0 / r.mn, 16384.0 / (r.mn * ghz));
            c = true;
        }
        printf("]}");
    }
    printf("\n}\n");
    return 0;
}
