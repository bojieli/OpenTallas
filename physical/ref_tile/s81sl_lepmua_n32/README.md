# s81sl_lepmua_n32 — MU native32 control successor

Source9a4faab57 (opt-in NATIVE32=1,RX_SRAM=1,IN_PIPE=1), helpers synchronized from main. Structural model and immutable native/campaign receipts are in results/rtl/s81_lepmu_native32_1020. The exact-source native census includes actual mapped keep-wire driver protection and reset landing; maximum non-clock fanout32, no refused census checks, 18128FF,20SRAM. Verilator5.050 production seeds1/5 and all existing causalmutants matched their required verdict regexes. Zero source/static-calendar edges added; original tags, queue occupancy and protocol preserved.

SAFE checklist before layout:
1 Pins: input capture and output pinflops preserved; no combinational input-to-output path, mapped input-to-reg2levels/output1level. Reset lands2stages then balanced regional tree. No functional top port tied off.
2 Reach: existing475.2x561.6full-row macro geometry retained; original floorplan fixed-terminal reach111.8um. New control/read pointers are local per128bitSRAMbank and8/9bitconsumer group. Physical placement reach remains a gate obligation; no waiver of405um.
3 Fanout: PASS mapped max32 INCLUDING resets; no >32 driver. Status/history, nonempty, per-bank pointers, return mux select and tag-load controls are real kept copies/decodes.
4 Depth: mapped 368.4ps/12levels; no combinational top I/O path.
5 Storage: PASS20realSRAM (10RX32x128,10TX512x128), no new runtime-indexed flop storage.
6 Floorplan:20macros on43.2um lattice, >=20um macrochannels; same full rows, no pruning/islands. Outline is macro-lattice/pin-bound; mappedstdarea7693.764um2. Lowfill exception awaits coordinator, retained explicitly in spec; this is not layout approval.
7 Clock: Wcentre entry beside core mass, ordinary leafclock; actual TT/FF spread<=80ps and nativePG still owed by gate. Rootcount/insertion alone advisory. io_hold_margin0.03.
8 Schedule: PASS same-age state/control copies, zero new static edge, all production exact/mutants measured.

Next --cts gate, then inspect actual PNG/checklist/census/PG. Do not submit until full-row fill exception and physical evidence are reviewed.
