# HEAD count-aligned writer locality

Opt-in `clock.landing_ring_wreg.write_chunk` bounds each kept WREG write-enable
flop to 1/2/4/8/16/32/64 payload bits. Default64 preserves existing generated RTL;
all previous positional RTL parameters retain their positions. The CAS payload is
padded to64bits, so supported chunks divide the storage width. DSREP remains the
separate read-select replication mechanism. No default form, plan of record,
clock contract or strap/count rule changes.

Measured trigger: HEAD west RX vB worst TT slew430.66ps (limit320) on
u_cland_link_i/_12708_/A. Its driver BUFx10 place4855/net4854 fans out to109
AND3 inputs, derived from the shared writer-slot decode. There are357TT/343FF
slew violations;325TT are inside this landing. This is a drive/wire class failure.

Proof: chunk8/DSREP8/WREG1/FREG1 matches current-main chunk64/DSREP1/WREG1/FREG1
in43200 output-cycle comparisons, both WFALL modes,4680readycycles,0differences.
WREG mutant produces14252differences. Separate raw-ring delayed reference checks
4620readycycles and measures FREG +1payloadcycle and K+2. FREG mutant loses all
readycoverage and is detected; the original runner's diagnostic exit92 is retained
in freg_result.json. First insufficient-coverage attempts remain in scratch.

Private candidate recipe prepare_rx.py takes original l48uj sourceplan/sidecar.
It enables FREG1, WREG8, DSREP8 and increases link FT stages3→6 (PIN CYCLES +4
end-to-end = input+1, FT+3). Intended wire hop is699.84/6≈116.64um instead of233.
Original outline/pins stay: the large slot is inherited from the physical plan;
this candidate does not change that plan. Signals cap atM6 using conservative
kit settings; pin access exceptions remain as emitted by the shared flow.
Candidate is DO_NOT_COUNT until compiler/token pricing and plan integration.

GEOMETRY: viewed vB final placement, congestion and clocks; no macros or
macrochannels. The original data occupies the top300um of the1037umslot with
widely separated register stripes. The candidate planned image shows aligned
W→E bitorder, six straight short hops, separate pin FREG bank and enlarged ring
bank. SMELLS4/7/10 are addressed for payload reach by explicit stages/local writer
control; cold reset/clock span still requires actual PLACE/CTS review. Conditional
PLACE pilot only; review actual placed images before route or any batch.
