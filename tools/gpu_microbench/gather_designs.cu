// gather_designs.cu -- can the all-SM "gather" dependency of a megakernel decode be made
// cheaper than the 663 ns single-counter barrier measured by dep_latency.cu, and does it
// matter once the weight stream is overlapped? Results: results/gpu/blackwell_gather_designs.json
//
// Micro designs (1-5): a persistent kernel, one 256-thread block per SM (64 KiB of dynamic
// shared memory forces exactly one), runs `steps` dependent boundaries. At each boundary every
// SM produces a slice of the activation vector (4096 fp32 = 16 KiB, ~22 words per SM on 188 SMs;
// -DVW=2048 gives the same hidden size as bf16 pairs, 8 KiB) and every SM must then hold the
// WHOLE vector before it produces the next slice. Consumers CHECK every element of every step
// (values encode the step), so a design that is fast because it reads stale or torn data shows
// up in data_errors. ns/boundary = kernel time / steps; min and median over trials. Trials are
// short (500 steps, ~1 ms) because the GPU is time-sliced with another tenant.
//
//   1a counter_only        single atomic counter arrive + poll, no data (dep_latency.cu, 663 ns)
//   1b counter_data        1a + every SM reads the vector from L2 (ld.cg)
//   1c/1d counter_rep      1b with the vector written to 8/16 replicas (SM b reads copy b % R):
//                          spreads the 188-reader hot lines over more L2 slices
//   2a ll8                 flag-in-data, 8 B {word, tag} stores; consumers poll the data itself
//   2b ll16                flag-in-data, 16 B {3 words, tag}; one 128 B line per producer
//   2c ll128               NCCL LL128 layout: one 128 B line per producer written by one warp
//                          store, tag in the last 8 B (relies on 128 B store atomicity, which
//                          PTX does not promise -- tearing would show as data_errors)
//   2d/2e ll16_rep         2b with 8/16 replicas;  2f ll16_light: poll one entry per line first
//   2x/2y read_*_nodep     no dependency: re-read a ready vector (the data-movement floor)
//   3a/3b/3c flags         per-producer flag after __threadfence; warp polls packed flags,
//                          warp polls 128 B-padded flags, one thread per flag
//   3d sharded<K>_rep<R>   K counter shards (arrival serialisation / K), ld.acquire polls,
//                          R data replicas. K = 1, R = 8 is the best fp32/bf16 plain design.
//   4a cluster{8,16}_flags slice -> cluster.sync -> leader fence + per-cluster flag -> all poll
//   4b cluster8_ll16_dsmem each member polls 1/8 of the LL16 lines and pushes them to all 8
//                          members over DSMEM, then cluster.sync (8x less L2 read traffic)
//   4x cluster8_sync_only  reference: cluster.sync + 16 KiB DSMEM read from a peer (no global)
//   5a allreduce_red       Megatron row-parallel output: every SM red.add.v4.f32 its full
//                          partial into L2, counter barrier, every SM reads the sum
//   5b allreduce_cluster8  DSMEM reduce-scatter inside the 8-SM cluster, then red.add + barrier
//   5c allreduce_ll16      LL16 reduce-scatter + LL16 all-gather (two hops, no fence/atomics)
//
// GEMV chain (6): Qwen3-8B 4096x4096 bf16 GEMVs, fp32 activations, one block per SM, weights
// streamed from a 512 MiB buffer (16 matrices, 4x the 128 MiB L2, so every byte is DRAM) into a
// ring of 8 KiB rows by TMA (cp.async.bulk + mbarrier) or per-thread cp.async; exposed cost per
// boundary = t(dependent chain) - t(stream-only, same kernel structure), per GEMV:
//   static tiles (SM b owns rows [b*4096/188, (b+1)*4096/188)): counter / counter_rep8 / LL8
//     gather, the ring either continues into the next GEMV's tile across the boundary
//     (overlap) or is drained (drain); ring of 8 or 12 rows
//   dyn: rows claimed from a per-GEMV atomic counter as ring slots free up (claims run ahead
//     into the next GEMV), each finished row writes an LL8 {y, tag} entry, the gather polls
//     all 4096 entries -- no barrier, no drain, no static-tile straggler
// Every GEMV output is checked on 256 rows against a double-precision host reference.
//
// First-principles checks printed with the results: SM clock (clock64 vs %globaltimer),
// single-thread L2 hit latency (256 KiB pointer chase), achieved DRAM read bandwidth.
// Build: /usr/local/cuda-12.8/bin/nvcc -O3 -arch=sm_120 -rdc=true gather_designs.cu -o gather_designs
//        (add -DVW=2048 for the bf16-width vector; -DLDPOLL=1|2 polls with ld.relaxed.gpu|ld.cg)
// Run:   ./gather_designs [steps=4000] [trials=11] [gemv_steps=64] [nmat=16] [name-filter|gemv]
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <cmath>
#include <vector>
#include <string>
#include <algorithm>
#include <cuda_runtime.h>
#include <cooperative_groups.h>
namespace cg = cooperative_groups;
#define CK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { fprintf(stderr, "%s:%d %s\n", __FILE__, __LINE__, cudaGetErrorString(e_)); exit(1); } } while (0)

#ifndef VW
#define VW 4096
#endif
// activation vector in 32-bit words: 4096 = Qwen3-8B hidden in fp32 (16 KiB); build with
// -DVW=2048 for the same hidden size carried as bf16 pairs (8 KiB). The GEMV chain needs 4096.
constexpr int V = VW;
constexpr int NT = 256;          // threads per block
constexpr unsigned SPIN_LIMIT = 1u << 22;

// ---------------------------------------------------------------- PTX helpers
__device__ __forceinline__ unsigned long long gtimer() { unsigned long long t; asm volatile("mov.u64 %0, %%globaltimer;" : "=l"(t)); return t; }
__device__ __forceinline__ unsigned ld_acquire(const unsigned *p) { unsigned v; asm volatile("ld.acquire.gpu.global.u32 %0, [%1];" : "=r"(v) : "l"(p) : "memory"); return v; }
__device__ __forceinline__ unsigned ld_vol(const unsigned *p) { unsigned v; asm volatile("ld.volatile.global.u32 %0, [%1];" : "=r"(v) : "l"(p) : "memory"); return v; }
__device__ __forceinline__ void st_vol(unsigned *p, unsigned v) { asm volatile("st.volatile.global.u32 [%0], %1;" :: "l"(p), "r"(v) : "memory"); }
// poll load of a 16 B tagged entry: -DLDPOLL=0 ld.volatile (default), 1 ld.relaxed.gpu, 2 ld.global.cg
#if LDPOLL == 1
#define LDPOLL_INS "ld.relaxed.gpu.global.v4.u32"
#elif LDPOLL == 2
#define LDPOLL_INS "ld.global.cg.v4.u32"
#else
#define LDPOLL_INS "ld.volatile.global.v4.u32"
#endif
__device__ __forceinline__ uint4 ld_vol_v4(const uint4 *p) { uint4 r; asm volatile(LDPOLL_INS " {%0,%1,%2,%3}, [%4];" : "=r"(r.x), "=r"(r.y), "=r"(r.z), "=r"(r.w) : "l"(p) : "memory"); return r; }
__device__ __forceinline__ void st_vol_v4(uint4 *p, uint4 v) { asm volatile("st.volatile.global.v4.u32 [%0], {%1,%2,%3,%4};" :: "l"(p), "r"(v.x), "r"(v.y), "r"(v.z), "r"(v.w) : "memory"); }
__device__ __forceinline__ void st_vol_v2(uint2 *p, uint2 v) { asm volatile("st.volatile.global.v2.u32 [%0], {%1,%2};" :: "l"(p), "r"(v.x), "r"(v.y) : "memory"); }
__device__ __forceinline__ void red_add_v4(float *p, float4 v) { asm volatile("red.relaxed.gpu.global.add.v4.f32 [%0], {%1,%2,%3,%4};" :: "l"(p), "f"(v.x), "f"(v.y), "f"(v.z), "f"(v.w) : "memory"); }
__device__ __forceinline__ void cp_async16(void *smem, const void *g) { unsigned s = (unsigned)__cvta_generic_to_shared(smem); asm volatile("cp.async.cg.shared.global [%0], [%1], 16;" :: "r"(s), "l"(g) : "memory"); }
__device__ __forceinline__ void cp_commit() { asm volatile("cp.async.commit_group;" ::: "memory"); }
template <int N> __device__ __forceinline__ void cp_wait() { asm volatile("cp.async.wait_group %0;" :: "n"(N) : "memory"); }

// counter barrier exactly as dep_latency.cu (atomic arrive, atomic poll, fences)
__device__ __forceinline__ void counter_barrier(unsigned *ctr, unsigned target, unsigned *tmo) {
    __syncthreads();
    if (threadIdx.x == 0) {
        __threadfence(); atomicAdd(ctr, 1u);
        unsigned spins = 0;
        while (atomicAdd(ctr, 0u) < target) if (++spins > SPIN_LIMIT) { atomicExch(tmo, 1u); break; }
        __threadfence();
    }
    __syncthreads();
}

// ---------------------------------------------------------------- data encodings
__host__ __device__ __forceinline__ float fval(unsigned s, unsigned i) { return (float)((s * 131u + i * 7u) & 0xFFFFu); }  // exact in fp32
__device__ __forceinline__ int slo(int b, int nb) { return (int)((unsigned)(b * V) / (unsigned)nb); }   // 32-bit: a 64-bit divide costs ~100 instructions
// all-reduce partial of block b: small integers, so the fp32 sum is exact in any order
__device__ __forceinline__ float pval(int b, unsigned s, int i) { return (float)((b & 3) + ((i + s) & 3)); }
__device__ __forceinline__ float sumval(int nb, unsigned s, int i) {
    int S0 = (nb / 4) * 6 + ((nb & 3) > 1 ? 1 : 0) + ((nb & 3) > 2 ? 2 : 0);  // sum_b (b&3)
    return (float)(S0 + nb * (int)((i + s) & 3));
}

