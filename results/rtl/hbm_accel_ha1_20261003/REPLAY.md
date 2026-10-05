# HA1 matched transaction-count / W6 live-feedback milestone

Parent: `8564e79ea`. Owner: Codex HA1 (Herschel). New RTL namespace:
`rtl/hbm_accel/txcount/`. No pinned SM/W6, ablation, issuer, drain, or canonical
full-token file is changed. The model ladder is an unvalidated hypothesis.

The counter has an opt-in `ENABLE` parameter, off by default. The compiler
lowering returns no manifest unless explicitly enabled. It admits a frozen
rank/job(tag)/generation and 1–32 unique owner55 identities. An actual accepted
common W4 ACK and an actual accepted W6 visibility event must each match the
frozen context and manifest identity/index, exactly once. Two independent event
ports can advance on one edge. Completion backpressure holds context/counts;
missing events never mature with time. Invalid/stale/duplicate events quarantine
before simultaneous completion. Runtime reset retains active debt and faults;
only coordinated cold POR clears it. This is scheduler visibility, never RF
lease release, issuer frame retirement, consumer completion or W6 drain.

`ot_hbm_txcount_tap` observes guarded `rf_ack_accept`, `rf_ack_owner55`, and W6
`visible_valid && visible_ready` / `visible_identity`. The caller must supply
actual retained rank/job/generation and the frozen manifest index. This is an
integration contract, not an installed canonical mapping. Euclid owns that
issuer / RF drain mapping; Hubble owns separate serial / CDC work. No timer,
private clock or speculative owner retirement is a source of arrivals.

The W6 candidate uses a triplicated live state to remove decoded data from the
state-data feedback, with the original SECDED witness checked before release.
One live-copy upset is majority-corrected; a witness UE or majority/witness
mismatch quarantines immediately and retains debt. It adds 213 live flops per
instance and zero protocol cycles; it does not halve initiation rate. Syndrome
and quarantine still gate control enables: the 429 MHz clock defect is **not
qualified as repaired**. A late unchecked SECDED check was not introduced.

Pricing precedes RTL in the branch history. Portbook derives DFF area and wire
cycles from exact `tools/uarch_model.py` definitions using an AST subset, avoiding
unrelated physical-result imports in a sparse checkout. Storage-only area,
unmeasured codecs/muxes/counters, routing capacity and full die fit remain
ESTIMATE and block adoption. The initial empty price record was replaced with a
valid JSON price *before any RTL commit or build*; branch history retains it.

Run from a clean pinned checkout with Icarus available:

```
python3 tools/hbm_accel/txcount_price.py
python3 tools/hbm_accel/run_txcount.py --out /tmp/ha1-fresh-unique-run
```

The runner reuses every original W6 mutation/reset/fence case unchanged in a
generated successor bench, adding live-copy mutations. The actual composition
instantiates the existing archived W4 two-mirror SRAM RF, takes its actual common
ACK, then takes the W6 visible handshake and the scheduler completion on a
positive following edge. Source-drain levels are fixture inputs; this gives no
production CDC or refresh qualification. Both RF copies are read back exactly.

R1 (`230761c3b`, agidock128 PID419910) preserved: counter sampling race FAILED;
actual W4/W6 and both W6 suites PASSED. R2 (`aacae8b23`, PVE1 PID2378773) all
compiles/runs exit 0: counter141, actual14, originalW6 611, successorW6 621 checks.
The idle agidock128 r2 admission waiter PID422124 was retired before any job
started after available memory fell below the 12 GiB reserve plus request. PVE1
had 46 GiB available, load18.5, and was admitted for this small replay. No
progressing job was stopped and no EPYC/GPU/inference job was launched.

Local measurement: actual ACK→accepted scheduler completion **8 cycles**, of
which **5 cycles are deliberately held visibility backpressure**; actual W6
visibility handshake→accepted scheduler completion **1 cycle**. These are
fixture measurements at a 1 ns simulation cycle. Conversion to the *hypothetical*
1.2 GHz clock is 6.667 / 0.833 ns; no achieved clock is claimed. Wire stages,
CDC, credits and refresh are not included. The existing archived barrier network
references remain Qwen48 / V4.1 62 cycles; the study's full-boundary78→47 target
has not been measured here and is not replaced by the local numbers.

Adoption: **false**. G-exact on the real program, serial G-latency, composed
G-area, routed corridor G-route, contextual SS60/FF25 G-timing and composed
G-gain≥1% are all open. No P&R is launched before the required earlier gates.
Failures and all historical evidence remain immutable. See `milestone.json` and
`r1/terminal.json`, `r2/terminal.json` for source pins and terminal evidence.

Measured-composition ledger: HA1 | local protocol PASS | full serial gain
UNMEASURED | area ESTIMATE | route/timing UNMEASURED | excluded from headline.
