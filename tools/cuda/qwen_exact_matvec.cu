// Host simulation only. No FMA, reassociation, TF32 or flush-to-zero.
// Compile with --fmad=false --ftz=false; explicit RN intrinsics are intentional.
__device__ __forceinline__ float positive_zero(float x) {
    return x == 0.0f ? 0.0f : x;
}
extern "C" __global__ void qwen_serial_k(
    const float *w, const float *xb, float *partials,
    long long kc, long long split, long long n,
    long long sk, long long ss, long long sn) {
    const long long t = (long long)blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= split * n) return;
    const long long s = t / n, row = t % n;
    float acc = 0.0f;
    for (long long k = 0; k < kc; ++k) {
        const float product = positive_zero(__fmul_rn(w[k*sk+s*ss+row*sn], xb[s*kc+k]));
        acc = positive_zero(__fadd_rn(acc, product));
    }
    partials[t] = acc;
}
extern "C" __global__ void qwen_split_pair(
    const float *in, float *out, long long pairs, long long n) {
    const long long t = (long long)blockIdx.x * blockDim.x + threadIdx.x;
    if (t >= pairs * n) return;
    const long long s = t / n, row = t % n;
    out[t] = positive_zero(__fadd_rn(in[(2*s)*n+row], in[(2*s+1)*n+row]));
}