struct P {
    unsigned *ctr, *flags, *err, *tmo;
    float *plain, *acc;
    uint2 *ll8; uint4 *ll16, *llrs;
    float *sink;
    unsigned *rowctr;         // per-GEMV row claim counters (dynamic GEMV chain)
    unsigned long long *stat; // [0]: summed boundary cycles over blocks (GEMV chain)
    int rep;                 // replicas of the gathered vector (consumer b reads copy b % rep)
    float *rplain;           // [2 parity][REPMAX][V]
    uint4 *rll16;            // [2 parity][REPMAX][NBMAX * 8]
};
constexpr int REPMAX = 192, NBMAX = 256;

// poll M 16-byte entries (e = tid + 256 m < nent) of `base` until .w == tag; all loads of
// one round are issued back to back, so a round costs one L2 round trip, not M.
template <int M> __device__ __forceinline__ void poll16(const uint4 *base, int nent, unsigned tag, uint4 (&r)[M], unsigned *tmo) {
    unsigned need = 0;
#pragma unroll
    for (int m = 0; m < M; ++m) { r[m] = make_uint4(0, 0, 0, 0); if (threadIdx.x + NT * m < nent) need |= 1u << m; }
    unsigned spins = 0;
    while (need) {
#pragma unroll
        for (int m = 0; m < M; ++m) if (need >> m & 1) r[m] = ld_vol_v4(base + threadIdx.x + NT * m);
#pragma unroll
        for (int m = 0; m < M; ++m) if ((need >> m & 1) && r[m].w == tag) need &= ~(1u << m);
        if (++spins > SPIN_LIMIT) { atomicExch(tmo, 1u); break; }
    }
}
// LL16 line of producer b: 8 entries {x[3k], x[3k+1], x[3k+2], tag}
template <typename F> __device__ __forceinline__ void produce_ll16(uint4 *lines, int b, int nb, unsigned tag, F val) {
    if (threadIdx.x < 8) {
        int k = threadIdx.x, lo = slo(b, nb), hi = slo(b + 1, nb), i = lo + 3 * k;
        float x0 = i < hi ? val(i) : 0.f, x1 = i + 1 < hi ? val(i + 1) : 0.f, x2 = i + 2 < hi ? val(i + 2) : 0.f;
        st_vol_v4(lines + b * 8 + k, make_uint4(__float_as_uint(x0), __float_as_uint(x1), __float_as_uint(x2), tag));
    }
}
// element index and count of LL16 entry e (step-invariant: computed once, outside the step loop)
__device__ __forceinline__ void ll16_map(int e, int nb, int &i, int &n) {
    int b = e >> 3, k = e & 7, lo = slo(b, nb), hi = slo(b + 1, nb); i = lo + 3 * k; n = max(0, min(3, hi - i));
}
// check (and consume) one LL16 entry holding elements i .. i+n-1
template <typename F> __device__ __forceinline__ unsigned check_ll16(uint4 r, int i, int n, F val, float &acc) {
    unsigned bad = 0; float x[3] = {__uint_as_float(r.x), __uint_as_float(r.y), __uint_as_float(r.z)};
#pragma unroll
    for (int j = 0; j < 3; ++j) if (j < n) { bad += x[j] != val(i + j); acc += x[j]; }
    return bad;
}
__device__ __forceinline__ void finish(P p, unsigned bad, float acc) {
    if (bad) atomicAdd(p.err, bad);
    if (acc == -1.f) p.sink[0] = acc;   // keep the reads live
}

