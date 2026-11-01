# Current NX transport and normalization consumers

Current emitted source 7dcc944c1d951d28fba997d4cdd5ee88175b8f2d84c1bbf947eb60a40e63c176: extraction on intel1 unit oth-ubuntu-146604-1793546472 PASS. All38 direct XG receive paths check173 active NX bits (valid, hops, base, payload). All192 local XFIN/XG and XR/XFIN interface records check exact bit order and have zero added wrapper register edges. Horizontal ring crossings have2/5 register stages. The four snake-end V crossings have31/36. These32 selected links compose all240 origin-to-peer paths. Each composed path records actual boundary stages and an explicit coefficient for the still unqualified common local forward latency; old6-edge calibration is not silently applied.

Ten non-direct receive paths remain explicit: four outward LEP/HBC line inputs and six middle V inputs (column3 gunit L3/L5, column4 BK/seqhost, column6 Engram). They are outside the endpoint-only NX snake, but the six middle V bridges still need actual forwarding contracts for XQ/BF16 allgather. The exact descriptor and failure reason remain in nx_routes_kva3.json.

Actual consumers are distinct:

- Native attention entry: entry_norm.py emits n=1, unflagged a1=5sid+leaf, q-only for a_proj. book_attention_entry retains that contract.
- Final HEAD: lower_head.py emits n=2, a0=1008, a1=128+5sid+leaf. Bit7 is the actual HEAD egress flag; low7 bits retain beat ownership. book_head_final keeps this flag and the BF16-only family. It requires same-token final POST h residency, live final FFN pre1008, and HEADG480 gains already loaded by GAIN. Those upstream operations are not asserted to have run.
- Legacy lower_norm_smoke emits n=3 for both families. Its local dual-family collision remains open; a single-family K qualification does not qualify that programme.

The earlier generic book_bf16 is an unflagged native publication candidate, not a HEAD egress programme. Both new96-row books are unsealed385-word HOST fragments. No BEGIN, SEAL, KIT, END, absolute NX/RSTD/VQ dates, input-residency observation, global completion price, START or token PASS is supplied. Seven focused book/calendar tests PASS in0.12s, including wrong-family and missing HEAD-flag-sensitive payload checks. No RTL/default/plan parameter is changed.
