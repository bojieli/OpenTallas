# hdie_col_idx256r_a -- GEN2e3 col_idx IDX256R collar master (L2H-PAD, 10-19)

Master ot_hbm_static_cfg_collar_idx256r (GEN2e3 l20p packed operand face: prm 769 b, pw_addr 8 b, nonzero reserved operand
bit -> sticky fault, row not loaded, concurrent launch refused). The GEN2e3 source was derived from the NON-FAN32 idx256
body, whose mapped netlist had 807/261/165/87-load nets (checklist item 3 FAIL). This kit sets FAN32=1: the packed face is
ported onto the FAN32 structure of the closed-timing IDX256 tile hdie_col_idx256_1019 (16 protected 16-bit banks, kept
local cv/ct/ca copies, registered next-onehot record select, private run/counter copies, 25 kept reset stage-2 copies).
Operand words keep only the 769 used bits. FAN32 defaults to 0 so the GEN2e3 synth elaboration is unchanged in meaning.

Variant: **a** = 129.6 x 129.6 um, exact io.tcl, 1559 pins evenly spread on all four full faces (W/N/S 390, E 389; 3.01 pins/um).
(_a keeps the predecessor's 129.6 sq die slot; _b is the tighter 108 sq pin-bound outline. Bind whichever closes first.)

Bench (Verilator 5.050, fleet ot-epyc4 unit oth-ubuntu-3786034-1792454034): tb_idx256r vs canonical idx256 reference,
6 legal random installs (depth 1..256, 8 records, 12 launches, 4852 identity edges), 15 reserved-field rejects, concurrent
reserved+launch refusal. FAN32=1 MUT0 PASS; MUT3 (go early), MUT12 (reserved check off), MUT14 (record select rotated)
FAIL -> committed witnesses results/arch/hbm_idx_collar256r_1019/witness/f1_m{3,12,14}.log. FAN32=0 also PASS (sweep_summary.txt).
MUT 1/2/8/9/13 are not distinguished by this reference-equivalence bench (same mechanism as idx256; covered by tb_idx256).

SAFE-DESIGN checklist (owner 10-19):
1. Pins PASS: every input lands in a pin flop, every output is a flop Q (kit pin_regs off with reason); reset lands in
   g_rst_same.rc[0:1] (raw pin -> one flop) + 25 kept stage-2 copies.
2. Reach PASS: soft tile 129.6 sq, opposite-corner Manhattan 259.2 um < 405; no macros.
3. Fanout PASS (by construction, gate measures): FAN32 bank/copy structure (0 nets > 32 on the idx256 FAN32 map); new
   reserved-check net resv_row_bad drives 16 bank inhibits (buffered); cd pin flops <= 15 word loads + 1 OR tree.
4. Depth PASS: reserved check = OR of <= 254 cd pin-flop bits + 6:1 row select (~10 levels) into the existing enable/fault
   path; idx256 FAN32 worst 376.7 ps / 10 levels. No combinational in->out path.
5. Storage PASS: 769 operand + 2048 record held-config bits in protected 16-bit words loaded only on install (no runtime-
   indexed flop array read except the 8:1 one-hot registered record select, as in the closed idx256); no delay chains.
6. Floorplan: no macros; one full std-cell region; aspect 1:1; pin-bound outline (fill ~16% < 40%), waived as for the
   ROOT-approved 129.6 sq idx256 (20%): 1559 pins need the perimeter; all faces <= 3.01 pins/um.
7. Clock: single clk root, clk pin mid-W; predecessor measured TT/FF insertion 195/160 ps, spread 29/26 ps (5420 sinks);
   gate --cts measures this master; io_hold_margin 0.03.
8. Schedule PASS: static; 0 added cycles vs idx256 on every successful edge (cfg->pw_we 2, launch->start_v 2, go offset+1).
