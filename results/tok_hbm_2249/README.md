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

## Producer lifetime allocator and native write-completion diagnosis

`vm_value_phase.py` now handles records1458–1473 as two THREE-row producer phases
matching attention's NL3 grouping. Value versions, not one permanent translation
per old address, determine storage lifetimes. Reads join all values addressed by
one descriptor; intra-instruction aliases retain one translation. All rows of a
native source record share a lifetime boundary, so allocation cannot reuse an
input while another row of the same record still runs. The SM row arrays retain
shared-weight three-row issue. Affine rows are re-encoded as native ROWX records;
only the few non-affine DMA loads remain single-row commands.

Native DMA stores require complete32-byte sectors. The allocator therefore owns
whole8-word sectors. A partial output first preserves the prior sector contents
and joins that version, so scalar retirement cannot corrupt neighbouring values.
This raises the first phase's high-water versus a word-only placement, correctly:
**238592/220160 words**, below262144. Forty native records cover96 expanded rows;
both SM records retain three-row shared-weight issue. The independent word-version
replay checks995472 read words and catches8 address/slot/template/boundary-payload
controls. Exact engine footprints include scalar broadcast and paired SU reads;
no arithmetic template or rounding operation is changed.

Boundary loads are explicit:14/25 intervals,138264/156776 words. Declared static
output retirement covers26/20 sector intervals,92792/100552 words. These are
component obligations;1118 unresolved whole-programme dynamic obligations still
prevent final installation. Publication must use immutable value epochs: a
phase's output cannot overwrite another phase's still-needed input snapshot.
Real scratch authority and the whole source calendar remain required.

The opstore_a geometry proposal also exposed a real source timing contract:
both+1 eight-bit internal chains target SFU local_w_done. The unmodified source
checks write_expected[WRITE_RETURN+1] against those bits exactly. A real833ps
component probe on intel1 (ot-run unit2842440) confirms: expected11/actual11 PASS
fault0; expected11/actual12 gives fault1; expected12/actual12 PASS fault0. The die
owner recovered legal original-five-station geometry instead, preserving
WRITE_RETURN11 and adding0 cycles. This is not a two-cycle serial SFU penalty.
No source timing parameter was adopted or modified by this lane.

A native-address issue was found in the older unreserved publication preparation:
scratch0xF000000000 is40-bit encodable but has illegal HGI stripe code7. It was
never installed. New native DMA publication must enforce the actual HGI address
and sector rules; no old result is promoted to full-fit or token success.