// ---------------------------------------------------------------- 1. single counter
__global__ void k_counter_only(int steps, P p) {
    for (int s = 1; s <= steps; ++s) counter_barrier(p.ctr, gridDim.x * (unsigned)s, p.tmo);
}
__global__ void k_counter_data(int steps, P p) {
    const int nb = gridDim.x, b = blockIdx.x, lo = slo(b, nb), hi = slo(b + 1, nb), t = threadIdx.x;
    unsigned bad = 0; float acc = 0;
    for (int s = 1; s <= steps; ++s) {
        float *v0 = p.rplain + (size_t)(s & 1) * REPMAX * V, *v = v0 + (b % p.rep) * V;
        if (lo + t < hi) for (int c = 0; c < p.rep; ++c) v0[c * V + lo + t] = fval(s, lo + t);
        counter_barrier(p.ctr, nb * (unsigned)s, p.tmo);
#pragma unroll
        for (int m = 0; m < V / 1024; ++m) {
            int q = t + NT * m; float4 x = __ldcg((const float4 *)v + q);
            bad += (x.x != fval(s, 4 * q)) + (x.y != fval(s, 4 * q + 1)) + (x.z != fval(s, 4 * q + 2)) + (x.w != fval(s, 4 * q + 3));
            acc += x.x + x.y + x.z + x.w;
        }
        __syncthreads();
    }
    finish(p, bad, acc);
}
// ---------------------------------------------------------------- 2. flag-in-data (LL)
__global__ void k_ll8(int steps, P p) {
    const int nb = gridDim.x, b = blockIdx.x, lo = slo(b, nb), hi = slo(b + 1, nb), t = threadIdx.x;
    unsigned bad = 0; float acc = 0;
    for (int s = 1; s <= steps; ++s) {
        uint2 *L = p.ll8 + (s & 1) * V;
        if (lo + t < hi) st_vol_v2(L + lo + t, make_uint2(__float_as_uint(fval(s, lo + t)), (unsigned)s));
        uint4 r[V / 512]; unsigned need = (1u << (V / 512)) - 1, spins = 0;
        while (need) {
#pragma unroll
            for (int m = 0; m < V / 512; ++m) if (need >> m & 1) r[m] = ld_vol_v4((const uint4 *)L + t + NT * m);
#pragma unroll
            for (int m = 0; m < V / 512; ++m) if ((need >> m & 1) && r[m].y == (unsigned)s && r[m].w == (unsigned)s) need &= ~(1u << m);
            if (++spins > SPIN_LIMIT) { atomicExch(p.tmo, 1u); break; }
        }
#pragma unroll
        for (int m = 0; m < V / 512; ++m) {
            int i = 2 * (t + NT * m); float a = __uint_as_float(r[m].x), c = __uint_as_float(r[m].z);
            bad += (a != fval(s, i)) + (c != fval(s, i + 1)); acc += a + c;
        }
        __syncthreads();
    }
    finish(p, bad, acc);
}
template <bool NODEP> __global__ void k_ll16(int steps, P p) {
    const int nb = gridDim.x, b = blockIdx.x;
    unsigned bad = 0; float acc = 0;
    int ib[6], nn[6];
#pragma unroll
    for (int m = 0; m < 6; ++m) { int e = threadIdx.x + NT * m; ib[m] = 0; nn[m] = 0; if (e < nb * 8) ll16_map(e, nb, ib[m], nn[m]); }
    for (int s = 1; s <= steps; ++s) {
        const unsigned tag = NODEP ? 7u : (unsigned)s;
        uint4 *L0 = p.rll16 + (size_t)(NODEP ? 1 : (s & 1)) * REPMAX * NBMAX * 8, *L = L0 + (b % p.rep) * NBMAX * 8;
        auto val = [&](int i) { return fval(tag, i); };
        if (!NODEP) for (int c = 0; c < p.rep; ++c) produce_ll16(L0 + c * NBMAX * 8, b, nb, tag, val);
        uint4 r[6]; poll16<6>(L, nb * 8, tag, r, p.tmo);
#pragma unroll
        for (int m = 0; m < 6; ++m) bad += check_ll16(r[m], ib[m], nn[m], val, acc);
        __syncthreads();
    }
    finish(p, bad, acc);
}
// LL16 with light polling: threads t < nb spin on ONE 16 B entry (slot 7) of producer t's line
// (3 KiB per poll round instead of 24 KiB); once every producer has shown the tag, one full
// read of all entries (entries still stale are re-polled by poll16, each carries its own tag).
__global__ void k_ll16_light(int steps, P p) {
    const int nb = gridDim.x, b = blockIdx.x, t = threadIdx.x;
    unsigned bad = 0; float acc = 0;
    int ib[6], nn[6];
#pragma unroll
    for (int m = 0; m < 6; ++m) { int e = t + NT * m; ib[m] = 0; nn[m] = 0; if (e < nb * 8) ll16_map(e, nb, ib[m], nn[m]); }
    for (int s = 1; s <= steps; ++s) {
        uint4 *L0 = p.rll16 + (size_t)(s & 1) * REPMAX * NBMAX * 8, *L = L0 + (b % p.rep) * NBMAX * 8;
        auto val = [&](int i) { return fval(s, i); };
        for (int c = 0; c < p.rep; ++c) produce_ll16(L0 + c * NBMAX * 8, b, nb, (unsigned)s, val);
        if (t < nb) { unsigned spins = 0; while (ld_vol_v4(L + t * 8 + 7).w != (unsigned)s) if (++spins > SPIN_LIMIT) { atomicExch(p.tmo, 1u); break; } }
        __syncthreads();
        uint4 r[6]; poll16<6>(L, nb * 8, (unsigned)s, r, p.tmo);
#pragma unroll
        for (int m = 0; m < 6; ++m) bad += check_ll16(r[m], ib[m], nn[m], val, acc);
        __syncthreads();
    }
    finish(p, bad, acc);
}
__global__ void k_read_plain(int steps, P p) {   // no dependency: data-movement floor for 16 KiB
    unsigned bad = 0; float acc = 0; const int t = threadIdx.x;
    for (int s = 1; s <= steps; ++s) {
        const float *v = p.rplain + (size_t)(REPMAX + blockIdx.x % p.rep) * V;   // prefilled with fval(7, i)
#pragma unroll
        for (int m = 0; m < V / 1024; ++m) {
            int q = t + NT * m; float4 x = __ldcg((const float4 *)v + q);
            bad += (x.x != fval(7, 4 * q)) + (x.y != fval(7, 4 * q + 1)) + (x.z != fval(7, 4 * q + 2)) + (x.w != fval(7, 4 * q + 3));
            acc += x.x + x.y + x.z + x.w;
        }
        __syncthreads();
    }
    finish(p, bad, acc);
}
// LL128: producer's warp 0 lanes 0..7 store one 128 B line; lanes 0..5 carry 24 data slots,
// lane 7 carries the tag in its last 8 bytes. Consumers: 8-lane groups load whole lines.
__global__ void k_ll128(int steps, P p) {
    const int nb = gridDim.x, b = blockIdx.x, lo = slo(b, nb), hi = slo(b + 1, nb), t = threadIdx.x, lane = t & 31, q = t & 7, g = t >> 3;
    unsigned bad = 0; float acc = 0;
    int ib[6], nn[6];
#pragma unroll
    for (int m = 0; m < 6; ++m) { int bb = g + 32 * m; ib[m] = 0; nn[m] = 0; if (bb < nb && q < 6) { ib[m] = slo(bb, nb) + 4 * q; nn[m] = max(0, min(4, slo(bb + 1, nb) - ib[m])); } }
    for (int s = 1; s <= steps; ++s) {
        uint4 *L = p.ll16 + (s & 1) * nb * 8;
        if (t < 8) {
            uint4 w = make_uint4(0, 0, 0, 0);
            if (q < 6) { int i = lo + 4 * q; float x[4]; for (int j = 0; j < 4; ++j) x[j] = i + j < hi ? fval(s, i + j) : 0.f;
                         w = make_uint4(__float_as_uint(x[0]), __float_as_uint(x[1]), __float_as_uint(x[2]), __float_as_uint(x[3])); }
            if (q == 7) w = make_uint4(0, 0, (unsigned)s, (unsigned)s);
            st_vol_v4(L + b * 8 + q, w);
        }
        uint4 r[6]; unsigned need = 0, spins = 0;
#pragma unroll
        for (int m = 0; m < 6; ++m) { r[m] = make_uint4(0, 0, 0, 0); if (g + 32 * m < nb) need |= 1u << m; }
        while (__any_sync(0xffffffffu, need)) {
#pragma unroll
            for (int m = 0; m < 6; ++m) if (need >> m & 1) r[m] = ld_vol_v4(L + (g + 32 * m) * 8 + q);
#pragma unroll
            for (int m = 0; m < 6; ++m) { unsigned f = __shfl_sync(0xffffffffu, r[m].w, (lane & ~7) | 7); if ((need >> m & 1) && f == (unsigned)s) need &= ~(1u << m); }
            if (++spins > SPIN_LIMIT) { atomicExch(p.tmo, 1u); need = 0; }
        }
#pragma unroll
        for (int m = 0; m < 6; ++m) {
            float x[4] = {__uint_as_float(r[m].x), __uint_as_float(r[m].y), __uint_as_float(r[m].z), __uint_as_float(r[m].w)};
            for (int j = 0; j < 4; ++j) if (j < nn[m]) { bad += x[j] != fval(s, ib[m] + j); acc += x[j]; }
        }
        __syncthreads();
    }
    finish(p, bad, acc);
}
// ---------------------------------------------------------------- 3. per-producer flags
// MODE 0: warp 0 polls packed flags; 1: warp 0 polls 128 B-padded flags; 2: one thread per packed flag
template <int MODE> __global__ void k_flags(int steps, P p) {
    const int nb = gridDim.x, b = blockIdx.x, lo = slo(b, nb), hi = slo(b + 1, nb), t = threadIdx.x;
    const int stride = MODE == 1 ? 32 : 1;
    unsigned bad = 0; float acc = 0;
    for (int s = 1; s <= steps; ++s) {
        float *v = p.plain + (s & 1) * V;
        if (lo + t < hi) v[lo + t] = fval(s, lo + t);
        __syncthreads();
        if (t == 0) { __threadfence(); st_vol(p.flags + b * stride, (unsigned)s); }
        if (MODE == 2 ? t < nb : t < 32) {
            unsigned need = 0, spins = 0; const int per = MODE == 2 ? 1 : (nb + 31) / 32;
            for (int m = 0; m < per; ++m) if (t + 32 * m < nb) need |= 1u << m;
            while (need) {                                  // relaxed loads issued back to back, one fence after
                unsigned f[8];
#pragma unroll
                for (int m = 0; m < 8; ++m) f[m] = (need >> m & 1) ? ld_vol(p.flags + (t + 32 * m) * stride) : 0u;
#pragma unroll
                for (int m = 0; m < 8; ++m) if ((need >> m & 1) && f[m] >= (unsigned)s) need &= ~(1u << m);
                if (++spins > SPIN_LIMIT) { atomicExch(p.tmo, 1u); break; }
            }
            asm volatile("fence.acq_rel.gpu;" ::: "memory");
        }
        __syncthreads();
#pragma unroll
        for (int m = 0; m < V / 1024; ++m) {
            int q = t + NT * m; float4 x = __ldcg((const float4 *)v + q);
            bad += (x.x != fval(s, 4 * q)) + (x.y != fval(s, 4 * q + 1)) + (x.z != fval(s, 4 * q + 2)) + (x.w != fval(s, 4 * q + 3));
            acc += x.x + x.y + x.z + x.w;
        }
        __syncthreads();
    }
    finish(p, bad, acc);
}
// 3d: sharded counter. Block b arrives (fence + atomic) on counter b % K (one 128 B line each), lanes
// 0..K-1 of warp 0 each poll one shard with ld.acquire. K = 1 is the single counter; K = nb is
// per-producer flags. Arrival serialisation on one line falls by K while polling traffic grows by K.
// The vector is written to p.rep replicas (consumer b reads copy b % rep) to spread the hot lines.
template <int K> __global__ void k_sharded(int steps, P p) {
    const int nb = gridDim.x, b = blockIdx.x, lo = slo(b, nb), hi = slo(b + 1, nb), t = threadIdx.x;
    const unsigned mine = t < K ? (unsigned)((nb - t + K - 1) / K) : 0u;   // blocks arriving on shard t
    unsigned bad = 0; float acc = 0;
    for (int s = 1; s <= steps; ++s) {
        float *v0 = p.rplain + (size_t)(s & 1) * REPMAX * V, *v = v0 + (b % p.rep) * V;
        if (lo + t < hi) for (int c = 0; c < p.rep; ++c) v0[c * V + lo + t] = fval(s, lo + t);
        __syncthreads();
        if (t == 0) { __threadfence(); atomicAdd(p.flags + (b % K) * 32, 1u); }
        if (t < K) { unsigned spins = 0; while (ld_acquire(p.flags + t * 32) < mine * s) if (++spins > SPIN_LIMIT) { atomicExch(p.tmo, 1u); break; } }
        __syncthreads();
#pragma unroll
        for (int m = 0; m < V / 1024; ++m) {
            int q = t + NT * m; float4 x = __ldcg((const float4 *)v + q);
            bad += (x.x != fval(s, 4 * q)) + (x.y != fval(s, 4 * q + 1)) + (x.z != fval(s, 4 * q + 2)) + (x.w != fval(s, 4 * q + 3));
            acc += x.x + x.y + x.z + x.w;
        }
        __syncthreads();
    }
    finish(p, bad, acc);
}
// ---------------------------------------------------------------- 4. hierarchical (clusters)
__global__ void k_cluster_flags(int steps, P p) {
    cg::cluster_group c = cg::this_cluster();
    const int nb = gridDim.x, b = blockIdx.x, lo = slo(b, nb), hi = slo(b + 1, nb), t = threadIdx.x;
    const int cs = c.num_blocks(), ncl = nb / cs, cid = b / cs;
    unsigned bad = 0; float acc = 0;
    for (int s = 1; s <= steps; ++s) {
        float *v = p.plain + (s & 1) * V;
        if (lo + t < hi) v[lo + t] = fval(s, lo + t);
        c.sync();                                                   // cluster's slices written (cluster scope)
        if (c.block_rank() == 0 && t == 0) { __threadfence(); st_vol(p.flags + cid, (unsigned)s); }   // cumulative gpu release
        if (t < ncl) { unsigned spins = 0; while (ld_acquire(p.flags + t) < (unsigned)s) if (++spins > SPIN_LIMIT) { atomicExch(p.tmo, 1u); break; } }
        __syncthreads();
#pragma unroll
        for (int m = 0; m < V / 1024; ++m) {
            int q = t + NT * m; float4 x = __ldcg((const float4 *)v + q);
            bad += (x.x != fval(s, 4 * q)) + (x.y != fval(s, 4 * q + 1)) + (x.z != fval(s, 4 * q + 2)) + (x.w != fval(s, 4 * q + 3));
            acc += x.x + x.y + x.z + x.w;
        }
        __syncthreads();
    }
    c.sync();
    finish(p, bad, acc);
}
// LL16 through L2, but each cluster member polls only 1/cs of the producer lines and PUSHES
// what it got into every member's shared memory (DSMEM stores, fire-and-forget), then one
// cluster.sync publishes them: L2 read traffic drops by the cluster size.
__global__ void k_cluster_ll16(int steps, P p) {
    __shared__ float xsb[2][V];
    cg::cluster_group c = cg::this_cluster();
    const int nb = gridDim.x, b = blockIdx.x, t = threadIdx.x, cs = c.num_blocks(), rk = c.block_rank();
    const int b0 = rk * nb / cs, b1 = (rk + 1) * nb / cs;           // producer lines this member polls
    unsigned bad = 0; float acc = 0;
    int i0 = 0, n0 = 0; if (t < (b1 - b0) * 8) ll16_map(b0 * 8 + t, nb, i0, n0);
    for (int s = 1; s <= steps; ++s) {
        uint4 *L = p.ll16 + (s & 1) * nb * 8; float *xs = xsb[s & 1];   // double buffer: peers may still write/read the other one
        auto val = [&](int i) { return fval(s, i); };
        produce_ll16(L, b, nb, (unsigned)s, val);
        uint4 r[1]; poll16<1>(L + b0 * 8, (b1 - b0) * 8, (unsigned)s, r, p.tmo);
        if (t < (b1 - b0) * 8) {
            float x[3] = {__uint_as_float(r[0].x), __uint_as_float(r[0].y), __uint_as_float(r[0].z)};
            for (int q = 0; q < cs; ++q) {
                float *dst = c.map_shared_rank(xs, q);
                for (int j = 0; j < 3; ++j) if (j < n0) dst[i0 + j] = x[j];
            }
        }
        c.sync();
        for (int i = t; i < V; i += NT) { bad += xs[i] != fval(s, i); acc += xs[i]; }
    }
    c.sync();
    finish(p, bad, acc);
}
#ifndef DSMEM_PTX
#define DSMEM_PTX 1   // 1: mapa + ld.shared::cluster; 0: generic pointer from map_shared_rank
#endif
__device__ __forceinline__ unsigned smem_u32(const void *p) { return (unsigned)__cvta_generic_to_shared(p); }
// DSMEM reference: per step, cluster.sync then every block reads 16 KiB (float4) from the next
// member's shared memory. No global memory involved.
__global__ void k_dsmem_read(int steps, P p) {
    __shared__ float4 buf[V / 4];
    cg::cluster_group c = cg::this_cluster();
    const int t = threadIdx.x, cs = c.num_blocks(), rk = c.block_rank();
    for (int i = t; i < V / 4; i += NT) buf[i] = make_float4(i, i, i, i);
    c.sync();
    const float4 *peer = c.map_shared_rank(buf, (rk + 1) % cs);
    unsigned pa; asm volatile("mapa.shared::cluster.u32 %0, %1, %2;" : "=r"(pa) : "r"(smem_u32(buf)), "r"((rk + 1) % cs));
    unsigned bad = 0; float acc = 0;
    for (int s = 1; s <= steps; ++s) {
        float4 x[V / 1024];
#pragma unroll
        for (int m = 0; m < V / 1024; ++m) {
            if (DSMEM_PTX) asm volatile("ld.shared::cluster.v4.f32 {%0,%1,%2,%3}, [%4];" : "=f"(x[m].x), "=f"(x[m].y), "=f"(x[m].z), "=f"(x[m].w) : "r"(pa + 16u * (t + NT * m)));
            else x[m] = peer[t + NT * m];
        }
#pragma unroll
        for (int m = 0; m < V / 1024; ++m) { bad += x[m].x != (float)(t + NT * m); acc += x[m].y; }
        c.sync();
    }
    finish(p, bad, acc);
}
// ---------------------------------------------------------------- 5. all-reduce (Megatron row-parallel)
__global__ void k_allreduce_red(int steps, P p) {
    const int nb = gridDim.x, b = blockIdx.x, lo = slo(b, nb), hi = slo(b + 1, nb), t = threadIdx.x;
    unsigned bad = 0; float acc = 0;
    for (int s = 1; s <= steps; ++s) {
        float *A = p.acc + (s % 3) * V, *Z = p.acc + ((s + 1) % 3) * V;
        if (lo + t < hi) Z[lo + t] = 0.f;                          // last read two steps ago
#pragma unroll
        for (int m = 0; m < V / 1024; ++m) { int i = 4 * (t + NT * m); red_add_v4(A + i, make_float4(pval(b, s, i), pval(b, s, i + 1), pval(b, s, i + 2), pval(b, s, i + 3))); }
        counter_barrier(p.ctr, nb * (unsigned)s, p.tmo);
#pragma unroll
        for (int m = 0; m < V / 1024; ++m) {
            int i = 4 * (t + NT * m); float4 x = __ldcg((const float4 *)(A + i));
            bad += (x.x != sumval(nb, s, i)) + (x.y != sumval(nb, s, i + 1)) + (x.z != sumval(nb, s, i + 2)) + (x.w != sumval(nb, s, i + 3));
            acc += x.x + x.y + x.z + x.w;
        }
        __syncthreads();
    }
    finish(p, bad, acc);
}
__global__ void k_allreduce_cluster(int steps, P p) {
    __shared__ float4 part[V / 4];
    cg::cluster_group c = cg::this_cluster();
    const int nb = gridDim.x, b = blockIdx.x, lo = slo(b, nb), hi = slo(b + 1, nb), t = threadIdx.x, cs = c.num_blocks(), rk = c.block_rank();
    const int ch = V / 4 / cs;                                    // float4s per member chunk
    unsigned bad = 0; float acc = 0;
    for (int s = 1; s <= steps; ++s) {
        float *A = p.acc + (s % 3) * V, *Z = p.acc + ((s + 1) % 3) * V;
        if (lo + t < hi) Z[lo + t] = 0.f;
#pragma unroll
        for (int m = 0; m < V / 1024; ++m) { int i = 4 * (t + NT * m); part[t + NT * m] = make_float4(pval(b, s, i), pval(b, s, i + 1), pval(b, s, i + 2), pval(b, s, i + 3)); }
        c.sync();
        for (int j = t; j < ch; j += NT) {
            int q4 = rk * ch + j; float4 sum = make_float4(0, 0, 0, 0);
            for (int q = 0; q < cs; ++q) { float4 x = c.map_shared_rank(part, q)[q4]; sum.x += x.x; sum.y += x.y; sum.z += x.z; sum.w += x.w; }
            red_add_v4(A + 4 * q4, sum);
        }
        counter_barrier(p.ctr, nb * (unsigned)s, p.tmo);          // also orders peers' DSMEM reads before my next write
#pragma unroll
        for (int m = 0; m < V / 1024; ++m) {
            int i = 4 * (t + NT * m); float4 x = __ldcg((const float4 *)(A + i));
            bad += (x.x != sumval(nb, s, i)) + (x.y != sumval(nb, s, i + 1)) + (x.z != sumval(nb, s, i + 2)) + (x.w != sumval(nb, s, i + 3));
            acc += x.x + x.y + x.z + x.w;
        }
        __syncthreads();
    }
    c.sync();
    finish(p, bad, acc);
}
// reduce-scatter (LL16, producer b writes one line per chunk j into llrs[j*nb+b]) then
// all-gather (LL16). Two one-way hops, no fences, no atomics.
__global__ void k_allreduce_ll16(int steps, P p) {
    __shared__ float red[8][8][3];
    const int nb = gridDim.x, b = blockIdx.x, t = threadIdx.x, lane = t & 31, w = t >> 5;
    unsigned bad = 0; float acc = 0;
    int ib[6], nn[6];
#pragma unroll
    for (int m = 0; m < 6; ++m) { int e = t + NT * m; ib[m] = 0; nn[m] = 0; if (e < nb * 8) ll16_map(e, nb, ib[m], nn[m]); }
    for (int s = 1; s <= steps; ++s) {
        uint4 *RS = p.llrs + (size_t)(s & 1) * nb * nb * 8, *AG = p.ll16 + (s & 1) * nb * 8;
#pragma unroll
        for (int m = 0; m < 6; ++m) {                              // my partial, chunked per reducer (entry e: chunk e>>3, slot e&7)
            int e = t + NT * m; if (e >= nb * 8) continue;
            int j = e >> 3, k = e & 7, i = ib[m], n = nn[m];
            float x0 = n > 0 ? pval(b, s, i) : 0.f, x1 = n > 1 ? pval(b, s, i + 1) : 0.f, x2 = n > 2 ? pval(b, s, i + 2) : 0.f;
            st_vol_v4(RS + (size_t)j * nb * 8 + b * 8 + k, make_uint4(__float_as_uint(x0), __float_as_uint(x1), __float_as_uint(x2), (unsigned)s));
        }
        uint4 r[6]; poll16<6>(RS + (size_t)b * nb * 8, nb * 8, (unsigned)s, r, p.tmo);   // entry e: producer e>>3, slot e&7 == t&7
        float a0 = 0, a1 = 0, a2 = 0;
#pragma unroll
        for (int m = 0; m < 6; ++m) if (t + NT * m < nb * 8) { a0 += __uint_as_float(r[m].x); a1 += __uint_as_float(r[m].y); a2 += __uint_as_float(r[m].z); }
        for (int o = 8; o < 32; o <<= 1) { a0 += __shfl_xor_sync(~0u, a0, o); a1 += __shfl_xor_sync(~0u, a1, o); a2 += __shfl_xor_sync(~0u, a2, o); }
        if (lane < 8) { red[w][lane][0] = a0; red[w][lane][1] = a1; red[w][lane][2] = a2; }
        __syncthreads();
        if (t < 8) {
            float y[3] = {0, 0, 0};
            for (int ww = 0; ww < 8; ++ww) for (int j = 0; j < 3; ++j) y[j] += red[ww][t][j];
            st_vol_v4(AG + b * 8 + t, make_uint4(__float_as_uint(y[0]), __float_as_uint(y[1]), __float_as_uint(y[2]), (unsigned)s));
        }
        auto val = [&](int i) { return sumval(nb, s, i); };
        poll16<6>(AG, nb * 8, (unsigned)s, r, p.tmo);
#pragma unroll
        for (int m = 0; m < 6; ++m) bad += check_ll16(r[m], ib[m], nn[m], val, acc);
        __syncthreads();
    }
    finish(p, bad, acc);
}
// ---------------------------------------------------------------- 6. GEMV chain with a DRAM weight stream
__host__ __device__ inline uint32_t hash32(uint64_t x) { x ^= x >> 33; x *= 0xff51afd7ed558ccdULL; x ^= x >> 33; x *= 0xc4ceb9fe1a85ec53ULL; x ^= x >> 33; return (uint32_t)x; }
__host__ __device__ inline uint16_t f2bf(float f) { uint32_t u; memcpy(&u, &f, 4); u += 0x7FFFu + ((u >> 16) & 1u); return (uint16_t)(u >> 16); }
__host__ __device__ inline float bf2f(uint16_t h) { uint32_t u = (uint32_t)h << 16; float f; memcpy(&f, &u, 4); return f; }
__host__ __device__ inline uint16_t wgen(uint64_t idx) { float u = (hash32(idx) >> 8) * (1.f / 16777216.f); return f2bf((2.f * u - 1.f) * 0.0270633f); } // var = 1/4096
__host__ __device__ inline float xgen(int i) { return (hash32(0x1234567ULL + i) >> 8) * (2.f / 16777216.f) - 1.f; }
__global__ void k_wgen(uint16_t *w, size_t n) { for (size_t i = blockIdx.x * (size_t)blockDim.x + threadIdx.x; i < n; i += (size_t)gridDim.x * blockDim.x) w[i] = wgen(i); }
__global__ void k_bw(const uint4 *w, size_t n4, float *sink) {   // reference DRAM read bandwidth
    uint32_t a = 0;
    for (size_t i = blockIdx.x * (size_t)blockDim.x + threadIdx.x; i < n4; i += (size_t)gridDim.x * blockDim.x) { uint4 v = __ldcs(w + i); a ^= v.x ^ v.y ^ v.z ^ v.w; }
    if (a == 0x12345678u) sink[0] = 1.f;
}
// NS: ring stages, one 8 KiB weight row each (8 = 64 KiB, 12 = 96 KiB of the 99 KiB per block)
__device__ __forceinline__ void mbar_init(uint64_t *b, unsigned n) { asm volatile("mbarrier.init.shared::cta.b64 [%0], %1;" :: "r"(smem_u32(b)), "r"(n) : "memory"); }
__device__ __forceinline__ void tma_row(void *dst, const void *src, unsigned bytes, uint64_t *b) {
    asm volatile("mbarrier.arrive.expect_tx.shared::cta.b64 _, [%0], %1;" :: "r"(smem_u32(b)), "r"(bytes) : "memory");
    asm volatile("cp.async.bulk.shared::cluster.global.mbarrier::complete_tx::bytes [%0], [%1], %2, [%3];" :: "r"(smem_u32(dst)), "l"(src), "r"(bytes), "r"(smem_u32(b)) : "memory");
}
__device__ __forceinline__ void mbar_wait(uint64_t *b, unsigned parity) {
    asm volatile("{\n .reg .pred p;\n WAIT_%=:\n mbarrier.try_wait.parity.shared::cta.b64 p, [%0], %1;\n @!p bra WAIT_%=;\n}" :: "r"(smem_u32(b)), "r"(parity) : "memory");
}
// MODE 0 stream only (no dependency), 1 counter barrier + ld.cg gather (replica b % p.rep), 2 LL8 gather.
// TMA: weights arrive by cp.async.bulk (TMA engine, one thread issues 8 KiB rows, mbarrier completion),
// else by per-thread 16 B cp.async through the LSU (then the dependency's loads queue behind the stream).
template <int MODE, bool OVERLAP, bool TMA, int NS>
__global__ void __launch_bounds__(NT, 1) k_gemv(const uint16_t *W, int G, int nmat, const float *x0, float *ylog, P p) {
    extern __shared__ __align__(128) uint4 ring[];   // NS * 512 uint4
    __shared__ float red[8][24];
    __shared__ uint64_t full[NS];
    const int nb = gridDim.x, b = blockIdx.x, t = threadIdx.x, lane = t & 31, wp = t >> 5;
    const int r0 = slo(b, nb), nr = slo(b + 1, nb) - r0, total = G * nr;
    unsigned long long bcyc = 0;
    float xr[16];
    for (int k = 0; k < 8; ++k) { xr[k] = x0[t * 8 + k]; xr[8 + k] = x0[2048 + t * 8 + k]; }
    if (TMA) { if (t == 0) { for (int k = 0; k < NS; ++k) mbar_init(&full[k], 1); asm volatile("fence.mbarrier_init.release.cluster;" ::: "memory"); } __syncthreads(); }
    auto src_of = [&](int j) { int g = j / nr, r = j - g * nr; return (const uint4 *)(W + ((size_t)(g % nmat) * V + r0 + r) * V); };
    auto issue = [&](int j, bool ok) {               // cp.async: every thread; TMA: thread 0
        if (TMA) {
            if (ok && j < total && t == 0) { asm volatile("fence.proxy.async.shared::cta;" ::: "memory"); tma_row(ring + (j % NS) * 512, src_of(j), 8192, &full[j % NS]); }
        } else {
            if (ok && j < total) { const uint4 *src = src_of(j); uint4 *st = ring + (j % NS) * 512; cp_async16(st + t, src + t); cp_async16(st + 256 + t, src + 256 + t); }
            cp_commit();
        }
    };
    auto wait_row = [&](int j) {
        if (TMA) mbar_wait(&full[j % NS], (j / NS) & 1);
        else { cp_wait<NS - 2>(); __syncthreads(); }
    };
    auto compute = [&](int j) {
        const uint4 *st = ring + (j % NS) * 512;
        uint4 a = st[t], c = st[256 + t]; uint32_t wa[4] = {a.x, a.y, a.z, a.w}, wc[4] = {c.x, c.y, c.z, c.w};
        float s = 0;
#pragma unroll
        for (int k = 0; k < 4; ++k) {
            s += __uint_as_float(wa[k] << 16) * xr[2 * k] + __uint_as_float(wa[k] & 0xFFFF0000u) * xr[2 * k + 1];
            s += __uint_as_float(wc[k] << 16) * xr[8 + 2 * k] + __uint_as_float(wc[k] & 0xFFFF0000u) * xr[9 + 2 * k];
        }
        for (int o = 16; o; o >>= 1) s += __shfl_xor_sync(~0u, s, o);
        if (lane == 0) red[wp][j % nr] = s;
    };
    auto boundary = [&](int g) {
        long long c0 = clock64();
        __syncthreads();
        float y = 0;
        if (t < nr) { for (int k = 0; k < 8; ++k) y += red[k][t]; ylog[(size_t)g * V + r0 + t] = y; }
        const unsigned tag = g + 1;
        if (MODE == 1) {
            float *v0 = p.rplain + (size_t)(tag & 1) * REPMAX * V, *v = v0 + (b % p.rep) * V;
            if (t < nr) for (int c = 0; c < p.rep; ++c) v0[c * V + r0 + t] = y;
            counter_barrier(p.ctr, nb * tag, p.tmo);
            const float4 *v4 = (const float4 *)v;
            float4 u0 = __ldcg(v4 + 2 * t), u1 = __ldcg(v4 + 2 * t + 1), u2 = __ldcg(v4 + 512 + 2 * t), u3 = __ldcg(v4 + 512 + 2 * t + 1);
            float tmp[16] = {u0.x, u0.y, u0.z, u0.w, u1.x, u1.y, u1.z, u1.w, u2.x, u2.y, u2.z, u2.w, u3.x, u3.y, u3.z, u3.w};
            for (int k = 0; k < 16; ++k) xr[k] = tmp[k];
        } else if (MODE == 2) {
            uint2 *L = p.ll8 + (tag & 1) * V;
            if (t < nr) st_vol_v2(L + r0 + t, make_uint2(__float_as_uint(y), tag));
            const uint4 *L4 = (const uint4 *)L;
            uint4 r[8]; unsigned need = 0xFF, spins = 0;
            while (need) {
#pragma unroll
                for (int m = 0; m < 8; ++m) if (need >> m & 1) r[m] = ld_vol_v4(L4 + (m < 4 ? 4 * t + m : 1024 + 4 * t + m - 4));
#pragma unroll
                for (int m = 0; m < 8; ++m) if ((need >> m & 1) && r[m].y == tag && r[m].w == tag) need &= ~(1u << m);
                if (++spins > SPIN_LIMIT) { atomicExch(p.tmo, 1u); break; }
            }
#pragma unroll
            for (int m = 0; m < 8; ++m) { xr[2 * m] = __uint_as_float(r[m].x); xr[2 * m + 1] = __uint_as_float(r[m].z); }
        }
        bcyc += clock64() - c0;
    };
    if (OVERLAP) {                                   // one continuous stream across GEMVs
        if (TMA) {
            for (int j = 0; j < NS; ++j) issue(j, true);
            for (int i = 0; i < total; ++i) {
                wait_row(i); compute(i); __syncthreads();   // everyone is done with slot i % NS
                issue(i + NS, true);
                if (i % nr == nr - 1) boundary(i / nr);
            }
        } else {
            for (int j = 0; j < NS - 1; ++j) issue(j, true);
            for (int i = 0; i < total; ++i) {
                wait_row(i); issue(i + NS - 1, true); compute(i);
                if (i % nr == nr - 1) boundary(i / nr);
            }
        }
    } else {                                         // drain at each boundary: the next tile waits for the dependency
        const int D = TMA ? NS : NS - 1;
        for (int g = 0; g < G; ++g) {
            for (int j = 0; j < D; ++j) issue(g * nr + j, j < nr);
            for (int r = 0; r < nr; ++r) {
                if (TMA) { wait_row(g * nr + r); compute(g * nr + r); __syncthreads(); issue(g * nr + r + D, r + D < nr); }
                else { wait_row(g * nr + r); issue(g * nr + r + D, r + D < nr); compute(g * nr + r); }
            }
            boundary(g);
        }
    }
    if (!TMA) cp_wait<0>();
    if (t == 0) atomicAdd(p.stat, bcyc);
}

