# Required RDPAIR native leaf seams

This fleet-only component augments the existing XRT/RSTOPT/VP native-pair
mechanism with the actual production slice relay module and full relay record
widths. Its only cases are the local, typed-V and adjacent horizontal paths
required by the 29-leg native transport plan, plus one typed-V payload-bit
corruption control. It contains no replacement arithmetic or memory model.

The source inventory is inherited from the passing real-VP KV component, with
shared hashes checked before build. Added XRT, RSTOPT, slice and testbench files
are pinned independently. The installed Verilator NBA guard must pass before
results are accepted. All inputs and observations have fixed, finite ages.

```sh
python3 tools/s81_dv/rdpair_leaf4_1021/gate.py --baseline /absolute/real_vp_run --out /absolute/new_run
```

Run only on the admitted fleet. A new output directory preserves earlier
attempts. `--resume-objects /absolute/prior_run/obj` checks source identity and
resumes existing generated make objects with two compiler processes. The
sealed single-run receipt is `results/token_pass/s81_native_pair_leaf4_1021`.
