# Model weight/KV traffic screen

This is a hardware-independent ordinary-decode traffic calculation. It
answers how many active weight bytes are read for each mutable KV byte at
a given context and batch; it does **not** predict ROM/GPU speedup.

```text
R_read(B,L)  = active_weight_bytes(B) / (B × KV_read_bytes(L))
R_total(B,L) = active_weight_bytes(B) / (B × (KV_read_bytes(L) + KV_write_bytes))
```

## Raw traffic inputs

B1 weight traffic reflects expected routed-expert coverage. KV values are
per user and per generated token. Decimal GB/MB are used.

| Model | Context | B1 active weight | KV read/user/token | KV write/user/token |
|---|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 8,192 | 11.218 GB | 13.148 MB | 0.029 MB |
| DeepSeek-V4-Flash-0731 | 32,768 | 11.218 GB | 24.160 MB | 0.029 MB |
| DeepSeek-V4-Flash-0731 | 200,000 | 11.218 GB | 99.102 MB | 0.029 MB |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 11.218 GB | 457.577 MB | 0.029 MB |
| DeepSeek-V4-Pro-0813 | 8,192 | 39.667 GB | 27.796 MB | 0.041 MB |
| DeepSeek-V4-Pro-0813 | 32,768 | 39.667 GB | 43.800 MB | 0.041 MB |
| DeepSeek-V4-Pro-0813 | 200,000 | 39.667 GB | 152.710 MB | 0.041 MB |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 39.667 GB | 673.666 MB | 0.041 MB |
| Kimi-K3 | 8,192 | 136.990 GB | 562.618 MB | 449.386 MB |
| Kimi-K3 | 32,768 | 136.990 GB | 902.357 MB | 449.386 MB |
| Kimi-K3 | 200,000 | 136.990 GB | 3,214.172 MB | 449.386 MB |
| Kimi-K3 | 1,000,000 | 136.990 GB | 14,273.372 MB | 449.386 MB |

## Weight / KV-read ratio

| Model | Context | B1 | B8 | B32 | B64 |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 8,192 | 853.17× | 315.66× | 204.49× | 145.79× |
| DeepSeek-V4-Flash-0731 | 32,768 | 464.30× | 171.78× | 111.28× | 79.34× |
| DeepSeek-V4-Flash-0731 | 200,000 | 113.19× | 41.88× | 27.13× | 19.34× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 24.52× | 9.07× | 5.88× | 4.19× |
| DeepSeek-V4-Pro-0813 | 8,192 | 1,427.04× | 558.22× | 396.00× | 308.51× |
| DeepSeek-V4-Pro-0813 | 32,768 | 905.63× | 354.25× | 251.31× | 195.79× |
| DeepSeek-V4-Pro-0813 | 200,000 | 259.75× | 101.61× | 72.08× | 56.16× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 58.88× | 23.03× | 16.34× | 12.73× |
| Kimi-K3 | 8,192 | 243.49× | 67.84× | 41.38× | 30.58× |
| Kimi-K3 | 32,768 | 151.81× | 42.30× | 25.80× | 19.07× |
| Kimi-K3 | 200,000 | 42.62× | 11.87× | 7.24× | 5.35× |
| Kimi-K3 | 1,000,000 | 9.60× | 2.67× | 1.63× | 1.21× |

## Weight / (KV-read + write) ratio

| Model | Context | B1 | B8 | B32 | B64 |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V4-Flash-0731 | 8,192 | 851.32× | 314.97× | 204.05× | 145.48× |
| DeepSeek-V4-Flash-0731 | 32,768 | 463.75× | 171.58× | 111.15× | 79.25× |
| DeepSeek-V4-Flash-0731 | 200,000 | 113.16× | 41.87× | 27.12× | 19.34× |
| DeepSeek-V4-Flash-0731 | 1,000,000 | 24.51× | 9.07× | 5.88× | 4.19× |
| DeepSeek-V4-Pro-0813 | 8,192 | 1,424.96× | 557.40× | 395.43× | 308.06× |
| DeepSeek-V4-Pro-0813 | 32,768 | 904.79× | 353.93× | 251.08× | 195.61× |
| DeepSeek-V4-Pro-0813 | 200,000 | 259.68× | 101.58× | 72.06× | 56.14× |
| DeepSeek-V4-Pro-0813 | 1,000,000 | 58.88× | 23.03× | 16.34× | 12.73× |
| Kimi-K3 | 8,192 | 135.37× | 37.71× | 23.00× | 17.00× |
| Kimi-K3 | 32,768 | 101.34× | 28.24× | 17.22× | 12.73× |
| Kimi-K3 | 200,000 | 37.39× | 10.42× | 6.35× | 4.70× |
| Kimi-K3 | 1,000,000 | 9.30× | 2.59× | 1.58× | 1.17× |

## Interpretation boundary

- DeepSeek cache layout/precision and tensor topology follow pinned official artifacts; packing overhead is derived.
- Kimi topology is pinned, while KDA retained-state precision and optimized gated-MLA cache representation remain explicit assumptions in the model profile.
- Uniform independent expert routing determines expected expert coverage; production router traces are unavailable.
- Ratios are traffic screens, not speedup predictions.
- The ratio falls with context because mutable attention/state traffic
  grows, and falls with batch because GPU weight reads are amortized
  while KV traffic scales per user.
- ROM can exploit a large ratio only if its array, compute, NoC, power,
  and package can service the corresponding bytes; those are separate
  constraints in the iso-node reports.