// Dynamic row claiming + LL8 gather (TMA stream). Rows of each GEMV are claimed from a per-GEMV
// atomic counter as ring slots free up, so a fast SM takes more rows and the step ends one row
// after the slowest claim, not when the unluckiest static tile finishes. Claims run ahead into
// the NEXT GEMV (weights do not depend on x), so the ring keeps streaming across the boundary.
// Every finished row writes its output as an LL8 {y, tag} entry; the gather for x_{g+1} polls
// all 4096 entries, so completion needs no separate barrier.
template <int NS, bool DEP>
__global__ void __launch_bounds__(NT, 1) k_gemv_dyn(const uint16_t *W, int G, int nmat, const float *x0, float *ylog, P p) {
    extern __shared__ __align__(128) uint4 ring[];
    __shared__ float red[8][NS];
    __shared__ uint64_t full[NS];
    __shared__ int srow[NS], sg[NS];
    const int t = threadIdx.x, lane = t & 31, wp = t >> 5;
    unsigned long long bcyc = 0;
    float xr[16];
    for (int k = 0; k < 8; ++k) { xr[k] = x0[t * 8 + k]; xr[8 + k] = x0[2048 + t * 8 + k]; }
    int ig = 0; unsigned nxt = 0;                     // thread 0: GEMV being claimed, pre-issued claim
    if (t == 0) { for (int k = 0; k < NS; ++k) mbar_init(&full[k], 1); asm volatile("fence.mbarrier_init.release.cluster;" ::: "memory"); nxt = atomicAdd(p.rowctr, 1u); }
    auto claim_issue = [&](int slot) {                // thread 0 only
        unsigned r = nxt;
        while (r >= (unsigned)V) { if (++ig >= G) { srow[slot] = -1; return; } r = atomicAdd(p.rowctr + ig, 1u); }
        srow[slot] = (int)r; sg[slot] = ig;
        asm volatile("fence.proxy.async.shared::cta;" ::: "memory");
        tma_row(ring + slot * 512, W + ((size_t)(ig % nmat) * V + r) * V, 8192, &full[slot]);
        nxt = atomicAdd(p.rowctr + ig, 1u);           // result is only consumed at the next claim
    };
    if (t == 0) for (int k = 0; k < NS; ++k) claim_issue(k);
    __syncthreads();
    int cur = 0;                                      // GEMV whose input xr holds
    for (int k = 0;; ++k) {
        const int slot = k % NS, row = srow[slot], g = sg[slot];
        if (row < 0) break;
        if (DEP && g != cur) {                        // first row of GEMV g: gather x_g = y_{g-1} (LL8, tag g)
            long long c0 = clock64();
            const uint4 *L4 = (const uint4 *)(p.ll8 + (g & 1) * V);
            uint4 r[8]; unsigned need = 0xFF, spins = 0;
            while (need) {
#pragma unroll
                for (int m = 0; m < 8; ++m) if (need >> m & 1) r[m] = ld_vol_v4(L4 + (m < 4 ? 4 * t + m : 1024 + 4 * t + m - 4));
#pragma unroll
                for (int m = 0; m < 8; ++m) if ((need >> m & 1) && r[m].y == (unsigned)g && r[m].w == (unsigned)g) need &= ~(1u << m);
                if (++spins > SPIN_LIMIT) { atomicExch(p.tmo, 1u); break; }
            }
#pragma unroll
            for (int m = 0; m < 8; ++m) { xr[2 * m] = __uint_as_float(r[m].x); xr[2 * m + 1] = __uint_as_float(r[m].z); }
            cur = g; bcyc += clock64() - c0;
        }
        mbar_wait(&full[slot], (k / NS) & 1);
        const uint4 *st = ring + slot * 512;
        uint4 a = st[t], c = st[256 + t]; uint32_t wa[4] = {a.x, a.y, a.z, a.w}, wc[4] = {c.x, c.y, c.z, c.w};
        float s = 0;
#pragma unroll
        for (int q = 0; q < 4; ++q) {
            s += __uint_as_float(wa[q] << 16) * xr[2 * q] + __uint_as_float(wa[q] & 0xFFFF0000u) * xr[2 * q + 1];
            s += __uint_as_float(wc[q] << 16) * xr[8 + 2 * q] + __uint_as_float(wc[q] & 0xFFFF0000u) * xr[9 + 2 * q];
        }
        for (int o = 16; o; o >>= 1) s += __shfl_xor_sync(~0u, s, o);
        if (lane == 0) red[wp][slot] = s;
        __syncthreads();                              // slot consumed, partials visible
        if (t == 0) {
            float y = 0; for (int w = 0; w < 8; ++w) y += red[w][slot];
            ylog[(size_t)g * V + row] = y;
            st_vol_v2(p.ll8 + ((g + 1) & 1) * V + row, make_uint2(__float_as_uint(y), (unsigned)(g + 1)));
            claim_issue(slot);
        }
        __syncthreads();                              // srow/sg of the refilled slot visible
    }
    if (t == 0) atomicAdd(p.stat, bcyc);
}

