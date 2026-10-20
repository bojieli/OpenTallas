# Sid6 source vehicle: review plan, implementation HOLD

Current authorization covers source/model work only. This packet does not grant
or install a production imagewriter, generated die, binding or RTL change.

The bounded vehicle is one real head, sid6, using the six physical frames in
selected source ceaed19c4 (die SHA256
61b683b697d17b7d6d1619352d302648d835822677c02097ce48639a0aa399b8).
It owns all512 rank-local wq_b rows3072..3583, divided into15 epochs of at most
six real rows per frame. The original fixture is L0/rank0/chunk8, context1048576,
position1048575, seed20260930, from checkpoint dba1be0a40aa45a94ad051997016db3960a90277.
Its metadata SHA is d7f2eb6175bec6a21f2ccede5a103842d7d03e36c54b4859b967a6e04ba44b28;
meta/files and every consumed binary hash are pinned beside this plan. No final
Q payload is a stimulus. The existing q_norm.scale input is an explicit
intermediate-state boundary, so this vehicle cannot qualify a token or prove
its upstream normalization producer.

| Actual frame | Master | LK (four lanes) | CAP lane/tree | Return endpoint/stations | Dimensions |
|---|---|---|---|---|---|
|u_f_3L01|col_h10_l4|0x492 (2,2,2,2)|0/W|w_r_f_3L01_lnd /1|0..85|
|u_f_3L02|col_h9_MX_l4|0x249 (1,1,1,1)|1/W|w_r_f_3L02_src /0|86..171|
|u_f_3L03|col_h9_l4|0x492 (2,2,2,2)|2/W|w_r_f_3L03_lnd /2|172..256|
|u_f_3R01|col_h10_l4|0x492 (2,2,2,2)|3/W|w_r_f_3R01_lnd /1|257..341|
|u_f_3R02|col_h9_MX_l4|0x249 (1,1,1,1)|4/E|w_r_f_3R02_src /0|342..426|
|u_f_3R03|col_h9_l4|0x492 (2,2,2,2)|5/E|w_r_f_3R03_lnd /2|427..511|

All frame clk/cr/cr_s names and the slice clock are ck_cl3S. CAP lanes6/7 are
actual literal zeros. This does not prove edge phase: native source/landing
launch, capture and reset-release dates remain NULL. The return phase method
must trace the selected die's exact source→station→landing→packed CAP paths,
resolve every register's posedge/negedge clock and actual landing strap, and
carry valid/tag/data/status together. Then a marker must be observed through
the existing route at its physical sample edges. No half-cycle station count
is rounded into an invented ARR edge. Before source implementation, the
model can state conditional phase constraints; it cannot claim those dates.

The implemented model uses only original fixture bytes and original segment
math. It matches512 BF16 gold rows, maps every real row once onto actual frame/
epoch/address, and rejects512 wrong-owner tags. Epochs0..13 own36 rows each;
epoch14 owns8 rows (2,2,1,1,1,1 across the frames). Unused row capacity stays
padding, never a real value. Actual frame emission and native ARR calendars
remain HOLD. Original row flags1, semantic identity and reduction lo/k/n are
preserved. CAP rbase=0x5800, rcnt828, fmt2, obase0, np0. Tail capture is leaf2
even rows16..46; coefficients reserve odd17..47; QR output reserves544..559.

Cost is reuse of existing source/state. New hardware:0 FF,0 gates,0 SRAM/ROM
macros,0 pins,0 clocks/reset loads and0 pipeline stages. Captured projection
uses16384 existing VP SRAM bits; coefficients2048 and QR output2048. The
original six frames and CAP are existing physical blocks; the vehicle does
not replicate them on the die. Existing ROM occupancy and calendar depth must
be checked after a private phase plan exists; neither free capacity nor a
physical area reduction is claimed. K1280, three segments, nine useful q-pairs
per six-row frame phase,15 epochs versus the invalid fixed8 reference's11.
No edge cost is inferred from four extra epochs: actual epoch span is NULL.
The eventual fixed NP4 transport remainsII4, with no relaxation of the original
token deadline. Model admission was8GB/one thread, unpinned ot-run. A future
six-frame simulation needs a separate bounded compute admission; it is not
launched by this packet.

After exact ROOT source grant, the smallest isolated implementation would be
a private selected-plan adapter and vehicle under qf_producer, consuming the
six exact frame records, original input state and weights. It must not invoke
the fixed8 production Die/placement or change production files. It would drive
the existing XS/element programme into actual frame modules and existing
return routes/CAP/VP storage. No replayed return/final-Q trace would drive an
endpoint. Numeric fixture output is scoreboard only. QR/gather/Q512 consumer
are subsequent dependencies; their closure is not implied by CAP success.

Pass requires all512 identities exactly once, exact original accumulator/BF16
values at configured storage, correct flags and padding, all15 epochs, zero
frame/tree/CAP faults, F5/F6/F8/F11 freedom, and valid final-write/read ages.
For each key, hold the CAP slot through its complete re-entry; keep config
until old partials and D2 consumers drain; release VP addresses only after
all dependent reads. Record real source→ARR→CW→SRAM timestamps. Prove issuer
retirement independence or conservatively hold until source completion.
Wrong owner/flag/row, corrupt partial, missing partial, early/late transfer,
CFG while partial remains, same-slot foreign key, same-port collision and
reset during a partial must fail causally. Original deadline/clock/reset/MU
criteria remain unchanged. Any missing native phase or original-deadline
failure keeps source qualification HOLD/FAIL, even if the arithmetic model
passes. No selected122-frame success is inferred from this six-frame plan.
