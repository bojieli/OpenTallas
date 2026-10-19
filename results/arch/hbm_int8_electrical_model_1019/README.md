# INT8 V2 electrical ownership model

MODEL only. Source `da40a2a46`, placement `121b7ec9a`, exact kit `ec8bf662d`, receipt `7e56c222c`; immutable ODB SHA256 `fc6b007164e4e5c2a934052922d40114cc4fc60602423d023aa53fa2a67d2081`. No RTL, netlist, checkpoint, constraint, route or CTS change was made. Fleet read-only Python completed on ot-epyc8, unit `oth-ubuntu-1892507-1792444067`, exit 0. The two preliminary extraction errors (missing-semicolon area parsing, local-only electrical rows) did not modify the checkpoint. `model.py` consumes the exact existing V2 native export and native TT/FF libraries; `model.json.gz` preserves typed pins, source loads, eight failing cones, all candidate data and library digests. Units are native ps/fF/um².

All 1070 output drivers are INVx1, from 1024 DFFHQN and 46 DFFASRHQN QN pins. Every QN has exactly one actual input sink, the inverter; existing FF-to-inverter center distance is at most 1.863 um. Function is `!A`; substituting a genuine stronger inverter preserves the Boolean value and original registered age. INVx1 max-cap46.08 fF is already below the fixed80 fF output load. Actual worst output load114.8 fF includes34.8 fF estimated wire. Constraints and load remain unchanged.

Native bilinear interpolation, without extrapolation, gives this candidate comparison at114.8 fF and260 ps input slew. These are lumped NLDM cell transitions, excluding distributed wire RC and FF CQ change; they do not establish pin slew or setup closure.

| Inverter | max-cap fF | TT rise/fall ps | FF rise/fall ps | area um² | TT/FF input fF |
|---|---:|---:|---:|---:|---:|
| INVx4 |184.32|294.350/239.661|222.593/193.287|.08748|2.33645/2.59330|
| INVx6 |368.64|221.802/183.542|172.331/151.115|.11664|3.48244/3.86653|
| INVx8 |368.64|186.624/155.858|146.826/129.127|.14580|4.61057/5.12139|

INVx6 is the smallest listed candidate with useful margin over the complete bounded input-slew range20..260 ps. INVx4's result at80 ps input (259.30 ps TT rise) is insufficient to select it. Replacing all1070 INVx1 by INVx6 costs +78.003 um² and +3062.88784 fF TT /+3405.61098 fF FF aggregate QN load. Each source QN's native max-cap is46.08 fF; its new sink consumes3.48244/3.86653 fF, leaving42.59756/42.21347 fF for source wire/other effects. Actual source-net wire capacitance and output transition must still be extracted; the arithmetic allowance is not a native PASS. No extra FF, clock sink, reset sample, storage bit, command, boundary bit, or cycle is introduced. Signal switching energy and source CQ increase must be priced from actual activity/corners; no dynamic-energy credit is claimed.

Reset failures collapse to six INVx1 output nets2291/5260/5264/5268/5270/5274, each with24 actual DFFASRHQN RESETN pins,17.75496 fF TT /19.269816 fF FF native sink capacitance. Each source is a real DFFHQN QN (slice6105/6104/6103/6102/6101/6100 respectively). These are sampled-reset landing descendants; SETN is not silently treated as ordinary D. Replacing only these six genuine inverters by INVx6 costs+.4374 um², +17.175072 fF TT /+19.096884 fF FF source load, zero age changes. Full wire cap, both assertion/release transitions, recovery/removal, source FF CQ/slew and upstream load need exact replay. Same-age genuine reset ownership copies remain a structural alternative if wire/load replay fails; any copies must retain both sampled assertion and release and count their D, clock and reset ancestry. Buffer trees do not reduce transparent logical fanout.

Internal D failures collapse to two NAND2xp33 output nets1665 and1595. Net1665 drives18 DFFASRHQN D pins (10.110222 fF TT /11.221722 FF); source inputs are slice5053/QN and slice4922/QN. Net1595 drives17 such D pins (9.548543/10.598293 fF); source inputs are slice5052/QN and slice4921/QN. NAND2x2 is a real matching `!(A&B)` candidate, max-cap92.16 fF, area.1458 versus.05832. Replacing both costs+.17496 um². Per gate input loading changes from A/B .336683/.346682 to1.92205/2.03952 fF TT, and .368030/.391247 to2.09909/2.22176 FF. Both arcs, sensitization, actual wire capacitance, all upstream loads and setup/hold must be evaluated before selection. The envelope's NAND numbers retain the first native timing arc only and are inventory, never an all-arc qualification.

Combined illustrative INVx6 boundary+reset and two NAND2x2 changes cost+78.61536 um², +0 FF/+0 clock sinks/+0 architectural edges. The current pin-bound outline237.6x129.6 um and total rectangle reach367.2 um remain model bounds; no widened cell has yet been legalized. Actual native row width/contact/PG overlap and the real per-net reach must be rechecked for a successor. INV6 width from native area at.27 um row height is.432 um versus INV1 .162 um, so fixed original locations cannot be assumed legal. Keep cells in the single existing legal band, preserve full-face IO density and actual PG rails; no isolated power island is proposed. Placement density alone is not legal-row or PG proof.

