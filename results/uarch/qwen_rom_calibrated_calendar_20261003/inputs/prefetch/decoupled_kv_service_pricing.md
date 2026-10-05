# Decoupled cross-layer KV service: pricing (model only, not adopted)

Base: origin/main 7baca4be1. Script: `work/decoupled.py`. It runs one 36-layer event loop, and its per-cohort logic is copied from `credit_layer_calendar`. In `all_grants` mode it reproduces the baseline exactly: **361.0713 us**.

## 1. Why the next layer waits: policy, not data and not storage
- `tools/uarch_model_qwen_kv_successor.py:312` sets `begin = max(t, windows[l%2])`. Here `t` is when the previous layer's last reverse grant retires (`credit_allocator.py:108,152`).
- Each layer is one lease. `credit_allocator.py:69-73` builds fresh cursors, credits and owner slots for each layer, and `:150-151` requires every debt to retire before the layer returns. The lease is stated in `successor.py:366` ("next prefetch starts after previous service drains; no early cross-layer ownership") and declared in `credit17.py:180`.
- The only data gates are the KW/VW writes (`:113,:143`) and the current-V tail (`:140`), which wait for prefix(l) = compute(l-1) + 451 cycles. Past-position K/V reads wait only for `begin`.
- The storage gate is the two 54-row tile windows (`parent_context.py:335-342,440-445`; KV_AW=7 gives 128 rows). It never binds.

## 2. Storage
- Landing storage already exists. Layer l+1 fills window (l+1)%2 while layer l's attention reads the other window. Each window is 5.31 MB per die; one layer of KV is 4.19 MB per die.
- What limits the rate is storage for data **in flight**. At a 566 ns mean credit hold, Little's law needs:
  - 138 cohorts (277 KB) to run at the command-bus floor;
  - 151 cohorts (305 KB) to run at the fill floor.
- The model provides 128 cohorts (256 KB), 64 pending entries per PC and 80 words per pool. All three are at their peak.
- In the model, attention waits for the whole layer to be filled (`successor.py:314`). The compute chain (2.56–4.53 us after fill) is shorter than the service pitch (9.6 us), so streaming attention would only shorten the last-layer tail.

## 3. The candidate: hand the lease over when layer l issues its last request
| compute assumption | control (us) | candidate (us) | rate gain | pitch (us/layer) |
|---|---|---|---|---|
| (a) model, 3,338 cycles | 361.0713 | 350.2673 | **+3.08%** | 9.91 → 9.59 |
| (b0) measured, 4,668 cycles at position 0 | 362.0282 | 351.1532 | +3.10% | 9.91 → 9.59 |
| (b8K) 4,668 + 1,220 cycles (unmeasured) | 366.4228 | 362.2088 | +1.16% | 10.00 → 9.88 |

**Binding constraint:** finite in-flight credits. The 128 global and 16 per-group cohorts, which equal 64 pending entries per PC, are all at peak. Little's law then gives a pitch of at least 9.22 us per layer. That is above the command-bus pitch (8.56 us) and the fill-lane pitch (7.82 us). Under the 8K compute, head-0 KW/VW and the current-V tail also stall the per-group order on prefix.

The **compute chain** (140 / 168 / 177 us) never binds; service binds in all cases.

**Floors:**
- Fill lanes: 281.4 us (aggregate 280.6 us).
- Command bus: **308.16 us**. This is 4 paths per stack × 4 stacks at 1 command per ns (`successor.py:109-113`), carrying 4.93 M commands. So the 280.6 us floor cannot be reached with the existing ports.
- Token bound with unlimited in-flight storage: 313.5 / 314.5 / 315.5 us, at most +15.2% / +15.1% / +16.2%.

## 4. Extra storage
- **Zero extra storage:** +3.08% under the model compute (+3.10% at position 0, +1.16% at 8K).
- **One extra layer of staging (a third tile window):** **0 gain**, because the window gate never binds. It costs 2 × 128x256 macros per tile, which is 11.95 mm² per die against 3.38 mm² remaining. It does not fit.
- **More in-flight capacity instead:** 144 / 18 / 72 / 90 is about 1.5 mm², estimated by scaling the credit17 cells. This was not run, and its gain is at most the floor above. Hold time rises with depth: credit17 gained only 0.69%.

## 5. Unqualified
The following are not qualified by this model:
- sustained PHY bandwidth;
- loaded routes and the Ampere channels;
- the 1.0/1.2 GHz CDC;
- the cross-layer epoch/lease RTL, i.e. two layer epochs live at once in credits, pending entries and owner slots;
- producer early release;
- strict refresh under continuous service.

The calibration is applied as a uniform per-layer `rest`. The non-layer extra stays at the model's 2.637 us.

The overlap assumed: attention(l) starts at max(fill_end(l), prefix(l)), and service runs under compute.
