G96 GROUP_REDUCE_MCAST price re-based on HANDOFF 0az (H-COLL, 2026-10-15)
======================================================================

Owner rule 0az (10-15 07:28): cross-die collective links keep link-level flow control (elastic RX buffer / credits at
the SerDes boundary); everything on-die stays fixed-slot. The frozen 1007-cycle G96 calendar (local_retime) assumed a
fixed-flight TX5/RX1 endpoint. `tools/hbm_coll_static/g96_bridge_calendar.py` now takes `--tx-extra/--rx-extra`
(V4 endpoint TX6/RX2 = 1/1) and `--elastic-edges E`: the receiving die consumes each cross-die word from its elastic
buffer E edges after the fixed-flight arrival (a compiler-reserved block-ready margin; on-die schedule unchanged).
Defaults reproduce the frozen calendar exactly (base = 1007, same as local_retime/model.json).

| config | relay/quarter edge | V4 TX6/RX2 | elastic E | cycles | / 1325.9 |
|---|---|---|---|---|---|
| base (frozen) | 0 | no | 0 | 1007 | 0.759 |
| v4e0 | 0 | yes | 0 | 1044 | 0.787 |
| v4e4 | 0 | yes | 4 | 1044 | 0.787 |
| v4e8 | 0 | yes | 8 | 1085 | 0.818 |
| v4e16 | 0 | yes | 16 | 1117 | 0.842 |
| v4e32 | 0 | yes | 32 | 1235 | 0.931 |
| v4e48 | 0 | yes | 48 | 1374 | 1.036 |
| v4e64 | 0 | yes | 64 | 1517 | 1.144 (FAIL 1.10) |
| r1v4e8 | 1 | yes | 8 | 1111 | 0.838 |
| r1v4e16 | 1 | yes | 16 | 1180 | 0.890 |

Reading: the record stays under price while the elastic margin (link latency variation + buffer read) is <= ~40 edges,
and under the 1.10 gate up to ~55 edges. Scope: compiler/calendar MODEL sensitivity only (no independent audit of the
re-based lowering, no native multi-die run, physical FEC/board latency unbound, zero/one relay assumed). The V4 cross-die
endpoint RTL has no elastic RX buffer yet; that is the open 0az RTL item. Runs: ot-epyc4
/srv/opentallas-scratch/claude/hcoll-g96-elastic-1015/<config>/ (calendar.json etc.).
