# Actual XR output to VP input transport

Source 32d6720b95, canonical top1c11db22/source003a165c, extended381-unit inventory.
Actual ot-run unit2555765 exit0:80/80leaves,480 coherent command/target5 fields,
34,880 exact VP input bits. Each leaf's identity is derived from the actual XR
sw_v source bit and unique VP input route, never normalised path indices.

The first run (unit2496611 exit2) blocked70leaves because generated source `$buf`
expressions create separate bound pin identities. Ten C3 leaves passed directly.
Example0N source chain: XR.sw_v[0]→$0.A[432] age0; $0.Y[432]→$22.A[432]
age2; $22.Y[432]→VP.swv_c.D[0] age0. The corrected adapter bridges only source
metadata kind=glue/master=$buf with exact equal-width Ainput/Youtput and identical
bit index. It sums every actual bound stage, rejects other logic/missing pins/
cycles, and retains all54,936bit proofs across126 buffers in the runtime record.
Four focused controls cover exact ages, wrong logic, swapped bits and cycles.
Original failure evidence is retained, not rewritten.

Rerun (through ot-run):

```
PYTHONPATH=tools/s81_dv python3 -m layer_prog.bound_entry_transport \
 --bound /srv/opentallas-scratch2/claude/tok-ds/s81_877/v2/out \
 --inventory /srv/opentallas-scratch2/claude/codex-bound-inventory-1026/inventory.vp.json \
 --out FRESH.json
```

The compact integration table records actual per-leaf command/store ages and
source VP paths. Full proof files remain at
`intel1:/srv/opentallas-scratch2/claude/native-control-1026/entry_transport{1,2}.json`.
Ages are not a shared DL4: e.g0N[2,2,9,9,16],3N[2,2,6,6,10],3S[2,2,8,9,14].
These records cover bound transport only. Current VP parameters/read/capture
latency, local store commit, HLOAD/GAIN, VN partials/return and actual reset/clock
bookings are separate receipts. Existing96-command proposed retime qualifies
XR/PDSK spacing only, never complete NORM partial arrival or GO readiness.
No production RTL, local macro behaviour or added-cycle token model is changed.
