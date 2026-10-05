// Validation experiments for dep_latency.cu: decompose a cross-SM dependency
// into its microarchitectural parts and test the methodology.
//   clock        : SM clock during the run (clock64 vs %globaltimer)
//   l2_chase     : dependent pointer chase resident in L2 (single thread) -> L2 hit latency
//   dram_chase   : same over a footprint far larger than L2 -> DRAM latency
//   fence        : cost of __threadfence (membar.gl) vs fence.acq_rel.gpu
//   atomic_one   : N threads' atomics serialised on one address (per-atomic L2 throughput)
//   pp_relacq    : ping-pong with st.release.gpu / ld.acquire.gpu, no membar (one-way)
//   pp_fence     : ping-pong with volatile + __threadfence (as in v1)
//   bar_atomic   : all-SM barrier, arrive = atomicAdd, wait = atomic polling (as in v1)
//   bar_ldacq    : all-SM barrier, arrive = red.release, wait = ld.acquire polling
//   bar_tree     : per-SM arrival flags, block 0 gathers and broadcasts a generation
//   bar_cluster  : hierarchical: cluster.sync (8 SMs), then one atomic per cluster
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <algorithm>
#include <cuda_runtime.h>
#include <cooperative_groups.h>
namespace cg = cooperative_groups;
#define CK(x) do { cudaError_t e = (x); if (e != cudaSuccess) { fprintf(stderr, "%s:%d %s\n", __FILE__, __LINE__, cudaGetErrorString(e)); exit(1); } } while (0)

__device__ __forceinline__ unsigned long long gtimer() { unsigned long long t; asm volatile("mov.u64 %0, %%globaltimer;" : "=l"(t)); return t; }
__device__ __forceinline__ void st_release(unsigned *p, unsigned v) { asm volatile("st.release.gpu.global.u32 [%0], %1;" :: "l"(p), "r"(v) : "memory"); }
__device__ __forceinline__ unsigned ld_acquire(const unsigned *p) { unsigned v; asm volatile("ld.acquire.gpu.global.u32 %0, [%1];" : "=r"(v) : "l"(p) : "memory"); return v; }
__device__ __forceinline__ void red_release_add(unsigned *p, unsigned v) { asm volatile("red.release.gpu.global.add.u32 [%0], %1;" :: "l"(p), "r"(v) : "memory"); }

__global__ void clock_kernel(unsigned long long *out) {
    unsigned long long c0 = clock64(), t0 = gtimer();
    while (gtimer() - t0 < 2000000ull) { }            // 2 ms
    out[0] = clock64() - c0; out[1] = gtimer() - t0;
}
__global__ void chase_kernel(const unsigned *next, int steps, unsigned *sink, unsigned long long *cyc) {
    unsigned i = 0;
    unsigned long long c0 = clock64();
    for (int s = 0; s < steps; ++s) i = __ldcg(next + i);   // cache-global: bypass L1, hit L2
    cyc[0] = clock64() - c0; sink[0] = i;
}
__global__ void fence_kernel(int steps, int mode, unsigned long long *cyc, unsigned *buf) {
    unsigned long long c0 = clock64();
    for (int s = 0; s < steps; ++s) {
        buf[0] = s;                                   // a store the fence must order
        if (mode == 0) __threadfence(); else asm volatile("fence.acq_rel.gpu;" ::: "memory");
    }
    cyc[mode] = clock64() - c0;
}
__global__ void atomic_one_kernel(unsigned *ctr) { if (!threadIdx.x) atomicAdd(ctr, 1u); }

