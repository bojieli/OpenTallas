# F1: SU job kinds RA / RB / QR (s81-functional-token, 2026-10-14)

Die item F1: the S81 stage programs issue `L*.ffn.softplus_sqrt`, `L*.ffn.bias` and `L*.attn.q_rope` to the SU (eng su, port 1),
40 each a token, but no S81 die unit computed them (SU kinds were QN KV QB SW SE SO GQ GK; die.v c7p has no router-act or
q-rope unit). Home decided: three new SU job kinds, stage programs and price graph unchanged.

| kind | op | RTL | operands |
|---|---|---|---|
| 8 RA | ffn.softplus_sqrt | `ot_s81_su_rxe` RA lanes = `ot_hdc_v41x_softplus_s` (PCUT 1, exhaustive 2^32 evidence) | count score rows |
| 9 RB | ffn.bias | 16 binary32 adders (golden add) | count score rows, then count bias rows (layer constant, compiler-placed after the all-gather output) |
| 10 QR | attn.q_rope | 16 lanes: 2 mul + 1 add, BF16 RNE (golden rope_tail) | the 4 rope rows of each head (in_base + 32 h + 28..31), in place |

Flat core: `ot_s81_su_core` + walker `ot_s81_su_rx`. Hierarchical slab `dsfd_sp_su_h`: new last stop `ot_s81_su_rxt` (TK 14, one
write slot), control tile `ot_s81_su_hctl` issues one operand row a cycle (RB interleaved score/bias, QR strided).

Gate: `tools/s81_suhc/su_gate.py` (pinned su_cases_v2_ildr.pkl; RA/RB/QR operands are stress values incl. +-0, subnormals,
+-88), Verilator DPI, ot-epyc4. Mutants `--xmut`: 1 RA returns softplus, 2 RB drops the bias, 3 QR inverse rotation.

| run | flat (0da7a12ae) | hier (4d201c771) |
|---|---|---|
| reduced positive x3 runs | PASS 0/311 | PASS 0/311 |
| reduced xmut 1 / 2 / 3 | FAIL 2 / 8 / rows | FAIL as required |
| full positive x3 runs | PASS 0/1816, 14/14 jobs | PASS 0/1816, 14/14 jobs |
| full xmut 1 / 2 / 3 | FAIL 6 / 24 / 64 rows (x3: golden_L0 observed, run stopped after) | FAIL 6 / 24 / 64 rows x3 |

Production-shape job cycles (start -> done at the slab pins, full shape, 96 scores / 384 scores + bias / 16 heads):

| kind | price | flat | hier (production) | hier / price |
|---|---|---|---|---|
| RA softplus_sqrt | 185.6 | 168 | 353 | 1.90 |
| RB bias | 117.6 | 69 | 277 | 2.36 |
| QR q_rope | 117.6 | 115 | 298 | 2.53 |

The flat arithmetic meets every price; the hierarchical excess is the slab's fixed job chain (two serial VM read round trips,
spine stops, as QB / SW / SO) plus one operand row a cycle (RB 48 rows, QR 64). UNQUALIFIED as units (> 1.10x). Modelled e2e
cost if all three stay serial on the critical path (40 runs a token each): +507 cyc a layer = 20,288 cyc = 2.45 % AR of 828,866.
Structural headroom: QR 4 rows a cycle (a head a cycle), RB 2 rows a cycle (score + bias pair), job overlap in hctl.