// ---------------------------------------------------------------- misc
__global__ void clock_kernel(unsigned long long *out) {
    unsigned long long c0 = clock64(), t0 = gtimer();
    while (gtimer() - t0 < 2000000ull) { }
    out[0] = clock64() - c0; out[1] = gtimer() - t0;
}
__global__ void chase_kernel(const unsigned *next, int steps, unsigned *sink, unsigned long long *cyc) {
    unsigned i = 0; unsigned long long c0 = clock64();
    for (int s = 0; s < steps; ++s) i = __ldcg(next + i);
    cyc[0] = clock64() - c0; sink[0] = i;
}
__global__ void fill_kernel(P p, int nb) {   // no-dependency buffers: plain[V..] and ll16 parity 1 hold step 7
    for (int i = threadIdx.x; i < V * REPMAX; i += blockDim.x) p.rplain[REPMAX * V + i] = fval(7, i % V);
    for (int e = threadIdx.x; e < nb * 8 * REPMAX; e += blockDim.x) {
        int c = e / (nb * 8), ee = e % (nb * 8), bb = ee >> 3, k = ee & 7, lo = slo(bb, nb), hi = slo(bb + 1, nb), i = lo + 3 * k;
        float x0 = i < hi ? fval(7, i) : 0.f, x1 = i + 1 < hi ? fval(7, i + 1) : 0.f, x2 = i + 2 < hi ? fval(7, i + 2) : 0.f;
        p.rll16[(size_t)(REPMAX + c) * NBMAX * 8 + ee] = make_uint4(__float_as_uint(x0), __float_as_uint(x1), __float_as_uint(x2), 7u);
    }
    for (int e = threadIdx.x; e < nb * 8; e += blockDim.x) {
        int bb = e >> 3, k = e & 7, lo = slo(bb, nb), hi = slo(bb + 1, nb), i = lo + 3 * k;
        float x0 = i < hi ? fval(7, i) : 0.f, x1 = i + 1 < hi ? fval(7, i + 1) : 0.f, x2 = i + 2 < hi ? fval(7, i + 2) : 0.f;
        p.ll16[nb * 8 + e] = make_uint4(__float_as_uint(x0), __float_as_uint(x1), __float_as_uint(x2), 7u);
    }
}

