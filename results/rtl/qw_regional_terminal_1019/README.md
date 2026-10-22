# Qwen regional clock terminal pickup and bounded structural model

Both existing diagnostic trials FAIL. This packet preserves the original results; no GEN, synthesis, simulation, gate, reroute, RTL, compiler or helper activation was performed. Read-only pickup 2026-10-19 13:41 PDT. Existing ep6 unit oth-ubuntu-2527398-1792434576 completed rB 12:59:28 and rA 13:05:45; wrapper `rA=0 rB=0` means scripts completed, not closure.

| Existing result | rA forwarded unpadded spine | rB ideal entry control |
|---|---:|---:|
| Regional verdict | FAIL | FAIL |
| Intra classes failing / judged | 38 / 655 | 38 / 655 |
| Worst judged intra pair TT / FF ps | 460.8 / 531.6 | 463.2 / 527.3 |
| Owed unlanded instance links / bits | 446 / 186347 | 446 / 186347 |
| Missing-root bit pairs | 8 | 8 |
| Existing landed lanes measured | 153 | 153 |
| Maximum TT→FF lane-lag drift ps | 424.6 | 402.9 |
| Lanes beyond T/2=416.6665ps | 3 | 0 |
| Inserted clock cells (whole vehicle) | 84809 | 76238 |
| Forwarded spine cells / levels / pads | 9272 / 350 / 0 | absent |
| Spine model insertion ps | 18934.0 | absent |

The pair maximum columns are independent maxima across failed classes. These are TT pathfinding/FF diagnostics, not SS qualification. All raw judged pairs and class summaries are in `raw/d/r*/die_clock_check.json.gz`; per-pin TT and FF arrivals are retained. Exact source tools declare bbe250fb5; actual copied script bytes and all packet bytes are hashed. Existing input/output ODB and library hashes are in `remote_hashes.txt`. Raw ODBs remain on ep6; this is not an ODB relocation or mutation.

## Why ideal entries do not repair the failure

`failed_regions.csv` enumerates all 76 mode/region observations using actual entry-pin coordinates and linked pair identities. The same 38 failing regions occur in both modes: 12 contain CB16 clock entries plus reset replicators, and 26 contain only native reset replicators. The latter are an independent structural counterexample to blaming unknown CB16 insertion alone. Their real insertion is qfd_rst_rep SS/FF/TT=[49.0,24.7,33.6]ps and p8=[58.0,29.1,39.5]ps.

For example ideal-control r235 has 17 reset entry pins on x=9402.522um, y=16589.772..17708.652um: a 1118.88um line, not a compact local region. Its full TT entry flop-arrival spread is 467ps; the linked pair-class maximum is a smaller subset (see CSV for exact TT/FF). Ideal-control r35 includes 16 CB16 and 15 reset entry pins spanning x=24323.802..27383.226 and y=18784.332..24089.292um, about 3.06×5.30mm. Its full TT flop-arrival spread is 617.2ps, while judged linked pairs reach TT430.5/FF515.5ps. Full-region spread and linked-pair skew must not be conflated.

The source partitions by existing qfd_clkrx output net and takes a sink median for `local_root`. A shared net name therefore does not imply a physically compact local region. rB defines clocks at each root-buffer input (explicit manifest `clock_source`); it removes the forwarded spine contribution but preserves the long, independently padded regional branches. The final manifests retain large residual spreads after eight trim iterations. Neither additional trimming nor a different ideal-root assumption is an authorized next experiment.

126/146 masters have ASSUMED zero insertion, including qfd_c_b16_dv's sixteen clock entry pins. This is 1125/10880 sink entries, not 126/146 of the entry population; 9755 entries have a supplied real master insertion. Actual per-pin native latency, child root ownership, and source-clock/capture domains remain prerequisites for CB16 qualification. A scalar zero does not establish an internal capture reference. Manifest topology fanout max12 is only the constructed clock graph, not a BUF/INV-transparent data/control fanout census or a native clock electrical check.

