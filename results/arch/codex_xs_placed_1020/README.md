# XS D/E physical audit — REVIEW blocked

Frozen source d6516cd02; gate results/layout 0cc04415e; actual014-library native source census00ed565e2 PASS max32/66238 roots.
Own collector branch only; original gates/ODBs untouched. Canonical PG collector + sibling binding copied from 0cc04415e. Docker image sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29. Fleet: agidock128 /srv/opentallas-scratch/claude/codex-xs-placed-1020. Audits use exact gate 5_1_grt.odb, immutable mounted read-only.

| Fact | D | E |
|---|---|---|
| Gate source run | smh_xs_p192d_lattice-20261020-013205 | smh_xs_p192e_lattice-20261020-013206 |
| ODB SHA256 | 41d7c34ac1b3e00ecfa36fefab84dc2f0f562199e15d9de9a7852c132fb8236a | b027b03e21bb9d2356ddcdd36e719825774841f21f58dc4d6f7ea26f781528a3 |
| Direct nonclock net diameter | 222.590um /108743 nets | 234.470um /109515 nets |
| Sequential source→capture displacement | **652.321um /224 captures>405** | **623.558um /344 captures>405** |
| Native PG raw failure terms | 32952/246906 | 34280/252420 |
| Protected PLACED unbound terms | **54 /27 HB4xp67 ot_inhold cells** | **54 /27 HB4xp67 ot_inhold cells** |
| Diagnostic global_connect remaining | **54** | **54** |
| TT/FF pin-flop spread | 44.7/43.9ps | 38.5/42.4ps |
| TT/FF max insertion | 602.8/478.3ps | 663.5/520.4ps |
| GRT overflow / M3 use | 0 /21.21% | 0 /19.66% |
| Size /aspect /fill | 475.2x388.8 /1.22 /0.304 | 475.2x432 /1.10 /0.274 |

The direct-net result alone is insufficient: buffers do not provide cycle boundaries. `sequential_reach.py` propagates launch-coordinate extrema through every combinational cell and stops at DFF/SRAM capture inputs. It conservatively considers all combinational input→output arcs, with CLOCK/PG nets excluded; `path_witness.json` independently traces the top three endpoint pairs. ALL SIX witnesses traverse only buffers/inverters (6–7 cells), so these failures do not depend on a pessimistic functional mux arc. D: `u_leaf.a2p[9]/QN` (32.867,293.895) → `u_leaf.g_sm[14].q2[9]/D` (413.298,22.005), 652.321um. E: `u_leaf.c3bd[18]/QN` (13.948,388.395) → `u_leaf.u_ctle.q[16]/D` (464.976,215.865), 623.558um. Escaped exact names/pins in receipts. 1739 capture inputs have no dynamic launch source in this propagation; constant-input classification is still owed. This does not change the demonstrated data reach failures.

PG raw collector is read-only. `pg_classify.py` looks up protection/status for every failure. `diagnostic_bind.tcl` calls canonical global_connect on a separate in-memory database and audits it, never writes an ODB, clears protection, or alters the original. All remaining failures are 27 protected ot_inhold_00000..26 cells, VDD+VSS. Final publication must audit exact 6_final ODB/SPEF; these intermediate diagnostics cannot substitute for that receipt.

SAFE8 review: (1) existing registered pins/reset landing documented by source/gate; (2) **FAIL data reach**, structural R0 plan and/or registered hops required; (3) actual-Lib source census PASS max32; (4) gate TT placement-RC setup+32ps/FF hold+38ps reported by predecessor, no SS headline claim; (5) 11 SRAMs, unchanged storage; (6) viewed both floorplan+density PNGs: 43.2 lattice R0 SRAMs, continuous cell region around macros, blue/green density no red hotspot, below target fill (pin bound); face pin maxima S5.3/N4.1/W2.6 perum; (7) spread PASS but **native protected-PG FAIL**, final PG proof owed; (8) no cycles added, static source unchanged. No waiver, REVIEW, route submission, or die bind authorized by this packet.

PNGs inspected: physical/ref_tile/smh_xs_p192{d,e}_lattice/gate_layout/{floorplan,density}.png at0cc04415e. Existing gates remain WARN as originally recorded; this packet adds failures and never overwrites them.
