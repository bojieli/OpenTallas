// Dependent-operation boundary cost on a CUDA GPU.
//
// What a decode step pays per dependent operator boundary, measured four ways:
//   1. graph   : back-to-back empty kernels captured in a CUDA graph (launch gap)
//   2. pdl     : the same chain with Programmatic Dependent Launch
//                (programmaticStreamSerialization + cudaGridDependencySynchronize)
//   3. gridsync: one persistent cooperative kernel, grid.sync() between steps
//   4. flag    : one persistent kernel, fine-grained dependency through L2:
//                 pingpong -- one producer block, one consumer block on another SM
//                 counter  -- every block arrives on a counter, all wait for it
//                 (the megakernel pattern for "reduction done -> next op")
// Each mode reports ns per boundary over many boundaries, repeated; the runner
// keeps min and median. Build: nvcc -O3 -arch=sm_120 -rdc=true dep_latency.cu
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <algorithm>
#include <cuda_runtime.h>
#include <cooperative_groups.h>
namespace cg = cooperative_groups;

#define CK(x) do { cudaError_t e = (x); if (e != cudaSuccess) { \
    fprintf(stderr, "%s:%d %s\n", __FILE__, __LINE__, cudaGetErrorString(e)); exit(1); } } while (0)

__global__ void empty_kernel(int *sink) { if (sink && threadIdx.x == 9999) sink[0] = 1; }

__global__ void pdl_kernel(int *sink) {
#if __CUDA_ARCH__ >= 900
    cudaGridDependencySynchronize();
    cudaTriggerProgrammaticLaunchCompletion();
#endif
    if (sink && threadIdx.x == 9999) sink[0] = 1;
}

__global__ void gridsync_kernel(int steps, int *sink) {
    cg::grid_group g = cg::this_grid();
    for (int s = 0; s < steps; ++s) g.sync();
    if (sink && threadIdx.x == 9999) sink[0] = steps;
}

// One producer block (0) and one consumer block (1) ping-pong a flag `steps` times.
__global__ void pingpong_kernel(int steps, volatile int *flag) {
    if (threadIdx.x != 0) return;
    if (blockIdx.x == 0) {
        for (int s = 0; s < steps; ++s) {
            while (flag[0] != 2 * s) { }
            __threadfence();
            flag[0] = 2 * s + 1;
        }
    } else if (blockIdx.x == 1) {
        for (int s = 0; s < steps; ++s) {
            while (flag[0] != 2 * s + 1) { }
            __threadfence();
            flag[0] = 2 * s + 2;
        }
    }
}

// Every block arrives on a monotonically increasing counter and waits until all
// blocks of this step have arrived: the fine-grained "all producers done" dependency.
__global__ void counter_kernel(int steps, unsigned *counter) {
    const unsigned nb = gridDim.x;
    for (int s = 0; s < steps; ++s) {
        __syncthreads();
        if (threadIdx.x == 0) {
            __threadfence();
            atomicAdd(counter, 1u);
            const unsigned target = nb * (unsigned)(s + 1);
            while (atomicAdd(counter, 0u) < target) { }
            __threadfence();
        }
        __syncthreads();
    }
}


// Intra-SM dependency: one block, __syncthreads() per boundary.
__global__ void blocksync_kernel(int steps, int *sink) {
    for (int s = 0; s < steps; ++s) __syncthreads();
    if (sink && threadIdx.x == 9999) sink[0] = steps;
}
// Thread-block cluster dependency: cluster.sync() per boundary (distributed shared memory domain).
__global__ void __cluster_dims__(8, 1, 1) clustersync_kernel(int steps, int *sink) {
    cg::cluster_group c = cg::this_cluster();
    for (int s = 0; s < steps; ++s) c.sync();
    if (sink && threadIdx.x == 9999) sink[0] = steps;
}

static float ms_between(cudaEvent_t a, cudaEvent_t b) { float ms; CK(cudaEventElapsedTime(&ms, a, b)); return ms; }

