# KV relay corridor candidate, 2026-10-20

Status: geometry preflight PASS for two variants, NOT a strict die result.
Source branch codex/kv-relay-plan-2210; geometry evaluated at c6c649db6
(018abccda placement change); a95cb0efc adds endpoint-priority allocation.
Read-only preflight stops before `_relays`; it does not omit any check from a
qualifying chain. Strict bind, real relay ages, GEN safety, PG/M8 GRT trial,
TT/FF STA, clock and die IR remain mandatory.

The d23p1/2/3 failures are preserved in the original KV-D2D3 run directories.
The failures respectively expose sink-greedy placement of 39 PV.start pads,
exhausted D2D payload endpoint approaches, and K.tx_record above the immutable
K22 image. No image, cycle count, pin model or reach constraint is relaxed.

## Two concrete variants

Both set OT_KV_ATTN_WEST_HOST=1 OT_KV_EQ_ROW_BANK=1
OT_KV_D2D_ENDPOINT_FIRST=1 and unset OT_KV_ATTN_DXY/OT_KV_ATTN_AT_D2D.
Other strict integration flags stay with the die owner.

| Variant | OT_KV_D2D_APRON_UM | HOST/D2D free channel | Wide relay rows | Legal row sites | Die height |
|---|---:|---:|---:|---:|---:|
| A | 216 | 347.784 um | 3 | 62 | 28432.08 um |
| B | 302.4 | 434.184 um | 4 | 83 | 28518.48 um |

The 548/549/552-bit words use 45.36 x 82.08 um relay frames. Row pitch and
placement use the actual GX/GY lattice, 21.6 um block halos and 4.32 um relay
gaps. Rows align from the D2D S face so endpoint reach is not spent on an unused
bottom margin. The committed JSON gives each actual site and a simultaneous
nonoverlapping assignment for all five wide words (rx_payload, rec_rx, rec_tx,
att_tx_payload, emb_tx_payload), checking every realized D2D view bit against
340 um. These are available sites, not an allocation claim after all other
chains have been built; the new priority gives those constrained words first
access before control/boot chains.

Attention moves from the old p1 home (5741.712,25261.2) to
(5917.536,27002.16) for A. Its E side has a 129.6 um approach to HOST; its N
side is 43.2 um below D2D. Exact K22 padding remains fail-closed when natural
stages exceed the image. S-going PV/control words get freshly derived/priced
ages. All added equalizer cells remain real one-cycle relays; the row bank
reserves its complete rectangle before placing a serpentine R0/MY chain.
Every intercell and endpoint hop is measured from actual cell pins.

The die width remains 13476.672 um. Relative to d23p1 height28302.48, A adds
1.747 mm2 and B adds 2.911 mm2, both below 28600 um in height. No token-rate
claim is made until the actual relay ledger and compiler have been exported.

## Future CTL slot, not enabled

The 345.6 x 475.2 portrait slot legally fits (6565.536,25961.04) in either
variant with normal halos. Legacy CTL source stays exact. C32 source/native
repair is another lane; its +2 drain and +2 boot edges must be priced before
C32 is enabled. Geometry alone does not qualify that binding.

## Fleet validation

`bank_tests.log`: 3/3 PASS (39 real row cells, lattice, orientation, per-hop
reach, no overlaps; occupied region and unreachable endpoint negatives).
`corridor_proof.log`: both geometry variants PASS, unit
oth-ubuntu-15477-1792560095 on ot-epyc6, admitted through unpinned ot-run.
The script and full site/endpoint packets are retained alongside this note.