__global__ void pp_relacq(int steps, unsigned *flag) {
    if (threadIdx.x) return;
    for (int s = 0; s < steps; ++s) {
        unsigned want = blockIdx.x == 0 ? 2u * s : 2u * s + 1u;
        while (ld_acquire(flag) != want) { }
        st_release(flag, want + 1u);
    }
}
__global__ void pp_fence(int steps, volatile unsigned *flag) {
    if (threadIdx.x) return;
    for (int s = 0; s < steps; ++s) {
        unsigned want = blockIdx.x == 0 ? 2u * s : 2u * s + 1u;
        while (flag[0] != want) { }
        __threadfence(); flag[0] = want + 1u;
    }
}
__global__ void bar_atomic(int steps, unsigned *ctr) {
    for (int s = 0; s < steps; ++s) {
        __syncthreads();
        if (!threadIdx.x) { __threadfence(); atomicAdd(ctr, 1u); unsigned t = gridDim.x * (s + 1u); while (atomicAdd(ctr, 0u) < t) { } __threadfence(); }
        __syncthreads();
    }
}
__global__ void bar_ldacq(int steps, unsigned *ctr) {
    for (int s = 0; s < steps; ++s) {
        __syncthreads();
        if (!threadIdx.x) { red_release_add(ctr, 1u); unsigned t = gridDim.x * (s + 1u); while (ld_acquire(ctr) < t) { } }
        __syncthreads();
    }
}
// flags: one 128-byte line per block (index b*32); gen at flags[nb*32]
__global__ void bar_tree(int steps, unsigned *flags) {
    const unsigned nb = gridDim.x; unsigned *gen = flags + nb * 32;
    for (int s = 0; s < steps; ++s) {
        __syncthreads();
        if (blockIdx.x == 0) {
            if (threadIdx.x < nb - 1 && threadIdx.x < blockDim.x) {
                // each thread of block 0 waits on some blocks' flags
            }
            for (unsigned b = 1 + threadIdx.x; b < nb; b += blockDim.x) while (ld_acquire(flags + b * 32) != (unsigned)(s + 1)) { }
            __syncthreads();
            if (!threadIdx.x) st_release(gen, s + 1);
        } else if (!threadIdx.x) {
            st_release(flags + blockIdx.x * 32, s + 1);
            while (ld_acquire(gen) != (unsigned)(s + 1)) { }
        }
        __syncthreads();
    }
}
__global__ void __cluster_dims__(8, 1, 1) bar_cluster(int steps, unsigned *ctr) {
    cg::cluster_group c = cg::this_cluster();
    const unsigned nclusters = gridDim.x / 8;
    for (int s = 0; s < steps; ++s) {
        c.sync();
        if (c.block_rank() == 0 && !threadIdx.x) { red_release_add(ctr, 1u); unsigned t = nclusters * (s + 1u); while (ld_acquire(ctr) < t) { } }
        c.sync();
    }
}

static float ms_between(cudaEvent_t a, cudaEvent_t b) { float ms; CK(cudaEventElapsedTime(&ms, a, b)); return ms; }