The measured FF ordinary hold failure remains -7.12 ps: FF slice13235/QN → INVx1 parse_blif37773/Y → FF slice12201/D. Launch118.92 ps, capture131.62 ps, CQ34.87 ps, inverter5.77 ps, net.02 ps; required166.70 ps includes uncertainty25, CRPR-1.97, nativehold12.05. This path is independent of the illustrative output driver replacement and must receive a separately source-bound structural hold treatment. Do not pad diagnostic IO: output setup -275.41 ps depends on an unqualified parent clock reference. Dedicated drivers address real electrical violations regardless of that reference, but cannot qualify the parent boundary.

Next authorized step is ROOT review of this MODEL and the independent positive identity/PNG/PG packet. A successor requires explicit approval, source-bound genuine-cell mapping, legal placement/PG/reach, measured FF hold repair, actual parent clock references, and exactness/negative controls. No new CTS, data ECO, route, gate or submission was launched. The existing 253 CTS cells and110 real clock load outputs are preserved and remain charged; positive clock identity does not waive electrical failure.

Checklist: registered IO PASS inherited; reset2 samples PASS inherited; reach MODEL bound367.2/open native successor; transparent fanout existing max24 unchanged; depth/timing OPEN; storage unchanged; floorplan/PG successor legalization OPEN; TT/FF spread existing evidence only, hold FAIL; static schedule unchanged and +0 edges. This packet is not tile closure or parent adoption.

## Actual upstream load and minimum-path follow-through

Read-only source extraction completed for all1080 relevant QN/CLK pins, all1070 boundary sources and all8 changed cones. Native `report_net`, `sta::report_slews`, complete min/max full-clock path reports, and `report_dcalc` ran against the same immutable checkpoint, with original constraints and placement RC. Fleet units `oth-ubuntu-1904545-1792444323` (native source/path reports), `oth-ubuntu-1921963-1792444404` (native table bounds), and `oth-ubuntu-1933067-1792444488` (original native CQ) all exited0. Final ODB digest still equals the pinned digest. No database write, cell swap, clock synthesis, repair or route command is present in these probes. The probe discovery errors involved unsupported reporting flags only and did not change design data.

| All1070 boundary sources | TT | FF |
|---|---:|---:|
| Actual original source wire capacitance maximum fF |.23824024|.23824030|
| Actual source CLK pin slew maximum ps |17.66643715|14.98304462|
| New INV6 load plus actual original source wire maximum fF |3.72068024|4.10477030|
| New QN transition maximum ps, native in-range table bound |45.23137595|33.65019972|
| New CQ maximum ps, native in-range table bound |74.58745388|53.10414146|
| Added source CQ bounded range ps |16.13102462..18.50486292|11.94357762..13.71770989|
| INV6 transition maximum ps at114.8 fF and new QN slew |176.38010685|123.19550735|

The new source loads are far below46.08 fF QN max-cap and their computed source transitions are below260 ps. Every new-load evaluation lies within its genuine native table grid. Original tiny loads lie below the table minimum for1070 TT and1067 FF sources: the analytical interpolator correctly refuses those old-load evaluations. Original CQ values instead come from the actual native STA `report_dcalc` result, with both rise/fall and min/max retained. No fabricated native characterisation or custom extrapolation is used. The added CQ ranges conservatively compare new table bounds with measured native original CQ. The INV6 column remains a lumped driver-output transition bound; it excludes distributed output wire waveform/delay, legalization displacement and parent reference obligations, and is not boundary setup closure.

Critically, the stronger reset inverter cannot be selected on slew alone. Each original minimum path's measured CQ and inverter delay was replaced analytically by the conservative native new-load minimum; original wire delays and capture check were held fixed. This isolates a real minimum-delay risk. It does not qualify a changed waveform or removal/hold table.

| Cone net | Existing FF min slack ps | Conditional TT min slack ps | Conditional FF min slack ps |
|---|---:|---:|---:|
|5264 RESETN|65.009|11.264|2.465|
|5260 RESETN|55.711|16.664|7.821|
|5274 RESETN|55.226|4.961|-3.505|
|2291 RESETN|62.183|18.455|9.269|
|5268 RESETN|55.680|17.258|8.744|
|5270 RESETN|44.033|11.594|3.296|
|1665 D|89.046|64.323|38.413|
|1595 D|89.653|67.313|41.272|

The reset paths are native asynchronous recovery/removal checks from the real sampled landing FFs, distinct from `rst_n` input timing. Faster reset delivery consumes their margin; unchanged two-sample age does not preserve physical removal. All six reset candidates miss the30 ps working margin in this conditional model and net5274 goes negative. Thus the illustrative INV6 reset replacement is **REFUSED as a ready successor**. It needs a genuine reset ownership/minimum-delay design with actual assertion/release phase and recovery/removal cost before any build. No +9.75 ps old removal margin is carried forward. The two NAND2x2 candidates retain38.4/41.3 ps only under fixed original wire/check assumptions; their real D slew affects hold checks and must be replayed. Both A/B native NAND arcs are included in this follow-through.

`source_bound_with_native_CQ.json.gz` retains every source load, native original CQ, both-arc new-load table result and actual source-clock slew. `summary.json.gz` retains all per-path conditional minimum-delay calculations. Compressed native TT/FF source and dcalc logs retain the raw evidence. `bound.py`, `source_probe.tcl`, `source_dcalc.tcl`, and `summarize.py` reproduce it. Boundary INV6 remains a plausible function-preserving MODEL candidate with measured upstream cost; reset strengthening is not approved; internal ordinary hold -7.12 and the parent IO reference remain open. Minimum-delay structural repair and reset waveform qualification are required before a successor can be concretely proposed.