The three rA excessive-drift lanes are dvw_io_collective_cmd_free (424.6ps), sf_io_shared_fault (421.9ps), sf_io_fault (418.9ps). All have negative TT/FF destination-source lags; exact signs are retained. Their actual E/K, reset epoch, first valid read and native source/receiver storage setup/hold must be recomputed; accepting the rB control cannot qualify their actual forwarded clocks.

## Bounded next model and integration proposal (ROOT decision required)

1. Replace assumed master latency entries with immutable, current native pin-to-capture SS/TT/FF insertion and root ownership. For a multi-clock child preserve each clock pin and its actual data endpoint association. Missing views and multiple possible producer roots stay NULL; do not fill by instance centroid, maximum latency, or source alias. Current native PG audits elsewhere found PG_HOLD; those timing histories stay preserved and need exact terminal completeness before adoption.
2. Partition the **actual entry/capture graph**, starting with the 26 reset-only failed regions (native references already present). Form bounded physical groups with explicit clock entry, PG-connected legal sites, true clock-pin loads, buffered route segments and complete linked-pair TT/FF checks. Reset replication must preserve the two face landing stages, source release sequence, minimum pulse and first-op epoch. Splitting a net can create new crossings; enumerate them before source changes. Then apply the same method to the 12 CB16 groups with real child insertion. A geometric grid alone is a capacity model, not native closure.
3. For every reassigned data/reset/control endpoint, derive the actual directed source→consumer clock domain from pins and source semantics. Forward long lanes through explicit half-cycle relay stages and land every cross-region data path with registered faces. Recompute actual maximum segment reach≤405um and transparent fanout≤32, using routed/pin geometry, not the bounding box or topology branch count in this packet. Recheck setup and hold, not only skew.
4. Existing 446 crossings remain a separate debt. Prior eb0ee1e0b model gives 186347 bits and a naive four-slot data floor745388FF; 307 proposed rings exceed2kb and 15 links have ambiguous multiple roots. These cannot be copied into arbitrary FF rings. Derive complete record/cohort widths, simultaneous-access schedule, SRAM contacts≤6/um, registered native storage endpoints and local reset/valid masks. Price read capture and output registers, pointer/valid/copy/reset/clock and PG overhead. Repartitioning may increase the 446 count; the incremental count/storage/area is presently NULL.
5. For each new hop and landing publish W/R roots, source publication edge, absolute reset-release epoch, K, E, first valid write/read, collision/lifetime rule and all-corner aperture. Hops and macro read/output staging may add cycles. Current total added SU/MU edges and token latency are NULL; no +0 or generic +1 assumption. Recompile the actual 109 source-age failures only after this ledger and compose with token/layer calendars. No new GEN/GRT/STA until ROOT accepts the priced integration model and critical PNG review.

## Safe-design status and review

All four original critical PNGs are retained at `raw/d/r{A,B}/png/die_{tt,ff}.png`; ROOT was sent paths before any next action. Viewed locally: rA retains distributed stripe branches and endpoint deficits; rB shows ideal root connections as black fan-out lines, which are diagnostic drawing/connectivity and not a physically qualified supply network. These global die images do not establish macro lattice, full-face contacts, full-width row band, protected-cell native PG, final route reach or internal child placement. No REVIEW.json/submit was written.

Checklist: pin registration/reset landing HOLD (source/epoch integration); reach HOLD (new actual endpoint partition); fanout HOLD (full native transparent census); depth HOLD (real complete cones); storage HOLD (307 >2kb naive rings); floorplan/contacts/native PG HOLD; clocks FAIL38classes plus actual drift; schedule HOLD (new ages unpriced). This is a model/evidence artifact only, no accepted waiver.

`derive.py` reproducibly generates CSV/summary from preserved existing JSON; it reads compressed or original JSON. No numerical simulation was needed for an evidence-only pickup. Initial collection requested nonexistent `tiles.tsv/build.json/clock.json`; those tar errors did not mutate remote data. Correct existing `blocks.tsv` and `tt/manifest.json` were subsequently collected. All owned processes finished; no live jobs were launched.
