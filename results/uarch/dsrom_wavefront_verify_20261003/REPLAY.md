# Replay: dsrom_wavefront_verify_20261003

Model only (no GPU, no inference). Branch base: ba4dc1a18 (scenario C record).

```bash
python3 tools/dsrom_wavefront_verify.py run       # ~1-2 min: raw.json (cons_v41_rom S58/S73 x 1M/200K, record settings, 4 stacks)
python3 tools/dsrom_wavefront_verify.py compose   # seconds: model.json
```

## What `run` captures

`run` wraps `_cons_adjust`, `_cons_occupancy`, `_cons_windows` and `v41_rom_ledger` while `cons_v41_rom` runs, and records:
- **T1 / Tp:** the AR and verify-pass critical paths;
- **per-stage occupancy:** field and hub issue, for AR and for the verify pass (the verify head includes the draft);
- **per-stage windows:** the critical-path contribution of each stage;
- **energy categories:** the per-die categories.

The die settings are those of `dsrom_return_storage_hbm.py run`, which uses the S58 die for both S58 and S73.

## Checks

- **S58 at 1M:** the run reproduces the scenario C record's model, 2,535.5 tok/s with Tp 932.97 µs. The record's figure is 928.64 + 4.34.
- **Scenario C AR:** the headline uses the record's composed AR, 2,489.9 at 1M and 2,599.9 at 200K. The direct S73 run gives 2,480.1 and 2,589.3, within 0.4%.
- **Wavefront:** verify = AR_C + 5 × II, and step = verify + 0.1173 × AR_C. The II comes from the direct S73 run.
