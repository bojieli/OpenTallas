# Regenerated svc closure reference (DIE-S81-56/PLAN 11-05, S81-066)

The class transforms name nets of the T7 bound 61c902f1. 1ec013265f (dsdv_svc_att.sv: one line added, two `inside`
predicates lowered) moved every src_<hash> name and the plain N_Y numbers behind it, so all 16 svc types refused
(`reference net 719_Y not structurally mapped`).

`tools/die_plan/s81_svc_ref_regen.py <pristine T7 bound> <out>` writes:
- `ref_t7_bound.sv.gz`: the pristine T7 bound of the fresh strict bind, the reference for `name_map`;
- `ref_map.json`: old -> new for the tokens the four transforms use (hash 16, att 26, eng 1, procmux 14), and the proof;
- `residual.txt`: the 61c902f1 bound renamed by the map against the new reference, as line multisets. It holds the
  source change, the plan-side changes of the bound, and nets next to them that the pairing did not resolve. No token
  the transforms use appears in it.

Proof logic of the transforms is unchanged: the map only renames, and it refuses a token it does not have. The T7
self-check still reproduces 12605dc2 byte-exactly from 61c902f1, and the chain on the new reference leaves the same
residual as its preimage. `gate_1105.out` is the MEM v2 gate rerun (pos + 5 mutants).

When a source move makes the types refuse again, rerun the tool on a pristine T7 bound and commit the new files. If a
source shift other than dsdv_svc_att.sv:451:+1 is involved, pass it with `--old-line-shift`.
