# Current VS candidate status

Latest measured RTL source2f0cb6f94, default-off OT_S81SL_VS_SRAM. Still NOT ADMISSIBLE.
All run objects remain under ot-epyc5:/srv/opentallas-scratch/claude/codex-s81-vs-bankmux-1021.
No VS layout gate or route has been launched by this owner.

| Source | Structural step | Actual native maximum / violating drivers | Existing functional proof |
|---|---|---|---|
|474637070|8SRAM parity/copy banks, predicted read, write bypass|768 /297|ENG159/73 PASS; MUT7 catches16; VSallops PASS; MUT9 catches33|
|4dfd957fa|byte write-decode, flush and pending selectors|512 /305|same ENG/MUT7 and VS/MUT9 results|
|5de57c716|QR byte capture/phase, kept control identities|521 /306|VSallops PASS; MUT9 catches33|
|11ed229e0|32regional reset leaves; each FP pipeline owns reset; unused old stash counters removed|521 /305; raw reset input1, zero role errors|ENG159/73 PASS; MUT7 catches16; VSallops PASS|

No measured external latency changed. Native admission remains a real blocker.
The latest circuit still has broad command/counter/operand-select controls and
shared FP cut-bundle payload fanout. The original 431-load reset node was
removed; retained source mappings place other high drivers at ka, captured
command fields, input-valid and shared ot_hdc_f12_cut payload registers.
Native JSON, mapped Verilog and mapped_attr JSON are retained remotely. Each
committed summary contains its full violating-driver list and raw report hash.
No constraint waiver, false path, multicycle or native-check change was used.

Source2f0cb6f94 operand-nibble hierarchy: existing ENG159/73 PASS, VS allops PASS, MUT4 catches22MOE errors; native5 FAIL654/307 (231seq), rst1, roles0. All raw logs committed. Next candidate adds regional arrival counters for ENG halfword selects and byte captures for RA/K/W; no added edges and no layout gate.

Source91891ec62 native6 max433/320violations (246seq), rst1/roles0. ENG159/73 PASS/MUT8caught4, VSallopsPASS. Regional ENG arrival and RA/K/W capture removes prior654/512/451 controls; broad result mux is next repair, no layout.

Source58f946148 byte result mux native7 max257/338violations (276seq), rst1/roles0; existing VSallops and ENG159/73 PASS. Former433/364 resultmux controls removed. New257 root traces command wsel[0] into64bit eight-way weight mux, next201 RA result capture; next source byte-local weight selectors + predicted RA byte write enables. No layout.