int main(int argc, char **argv) {
    const int N = argc > 1 ? atoi(argv[1]) : 2000;        // boundaries per trial
    const int TRIALS = argc > 2 ? atoi(argv[2]) : 15;
    const int BLOCKS = argc > 3 ? atoi(argv[3]) : 0;       // 0 = one block per SM
    cudaDeviceProp p; CK(cudaGetDeviceProperties(&p, 0));
    const int nb = BLOCKS ? BLOCKS : p.multiProcessorCount;
    cudaStream_t st; CK(cudaStreamCreateWithFlags(&st, cudaStreamNonBlocking));
    cudaEvent_t e0, e1; CK(cudaEventCreate(&e0)); CK(cudaEventCreate(&e1));
    int *sink; CK(cudaMalloc(&sink, sizeof(int)));
    int *flag; CK(cudaMalloc(&flag, sizeof(int)));
    unsigned *counter; CK(cudaMalloc(&counter, sizeof(unsigned)));
    printf("{\"device\": \"%s\", \"sm\": \"%d.%d\", \"sms\": %d, \"blocks\": %d, \"boundaries_per_trial\": %d, \"trials\": %d,\n",
           p.name, p.major, p.minor, p.multiProcessorCount, nb, N, TRIALS);

    auto report = [&](const char *name, std::vector<double> v, bool last) {
        std::sort(v.begin(), v.end());
        printf("  \"%s_ns\": {\"min\": %.1f, \"median\": %.1f, \"max\": %.1f}%s\n", name, v.front(), v[v.size() / 2], v.back(), last ? "" : ",");
    };

    // 1. CUDA graph of N empty kernels (grid = nb blocks, like a real op).
    {
        cudaGraph_t g; cudaGraphExec_t ge;
        CK(cudaStreamBeginCapture(st, cudaStreamCaptureModeGlobal));
        for (int i = 0; i < N; ++i) empty_kernel<<<nb, 128, 0, st>>>(sink);
        CK(cudaStreamEndCapture(st, &g)); CK(cudaGraphInstantiate(&ge, g, 0));
        CK(cudaGraphLaunch(ge, st)); CK(cudaStreamSynchronize(st));
        std::vector<double> v;
        for (int t = 0; t < TRIALS; ++t) {
            CK(cudaEventRecord(e0, st)); CK(cudaGraphLaunch(ge, st)); CK(cudaEventRecord(e1, st));
            CK(cudaEventSynchronize(e1)); v.push_back(ms_between(e0, e1) * 1e6 / N);
        }
        report("graph_launch_gap", v, false);
    }
    // 2. PDL chain in a graph.
    {
        cudaLaunchAttribute at[1];
        at[0].id = cudaLaunchAttributeProgrammaticStreamSerialization;
        at[0].val.programmaticStreamSerializationAllowed = 1;
        cudaLaunchConfig_t cfg = {}; cfg.gridDim = nb; cfg.blockDim = 128; cfg.stream = st;
        cfg.attrs = at; cfg.numAttrs = 1;
        cudaGraph_t g; cudaGraphExec_t ge;
        CK(cudaStreamBeginCapture(st, cudaStreamCaptureModeGlobal));
        for (int i = 0; i < N; ++i) CK(cudaLaunchKernelEx(&cfg, pdl_kernel, sink));
        CK(cudaStreamEndCapture(st, &g)); CK(cudaGraphInstantiate(&ge, g, 0));
        CK(cudaGraphLaunch(ge, st)); CK(cudaStreamSynchronize(st));
        std::vector<double> v;
        for (int t = 0; t < TRIALS; ++t) {
            CK(cudaEventRecord(e0, st)); CK(cudaGraphLaunch(ge, st)); CK(cudaEventRecord(e1, st));
            CK(cudaEventSynchronize(e1)); v.push_back(ms_between(e0, e1) * 1e6 / N);
        }
        report("pdl_boundary", v, false);
    }
    // 3. Persistent cooperative kernel, grid.sync() per boundary.
    {
        int steps = N; void *args[] = {&steps, &sink};
        CK(cudaLaunchCooperativeKernel((void *)gridsync_kernel, nb, 128, args, 0, st)); CK(cudaStreamSynchronize(st));
        std::vector<double> v;
        for (int t = 0; t < TRIALS; ++t) {
            CK(cudaEventRecord(e0, st));
            CK(cudaLaunchCooperativeKernel((void *)gridsync_kernel, nb, 128, args, 0, st));
            CK(cudaEventRecord(e1, st)); CK(cudaEventSynchronize(e1));
            v.push_back(ms_between(e0, e1) * 1e6 / N);
        }
        report("persistent_grid_sync", v, false);
    }
    // 4a. Fine-grained ping-pong between two blocks (one boundary = one handoff).
    {
        std::vector<double> v;
        for (int t = 0; t < TRIALS; ++t) {
            CK(cudaMemsetAsync(flag, 0, sizeof(int), st));
            CK(cudaEventRecord(e0, st));
            pingpong_kernel<<<2, 32, 0, st>>>(N, flag);
            CK(cudaEventRecord(e1, st)); CK(cudaEventSynchronize(e1));
            v.push_back(ms_between(e0, e1) * 1e6 / (2.0 * N));
        }
        report("flag_pingpong_handoff", v, false);
    }
    // 4b. Fine-grained all-blocks counter dependency (every block waits for all).
    {
        std::vector<double> v;
        for (int t = 0; t < TRIALS; ++t) {
            CK(cudaMemsetAsync(counter, 0, sizeof(unsigned), st));
            CK(cudaEventRecord(e0, st));
            counter_kernel<<<nb, 128, 0, st>>>(N, counter);
            CK(cudaEventRecord(e1, st)); CK(cudaEventSynchronize(e1));
            v.push_back(ms_between(e0, e1) * 1e6 / N);
        }
        report("flag_counter_all_blocks", v, false);
    }
    // 5. Intra-SM barrier and 8-block cluster barrier.
    {
        std::vector<double> v, w;
        for (int t = 0; t < TRIALS; ++t) {
            CK(cudaEventRecord(e0, st)); blocksync_kernel<<<1, 128, 0, st>>>(N, sink);
            CK(cudaEventRecord(e1, st)); CK(cudaEventSynchronize(e1)); v.push_back(ms_between(e0, e1) * 1e6 / N);
            CK(cudaEventRecord(e0, st)); clustersync_kernel<<<8, 128, 0, st>>>(N, sink);
            CK(cudaEventRecord(e1, st)); CK(cudaEventSynchronize(e1)); w.push_back(ms_between(e0, e1) * 1e6 / N);
        }
        report("block_syncthreads", v, false);
        report("cluster8_sync", w, true);
    }
    printf("}\n");
    return 0;
}
