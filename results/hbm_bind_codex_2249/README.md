# HBM scorer row-1 source locality candidate

Current die plan remains d29d `1aefc6184b2a`. Baseline strict bind is 81 UNPLANNED pairs / 57,312 bits, zero EMIT. The predecessor b30a eight-register move is rejected: 57,316 bits. Its b30p bit list uses that rejected map, so this work uses the actual d29d `map_d29c.json` instead.

The large b100→b102 crossing is a source register placement problem. A single 4,396-bit scorer input register drives both rows. Row 1 consumes 2,176 payload bits exclusively; their D sources are the two hub key buffers `keybuf.gp[2/3].u_line.key_out`, 1,088 bits each. Six other input registers share 570 query/control bits between rows (query payload 568, query valid and key valid).

`build_row1.py` preserves every existing non-top module and changes only the top NE/NW quarter instance references to four isolated wrapper/scorer modules. It splits the exclusive key payload register bits into b102 and replicates the six shared input register slices there. Only the row-1 first leaf input ports are rewired to the replicas. Every D bit, clock connection, original cell and other port is checked against the selected source. Added area is 570 FF per half, 1,140 per die; source latency is unchanged. The original source cache and modules remain available.

The actual candidate register vehicle passes 4,096 edges × 5,492 compared bits with zero mismatches. Its injected input mutant is caught on all 4,096 edges. This is a functional register transformation check, with no physical delay model. The script's nominal clock is 833 ps; its 1-ps simulation precision rounds the two half periods to a simulated 834 ps, so the `clock_ps` result field is nominal and establishes no timing claim. The die clock contract remains 833 ps.

Actual strict bind on the candidate is **83 UNPLANNED pairs / 57,312 bits, zero EMIT**; unmapped, tied, undriven and multiply bound are all zero. Per half, b100→b102 shrinks from 2,777 to 31 metadata bits and a new hub→b102 crossing carries 2,746 bits. Thus the candidate establishes the exact source form for a hub-side physical corridor; it does not reduce total unresolved bits by itself. The plan owner must build the two 1,088-bit key paths plus the 570-bit query/control path and align the residual metadata. Added landing/hop cycles remain a physical plan/model obligation. No P&R, STA, token-pass or adoption claim is made.

Artifacts live on intel1 under `/srv/opentallas-scratch2/claude/codex-hbm-bind-2249`:

- `row1/asbuilt.json`: candidate SHA256 `5aa082b452953e057060fa06b61bd0cc988cf860c3f7b5c9598cd13ea4358a55`, generated from source SHA256 `ce2560d35809481e138b82e47c131baec1f425c748fc8704a082af1619589b8d`.
- `row1/{manifest.json,map.json,receipt.json}`: exact source/cut mapping and transformation record.
- `row1_bind/out/bind_report.json`: full strict result; `bind.rc` is 1 because crossings remain.
- `row1/proof_v3`: actual generated register miter, good run and caught mutant.

All jobs for this milestone are terminal. Earlier builder/proof failures are retained in their distinct logs: an assertion counted 569 instead of 570 shared bits; the first proof generated a zero-width constant; the second lacked a simulation timescale. These generator/bench failures are fixed in the recorded passing constructor/proof.