int main(int argc, char **argv) {
    const int N = argc > 1 ? atoi(argv[1]) : 20000, TR = argc > 2 ? atoi(argv[2]) : 9;
    cudaDeviceProp p; CK(cudaGetDeviceProperties(&p, 0));
    const int nsm = p.multiProcessorCount, nb = (nsm / 8) * 8;   // cluster-friendly grid
    cudaStream_t st; CK(cudaStreamCreateWithFlags(&st, cudaStreamNonBlocking));
    cudaEvent_t e0, e1; CK(cudaEventCreate(&e0)); CK(cudaEventCreate(&e1));
    unsigned long long *dc; CK(cudaMalloc(&dc, 64)); unsigned *du; CK(cudaMalloc(&du, (nb + 2) * 128)); unsigned *sink; CK(cudaMalloc(&sink, 64));
    unsigned long long hc[4];
    printf("{\"device\": \"%s\", \"sms\": %d, \"l2_bytes\": %d, \"grid_blocks\": %d,\n", p.name, nsm, p.l2CacheSize, nb);
    // clock
    clock_kernel<<<1, 1, 0, st>>>(dc); CK(cudaStreamSynchronize(st)); CK(cudaMemcpy(hc, dc, 16, cudaMemcpyDeviceToHost));
    double ghz = (double)hc[0] / (double)hc[1];
    printf("  \"sm_clock_ghz\": %.3f,\n", ghz);
    // pointer chases: random cyclic permutation over the footprint, stride of a 128 B line
    auto chase = [&](size_t bytes, const char *name) {
        size_t n = bytes / 128; std::vector<unsigned> perm(n), nxt(n * 32, 0);
        for (size_t i = 0; i < n; ++i) perm[i] = i;
        srand(7); for (size_t i = n - 1; i > 0; --i) std::swap(perm[i], perm[rand() % (i + 1)]);
        for (size_t i = 0; i < n; ++i) nxt[perm[i] * 32] = perm[(i + 1) % n] * 32;
        unsigned *d; CK(cudaMalloc(&d, n * 128)); CK(cudaMemcpy(d, nxt.data(), n * 128, cudaMemcpyHostToDevice));
        int steps = 200000;
        chase_kernel<<<1, 1, 0, st>>>(d, steps, sink, dc); CK(cudaStreamSynchronize(st));   // warm
        chase_kernel<<<1, 1, 0, st>>>(d, steps, sink, dc); CK(cudaStreamSynchronize(st)); CK(cudaMemcpy(hc, dc, 8, cudaMemcpyDeviceToHost));
        double cyc = (double)hc[0] / steps;
        printf("  \"%s\": {\"footprint_mb\": %.1f, \"cycles\": %.1f, \"ns\": %.1f},\n", name, bytes / 1048576.0, cyc, cyc / ghz);
        CK(cudaFree(d));
    };
    chase((size_t)256 << 10, "chase_256KB");
    chase((size_t)2 << 20, "chase_2MB");
    chase((size_t)8 << 20, "chase_8MB");
    chase((size_t)32 << 20, "chase_32MB");
    chase((size_t)2048 << 20, "chase_2GB_dram");
    // fences
    fence_kernel<<<1, 1, 0, st>>>(20000, 0, dc, sink); fence_kernel<<<1, 1, 0, st>>>(20000, 1, dc, sink);
    CK(cudaStreamSynchronize(st)); CK(cudaMemcpy(hc, dc, 16, cudaMemcpyDeviceToHost));
    printf("  \"fence_after_store\": {\"membar_gl_cycles\": %.1f, \"fence_acq_rel_gpu_cycles\": %.1f},\n", hc[0] / 2e4, hc[1] / 2e4);
    // atomics to one address from nb*128 threads
    {
        std::vector<double> v;
        for (int t = 0; t < TR; ++t) {
            CK(cudaMemsetAsync(du, 0, 4, st)); CK(cudaEventRecord(e0, st));
            for (int r = 0; r < 100; ++r) atomic_one_kernel<<<nb, 128, 0, st>>>(du);
            CK(cudaEventRecord(e1, st)); CK(cudaEventSynchronize(e1));
            v.push_back(ms_between(e0, e1) * 1e6 / (100.0 * nb));
        }
        std::sort(v.begin(), v.end());
        printf("  \"atomic_one_per_block_same_address_ns_per_kernel_block\": {\"min\": %.3f, \"median\": %.3f},\n", v.front(), v[v.size() / 2]);
    }
    auto timed = [&](const char *name, auto launch, double per, bool last) {
        std::vector<double> v;
        for (int t = 0; t < TR; ++t) {
            CK(cudaMemsetAsync(du, 0, (nb + 2) * 128, st)); CK(cudaEventRecord(e0, st)); launch();
            CK(cudaEventRecord(e1, st)); CK(cudaEventSynchronize(e1)); v.push_back(ms_between(e0, e1) * 1e6 / per);
        }
        std::sort(v.begin(), v.end());
        printf("  \"%s_ns\": {\"min\": %.1f, \"median\": %.1f, \"min_cycles\": %.0f}%s\n", name, v.front(), v[v.size() / 2], v.front() * ghz, last ? "" : ",");
    };
    timed("pp_fence_oneway", [&] { pp_fence<<<2, 32, 0, st>>>(N, du); }, 2.0 * N, false);
    timed("pp_relacq_oneway", [&] { pp_relacq<<<2, 32, 0, st>>>(N, du); }, 2.0 * N, false);
    timed("bar_atomic", [&] { bar_atomic<<<nb, 128, 0, st>>>(N, du); }, N, false);
    timed("bar_ldacq", [&] { bar_ldacq<<<nb, 128, 0, st>>>(N, du); }, N, false);
    timed("bar_tree", [&] { bar_tree<<<nb, 128, 0, st>>>(N, du); }, N, false);
    timed("bar_cluster_hier", [&] { bar_cluster<<<nb, 128, 0, st>>>(N, du); }, N, true);
    printf("}\n");
    return 0;
}
