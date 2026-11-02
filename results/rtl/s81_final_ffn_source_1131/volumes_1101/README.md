# S81 down-projection field volumes (collected 2026-11-01 18:55 PST by TOK-DS-2)

Both Codex volumes ran to the end on intel1; data stays at intel1:/srv/opentallas-scratch2/claude/codex-ds-compiler-1101/<volume>/u_f_*.

| volume | status | results | failures | images | rank0 rows |
|---|---|---|---|---|---|
| down_aligned_fields_1131 (unit oth-ubuntu-608990) | PASS_RANK0_SOURCE_FIELDS_BF_UNQUALIFIED | 72 (70 aligned + 2 reused) | 0 | 12012 | 8960 |
| down_cap_safe_fields_1131 (unit oth-ubuntu-3333930) | PASS_RANK0_CAP_SAFE_SINGLE_FRAME_IMAGES_BF_UNQUALIFIED | 72 (71 + 1 reused) | 0 | 12012 | 8960 |

Scope (from the manifests): rank0 source images only, BF measurement empty, production_enabled false. CAP-safe is
single-frame FIN safe only: no simultaneous-frame, native CW, state, lease or mission admission. The aligned volume keeps the
old CAP assignments (source/address/image coverage only) and must not be promoted over the CAP-safe set.