static cudaStream_t st;
static float ms_between(cudaEvent_t a, cudaEvent_t b) { float ms; CK(cudaEventElapsedTime(&ms, a, b)); return ms; }

int main(int argc, char **argv) {
    const int N = argc > 1 ? atoi(argv[1]) : 4000, TR = argc > 2 ? atoi(argv[2]) : 11;
    const int G = argc > 3 ? atoi(argv[3]) : 64, NMAT = argc > 4 ? atoi(argv[4]) : 16;
    const std::string only = argc > 5 ? argv[5] : "";   // run only designs whose name contains this
    auto want = [&](const char *name) { return only.empty() || std::string(name).find(only) != std::string::npos; };
    cudaDeviceProp dp; CK(cudaGetDeviceProperties(&dp, 0));
    const int nsm = dp.multiProcessorCount;
    CK(cudaStreamCreateWithFlags(&st, cudaStreamNonBlocking));
    cudaEvent_t e0, e1; CK(cudaEventCreate(&e0)); CK(cudaEventCreate(&e1));
    P p{};
    CK(cudaMalloc(&p.ctr, 64)); CK(cudaMalloc(&p.flags, NBMAX * 128)); CK(cudaMalloc(&p.err, 4)); CK(cudaMalloc(&p.tmo, 4));
    CK(cudaMalloc(&p.plain, 2 * V * 4)); CK(cudaMalloc(&p.acc, 3 * V * 4)); CK(cudaMalloc(&p.ll8, 2 * V * 8));
    CK(cudaMalloc(&p.ll16, 2 * NBMAX * 8 * 16)); CK(cudaMalloc(&p.llrs, (size_t)2 * NBMAX * NBMAX * 8 * 16)); CK(cudaMalloc(&p.sink, 64)); CK(cudaMalloc(&p.stat, 64)); CK(cudaMalloc(&p.rowctr, 4096 * 4));
    CK(cudaMalloc(&p.rplain, (size_t)2 * REPMAX * V * 4)); CK(cudaMalloc(&p.rll16, (size_t)2 * REPMAX * NBMAX * 8 * 16)); p.rep = 1;
    unsigned long long *dc; CK(cudaMalloc(&dc, 64)); unsigned long long hc[2];
    clock_kernel<<<1, 1, 0, st>>>(dc); CK(cudaStreamSynchronize(st)); CK(cudaMemcpy(hc, dc, 16, cudaMemcpyDeviceToHost));
    const double ghz = (double)hc[0] / (double)hc[1];
    double l2_cyc;
    {
        size_t n = (256 << 10) / 128; std::vector<unsigned> perm(n), nxt(n * 32, 0);
        for (size_t i = 0; i < n; ++i) perm[i] = i;
        srand(7); for (size_t i = n - 1; i > 0; --i) std::swap(perm[i], perm[rand() % (i + 1)]);
        for (size_t i = 0; i < n; ++i) nxt[perm[i] * 32] = perm[(i + 1) % n] * 32;
        unsigned *d; CK(cudaMalloc(&d, n * 128)); CK(cudaMemcpy(d, nxt.data(), n * 128, cudaMemcpyHostToDevice));
        chase_kernel<<<1, 1, 0, st>>>(d, 100000, (unsigned *)p.sink, dc); chase_kernel<<<1, 1, 0, st>>>(d, 100000, (unsigned *)p.sink, dc);
        CK(cudaStreamSynchronize(st)); CK(cudaMemcpy(hc, dc, 8, cudaMemcpyDeviceToHost)); l2_cyc = hc[0] / 1e5; CK(cudaFree(d));
    }
    printf("{\"device\": \"%s\", \"sm\": \"%d.%d\", \"sms\": %d, \"l2_bytes\": %d, \"sm_clock_ghz\": %.3f, \"l2_hit_latency_cycles\": %.1f, \"l2_hit_latency_ns\": %.1f,\n",
           dp.name, dp.major, dp.minor, nsm, dp.l2CacheSize, ghz, l2_cyc, l2_cyc / ghz);
    printf(" \"steps\": %d, \"trials\": %d, \"vector_words\": %d, \"vector_bytes\": %d,\n \"designs\": [\n", N, TR, V, V * 4);

    auto reset = [&](int nb) {
        CK(cudaMemsetAsync(p.ctr, 0, 64, st)); CK(cudaMemsetAsync(p.flags, 0, NBMAX * 128, st)); CK(cudaMemsetAsync(p.err, 0, 4, st)); CK(cudaMemsetAsync(p.tmo, 0, 4, st));
        CK(cudaMemsetAsync(p.plain, 0, 2 * V * 4, st)); CK(cudaMemsetAsync(p.acc, 0, 3 * V * 4, st)); CK(cudaMemsetAsync(p.ll8, 0, 2 * V * 8, st));
        CK(cudaMemsetAsync(p.ll16, 0, 2 * NBMAX * 8 * 16, st)); CK(cudaMemsetAsync(p.llrs, 0, (size_t)2 * nb * nb * 8 * 16, st));
        CK(cudaMemsetAsync(p.rplain, 0, (size_t)2 * REPMAX * V * 4, st)); CK(cudaMemsetAsync(p.rll16, 0, (size_t)2 * REPMAX * NBMAX * 8 * 16, st));
        fill_kernel<<<1, 1024, 0, st>>>(p, nb);
    };
    bool first = true;
    // launch: cs == 0 -> cooperative (co-residency guaranteed), else cluster launch of size cs
    // every micro kernel gets PAD bytes of dynamic shared memory so that exactly one block fits per SM
    const int PAD = 64 << 10;
    auto run = [&](const char *name, const char *what, void (*k)(int, P), int nb, int cs, int rep = 1) {
        if (!want(name)) return;
        int steps = N; p.rep = rep;
        CK(cudaFuncSetAttribute((const void *)k, cudaFuncAttributeMaxDynamicSharedMemorySize, PAD));
        if (cs) {
            if (cs > 8) CK(cudaFuncSetAttribute((const void *)k, cudaFuncAttributeNonPortableClusterSizeAllowed, 1));
            cudaLaunchConfig_t cfg = {}; cfg.gridDim = cs; cfg.blockDim = NT; cfg.stream = st; cfg.dynamicSmemBytes = PAD;
            cudaLaunchAttribute at[1]; at[0].id = cudaLaunchAttributeClusterDimension; at[0].val.clusterDim.x = cs; at[0].val.clusterDim.y = 1; at[0].val.clusterDim.z = 1;
            cfg.attrs = at; cfg.numAttrs = 1;
            int ncl = 0; if (cudaOccupancyMaxActiveClusters(&ncl, (const void *)k, &cfg) != cudaSuccess || ncl < 1) { cudaGetLastError(); fprintf(stderr, "%s: cluster %d not launchable\n", name, cs); return; }
            if (nb == 0 || nb > ncl * cs) nb = ncl * cs;
            if (nb > nsm) nb = nsm / cs * cs;
            fprintf(stderr, "%s: cluster %d, max active clusters %d, grid %d\n", name, cs, ncl, nb);
        } else {
            int occ = 0; CK(cudaOccupancyMaxActiveBlocksPerMultiprocessor(&occ, k, NT, PAD)); if (occ != 1 || occ * nsm < nb) { fprintf(stderr, "%s: not co-resident\n", name); return; }
        }
        std::vector<double> v; unsigned errs = 0, tmo = 0;
        for (int tr = 0; tr < TR; ++tr) {
            reset(nb);
            CK(cudaEventRecord(e0, st));
            if (cs) {
                cudaLaunchConfig_t cfg = {}; cfg.gridDim = nb; cfg.blockDim = NT; cfg.stream = st; cfg.dynamicSmemBytes = PAD;
                cudaLaunchAttribute at[1]; at[0].id = cudaLaunchAttributeClusterDimension; at[0].val.clusterDim.x = cs; at[0].val.clusterDim.y = 1; at[0].val.clusterDim.z = 1;
                cfg.attrs = at; cfg.numAttrs = 1;
                CK(cudaLaunchKernelEx(&cfg, k, steps, p));
            } else {
                void *args[] = {&steps, &p}; CK(cudaLaunchCooperativeKernel((const void *)k, nb, NT, args, PAD, st));
            }
            CK(cudaEventRecord(e1, st)); CK(cudaEventSynchronize(e1)); CK(cudaGetLastError());
            v.push_back(ms_between(e0, e1) * 1e6 / steps);
            unsigned h[2]; CK(cudaMemcpy(&h[0], p.err, 4, cudaMemcpyDeviceToHost)); CK(cudaMemcpy(&h[1], p.tmo, 4, cudaMemcpyDeviceToHost));
            errs += h[0]; tmo += h[1];
        }
        std::sort(v.begin(), v.end());
        printf("%s  {\"name\": \"%s\", \"what\": \"%s\", \"blocks\": %d, \"cluster\": %d, \"replicas\": %d, \"min_ns\": %.1f, \"median_ns\": %.1f, \"max_ns\": %.1f, \"min_cycles\": %.0f, \"min_l2_round_trips\": %.2f, \"data_errors\": %u, \"timeouts\": %u}",
               first ? "" : ",\n", name, what, nb, cs, rep, v.front(), v[v.size() / 2], v.back(), v.front() * ghz, v.front() * ghz / l2_cyc, errs, tmo);
        first = false; fflush(stdout);
    };
    const int nb = nsm;
    run("1a_counter_only", "single atomic counter arrive+poll, no data (dep_latency.cu)", k_counter_only, nb, 0);
    run("1b_counter_data", "counter barrier + every SM reads the 16 KiB vector (ld.cg)", k_counter_data, nb, 0);
    run("2a_ll8", "flag-in-data 8 B {fp32, tag}; poll = read of 32 KiB", k_ll8, nb, 0);
    run("2b_ll16", "flag-in-data 16 B {3 fp32, tag}; one 128 B line per producer", k_ll16<false>, nb, 0);
    run("2c_ll128", "flag-in-data 128 B line per producer (one warp store), tag in last 8 B", k_ll128, nb, 0);
    run("1c_counter_data_rep8", "1b with the vector written to 8 replicas (consumer b reads copy b%8)", k_counter_data, nb, 0, 8);
    run("1d_counter_data_rep16", "1b with 16 replicas", k_counter_data, nb, 0, 16);
    run("2d_ll16_rep8", "2b with every producer line written to 8 replicas", k_ll16<false>, nb, 0, 8);
    run("2e_ll16_rep16", "2b with 16 replicas", k_ll16<false>, nb, 0, 16);
    run("2f_ll16_light_rep8", "LL16, 8 replicas, light polling (one entry per producer line), then one full read", k_ll16_light, nb, 0, 8);
    run("2f_ll16_light_rep1", "LL16, one copy, light polling then one full read", k_ll16_light, nb, 0, 1);
    run("2x_read_plain_nodep_rep8", "no dependency: 16 KiB read, 8 replicas", k_read_plain, nb, 0, 8);
    run("2x_read_plain_nodep_rep16", "no dependency: 16 KiB read, 16 replicas", k_read_plain, nb, 0, 16);
    run("2y_read_ll16_nodep_rep16", "no dependency: LL16 read, 16 replicas", k_ll16<true>, nb, 0, 16);
    run("2x_read_plain_nodep_rep188", "no dependency: 16 KiB read, a private copy per SM (no hot lines)", k_read_plain, nb, 0, 188);
    run("2y_read_ll16_nodep_rep188", "no dependency: LL16 read, a private copy per SM", k_ll16<true>, nb, 0, 188);
    run("2x_read_plain_nodep", "no dependency: every SM reads a ready 16 KiB vector", k_read_plain, nb, 0);
    run("2y_read_ll16_nodep", "no dependency: every SM reads a ready LL16 vector (23.5 KiB)", k_ll16<true>, nb, 0);
    run("3a_flags_warp_packed", "per-producer flag after fence; warp 0 polls packed flags", k_flags<0>, nb, 0);
    run("3b_flags_warp_padded", "per-producer flag after fence; warp 0 polls 128 B-padded flags", k_flags<1>, nb, 0);
    run("3c_flags_thread_each", "per-producer flag after fence; one thread polls each flag", k_flags<2>, nb, 0);
    run("3d_sharded4_rep8", "4 counter shards (arrival spread over 4 lines), 8 data replicas", k_sharded<4>, nb, 0, 8);
    run("3d_sharded8_rep8", "8 counter shards, 8 data replicas", k_sharded<8>, nb, 0, 8);
    run("3d_sharded16_rep8", "16 counter shards, 8 data replicas", k_sharded<16>, nb, 0, 8);
    run("3d_sharded32_rep8", "32 counter shards, 8 data replicas", k_sharded<32>, nb, 0, 8);
    run("3d_sharded1_rep8", "1 shard (single counter, ld.acquire poll), 8 data replicas", k_sharded<1>, nb, 0, 8);
    run("3d_sharded8_rep1", "8 counter shards, one copy of the vector", k_sharded<8>, nb, 0, 1);
    run("4a_cluster8_flags", "slice, cluster.sync, leader fence + per-cluster flag, all poll", k_cluster_flags, 0, 8);
    run("4a_cluster16_flags", "as 4a with 16-block (non-portable) clusters", k_cluster_flags, 0, 16);
    run("4b_cluster8_ll16_dsmem", "LL16 via L2, each member polls 1/8 of the lines and pushes them to all 8 members over DSMEM, cluster.sync", k_cluster_ll16, 0, 8);
    run("4x_cluster8_sync_only", "reference: 8-block cluster.sync + 16 KiB DSMEM read from a peer, no global memory", k_dsmem_read, 0, 8);
    run("1b_counter_data_184", "1b at the cluster-8 grid size, for comparison", k_counter_data, 184, 0);
    run("2b_ll16_184", "2b at the cluster-8 grid size, for comparison", k_ll16<false>, 184, 0);
    run("5a_allreduce_red", "all-reduce 4096 fp32: red.add.v4 from every SM + counter + read", k_allreduce_red, nb, 0);
    run("5b_allreduce_cluster8", "DSMEM reduce-scatter in 8-SM cluster, red.add.v4, counter, read", k_allreduce_cluster, 0, 8);
    run("5c_allreduce_ll16", "LL16 reduce-scatter + LL16 all-gather (two hops, no atomics)", k_allreduce_ll16, nb, 0);
    printf("\n ],\n");

    // ---------------- 6. GEMV chain with DRAM weight stream
    if ((!only.empty() && only != "gemv") || V != 4096) { printf(" \"gemv_chain\": null\n}\n"); return 0; }
    const size_t nw = (size_t)NMAT * V * V;
    uint16_t *W; CK(cudaMalloc(&W, nw * 2));
    k_wgen<<<nsm * 4, 256, 0, st>>>(W, nw);
    std::vector<float> hx0(V); for (int i = 0; i < V; ++i) hx0[i] = xgen(i);
    float *x0, *ylog; CK(cudaMalloc(&x0, V * 4)); CK(cudaMalloc(&ylog, (size_t)G * V * 4));
    CK(cudaMemcpy(x0, hx0.data(), V * 4, cudaMemcpyHostToDevice));
    CK(cudaStreamSynchronize(st));
    // reference DRAM read bandwidth over the same buffer
    std::vector<double> bw;
    for (int tr = 0; tr < TR; ++tr) {
        CK(cudaEventRecord(e0, st)); k_bw<<<nsm * 4, 512, 0, st>>>((const uint4 *)W, nw * 2 / 16, p.sink); CK(cudaEventRecord(e1, st));
        CK(cudaEventSynchronize(e1)); bw.push_back(nw * 2 / (ms_between(e0, e1) * 1e-3) / 1e9);
    }
    std::sort(bw.begin(), bw.end());
    struct GV { const char *name, *what; void (*k)(const uint16_t *, int, int, const float *, float *, P); int mode, ns, base, rep; };
    p.rep = 1;
    GV gv[] = {
        {"6_stream_only_tma", "no dependency between GEMVs (pure TMA weight stream + compute)", k_gemv<0, true, true, 8>, 0, 8, -1, 1},
        {"6_counter_overlap_tma", "counter barrier gather, TMA stream continues across the boundary", k_gemv<1, true, true, 8>, 1, 8, 0, 1},
        {"6_counter_rep8_overlap_tma", "counter barrier gather from 8 replicas, TMA stream continues across the boundary", k_gemv<1, true, true, 8>, 1, 8, 0, 8},
        {"6_ll8_overlap_tma", "LL8 flag-in-data gather, TMA stream continues across the boundary", k_gemv<2, true, true, 8>, 2, 8, 0, 1},
        {"6_counter_drain_tma", "counter barrier gather, TMA stream drained at the boundary (no overlap)", k_gemv<1, false, true, 8>, 1, 8, 0, 1},
        {"6_ll8_drain_tma", "LL8 gather, TMA stream drained at the boundary (no overlap)", k_gemv<2, false, true, 8>, 2, 8, 0, 1},
        {"6_stream_only_drain_tma", "no dependency, TMA pipeline restarted per GEMV (fill cost only)", k_gemv<0, false, true, 8>, 0, 8, 0, 1},
        {"6_stream_only_tma_ring12", "as 6_stream_only_tma with a 12-row (96 KiB) ring", k_gemv<0, true, true, 12>, 0, 12, -1, 1},
        {"6_counter_overlap_tma_ring12", "counter gather, 12-row ring prefetched across the boundary", k_gemv<1, true, true, 12>, 1, 12, 7, 1},
        {"6_counter_rep8_overlap_tma_ring12", "counter gather from 8 replicas, 12-row ring", k_gemv<1, true, true, 12>, 1, 12, 7, 8},
        {"6_ll8_overlap_tma_ring12", "LL8 gather, 12-row ring prefetched across the boundary", k_gemv<2, true, true, 12>, 2, 12, 7, 1},
        {"6_dyn_stream_only_tma", "dynamic row claiming, no dependency (x fixed)", k_gemv_dyn<8, false>, 0, 8, -1, 1},
        {"6_dyn_ll8_overlap_tma", "dynamic row claiming across GEMVs + per-row LL8 outputs, TMA stream never drains", k_gemv_dyn<8, true>, 2, 8, 11, 1},
        {"6_dyn_ll8_overlap_tma_vs_static", "same kernel as 6_dyn_ll8_overlap_tma, exposed cost vs the static stream-only baseline", k_gemv_dyn<8, true>, 2, 8, 0, 1},
        {"6_dyn_ll8_overlap_tma_ring12", "dynamic claiming + LL8, 12-row ring", k_gemv_dyn<12, true>, 2, 12, 11, 1},
        {"6_stream_only_cpasync", "no dependency, per-thread 16 B cp.async stream", k_gemv<0, true, false, 8>, 0, 8, -1, 1},
        {"6_counter_overlap_cpasync", "counter barrier gather, cp.async stream across the boundary", k_gemv<1, true, false, 8>, 1, 8, 15, 1},
        {"6_ll8_overlap_cpasync", "LL8 gather, cp.async stream across the boundary", k_gemv<2, true, false, 8>, 2, 8, 15, 1},
    };
    const int NG = sizeof(gv) / sizeof(gv[0]);
    for (auto &g : gv) CK(cudaFuncSetAttribute((const void *)g.k, cudaFuncAttributeMaxDynamicSharedMemorySize, g.ns * 8192));
    std::vector<std::vector<double>> tv(NG);
    std::vector<std::vector<double>> bns(NG);
    std::vector<double> maxrel(NG, 0); std::vector<unsigned> tmos(NG, 0);
    std::vector<float> hy((size_t)G * V);
    for (int tr = 0; tr < TR; ++tr) {
        for (int gi = 0; gi < NG; ++gi) {        // interleaved so background load hits every variant alike
            reset(nsm); CK(cudaMemsetAsync(ylog, 0, (size_t)G * V * 4, st)); CK(cudaMemsetAsync(p.stat, 0, 64, st)); CK(cudaMemsetAsync(p.rowctr, 0, 4096 * 4, st));
            p.rep = gv[gi].rep;
            int Gv = G, nm = NMAT; void *args[] = {(void *)&W, &Gv, &nm, &x0, &ylog, &p};
            CK(cudaEventRecord(e0, st));
            CK(cudaLaunchCooperativeKernel((const void *)gv[gi].k, nsm, NT, args, (size_t)gv[gi].ns * 8192, st));
            CK(cudaEventRecord(e1, st)); CK(cudaEventSynchronize(e1)); CK(cudaGetLastError());
            tv[gi].push_back(ms_between(e0, e1) * 1e6 / G);
            unsigned h; CK(cudaMemcpy(&h, p.tmo, 4, cudaMemcpyDeviceToHost)); tmos[gi] += h;
            unsigned long long hs; CK(cudaMemcpy(&hs, p.stat, 8, cudaMemcpyDeviceToHost)); bns[gi].push_back(hs / ghz / ((double)nsm * G));
            if (tr == 0) {                          // check 256 rows of every GEMV against a double-precision reference
                CK(cudaMemcpy(hy.data(), ylog, hy.size() * 4, cudaMemcpyDeviceToHost));
                for (int g = 0; g < G; ++g) {
                    const float *xg = (gv[gi].mode == 0 || g == 0) ? hx0.data() : &hy[(size_t)(g - 1) * V];
                    for (int k = 0; k < 256; ++k) {
                        int row = k * 16 + (g % 16); double ref = 0, mag = 0;
                        size_t base = ((size_t)(g % NMAT) * V + row) * V;
                        for (int c = 0; c < V; ++c) { double w = bf2f(wgen(base + c)); ref += w * xg[c]; mag += fabs(w * xg[c]); }
                        double rel = fabs(hy[(size_t)g * V + row] - ref) / (mag + 1e-30);
                        maxrel[gi] = std::max(maxrel[gi], rel);
                    }
                }
            }
        }
    }
    printf(" \"dram_read_bw_gbs\": {\"max\": %.1f, \"median\": %.1f},\n", bw.back(), bw[bw.size() / 2]);
    printf(" \"gemv_chain\": {\"shape\": \"4096x4096 bf16 weights, fp32 activations, %d GEMVs per trial over %d matrices (%.0f MiB, > L2)\", \"blocks\": %d, \"ring_row_bytes\": 8192,\n  \"variants\": [\n",
           G, NMAT, nw * 2 / 1048576.0, nsm);
    for (int gi = 0; gi < NG; ++gi) {
        auto v = tv[gi]; std::sort(v.begin(), v.end()); auto bm = bns[gi]; std::sort(bm.begin(), bm.end());
        printf("   {\"name\": \"%s\", \"what\": \"%s\", \"ring_rows\": %d, \"min_ns_per_gemv\": %.1f, \"median_ns_per_gemv\": %.1f, \"max_ns_per_gemv\": %.1f, \"min_gbs\": %.1f, \"boundary_ns_in_kernel_median\": %.1f, \"check_max_rel_err\": %.2e, \"timeouts\": %u}%s\n",
               gv[gi].name, gv[gi].what, gv[gi].ns, v.front(), v[v.size() / 2], v.back(), (double)V * V * 2 / v.front(), bm[bm.size() / 2], maxrel[gi], tmos[gi], gi + 1 < NG ? "," : "");
    }
    // paired per-trial exposed cost against stream-only
    printf("  ],\n  \"exposed_ns_per_boundary\": {");
    for (int gi = 1, np = 0; gi < NG; ++gi) {
        const int base = gv[gi].base; if (base < 0) continue;
        std::vector<double> d; for (int tr = 0; tr < TR; ++tr) d.push_back(tv[gi][tr] - tv[base][tr]);
        std::sort(d.begin(), d.end());
        auto a = tv[gi], b = tv[base]; std::sort(a.begin(), a.end()); std::sort(b.begin(), b.end());
        printf("%s\n   \"%s\": {\"vs\": \"%s\", \"min_minus_min\": %.1f, \"median_paired\": %.1f}", np++ ? "," : "", gv[gi].name, gv[base].name, a.front() - b.front(), d[d.size() / 2]);
    }
    printf("\n  }\n }\n}\n");
    return 0;
}
