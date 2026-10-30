# HBM token compiler continuation, 2026-10-29 22:49

## Actual three-lane attention phases

`vm_attention_phase.py` constructs native fragments from the real a122 records:
IDX.KVUNION1528/1529 -> ATT.QK1530/1531 -> SU1532–1534 -> ATT.PV1535/1536.
These are the two physical NL3 groups with slot0=0 and3. The tool retains the
actual KVUNION param, all three plan lanes,640-word QK/SU vectors,512-word PV
vectors, plan dimensions320x32,400-word lane maps and HBM descriptors. It maps
implicit rtab pointers together with the actual producer R descriptor, retaining
modulo32 alignment. The entire stage occupies16688/17488 words of the old VM.
It supports a reserved prefix for other live state and refuses overflow.

This directly handles the first previously unresolved dynamic-plan boundary;
ATT rsel plan mode has fixed physical lanes and is not an expert row-table
selection. Native record/row expansion and an injective address translation
preserve arithmetic, aliases, slots and lane identity. The fixed NL3 form is
retained rather than applying the earlier two-row producer grouping to attention.

`check_attention.py` generates actual encoded plan words for overlap, disjoint,
identical and short-context lists in both slot groups. The native relocated plan
and lane-map pointers reconstruct12342 golden lane-list words in order. Wrong
plan pointer, oversized plan header, wrong lane map, missing actual producer and
external-reserve overflow controls are caught (9 controls). Twelve native records
cover32 expanded rows and20480 plan words. This validates compiler relocation and
plan semantics; it does not claim an RTL whole-token replay.

Whole-programme installation remains held on real boundary input publication,
output retirement, outside live values, scratch authority, cross-phase scheduling
and the source/physical calendar. `executable=false`, `full_programme_fits=null`.
The current physical token model is1802.5tok/s (1794.4 bound) for pgp+2/IDX31;
the old+30 scorer feed chain remains unbuildable and is not made real by this work.
No new throughput rate is claimed for finite phases.

Reproduce:

```
PYTHONPATH=/home/ubuntu/OpenTallas/tools python3 tools/hbm_next/vm_attention_phase.py \
 --image /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r \
 --compiler-tools /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools \
 --out-dir /tmp/hbm-attention-phases
PYTHONPATH=/home/ubuntu/OpenTallas/tools python3 results/tok_hbm_2249/check_attention.py
```
