# Original HBM v13 GRT verdict and preserved STA chain

The original k16 pathfinding GRT exited 0 at 20:14 PT after 5,935 seconds, with
**421,308 bundle tracks of overflow**. This fails routing; v12 had 524,552.
Process 3045759 and its container are terminal. Source generator hash matches
commit a44b378b6 exactly. This evidence does not approve v13 geometry or contract.

| Layer | Exact router overflow |
|---|---:|
| M4 | 34,405 |
| M5 | 73,580 |
| M6 | 123,958 |
| M7 | 63,130 |
| M8 | 69,667 |
| M9 | 56,568 |

The full gcell usage map was streamed by the included collector through an
admitted 4 GB / 1 thread job. Its pooled 4x4 blocks yield 368,251 positive
usage-capacity units: pooling hides fine-gcell excess, so this spatial diagnostic
cannot replace the exact router total. 92.66% lies in the binned hub envelope
x10–20/y8–18 mm. Largest 2 mm bins: x14–16/y14–16 = 81,423; x12–14/y14–16 =
75,188; x10–12/y14–16 = 33,211; x14–16/y16–18 = 31,875. Congestion remains in
the same NW crossing area. The raw congestion report lists only 20,000
violations; do not treat its net-family frequency as exhaustive coverage.

The original local collector 2624641 was conclusively absent, with no downstream
STA logs or running STA process. A replacement lightweight collector runs in its
own setsid/flock group2925271 (bash2925273), waiting on existing original
clock handles3075393/trunk and3075394/hreg. Both are actively writing FF tree
reports; their SS reports are complete. htop3075392 finished at20:55 with exit0
and complete SS/FF reports. No clock or GRT run was duplicated or restarted.

The collector requires exit0 plus nonempty SS/FF reports, verifies the repaired
STA tool SHA, transfers the measured trees to EPYC1, and uses ot-run for clock
recording/preparation and independent placement/GRT STA. Its --dir is the actual
EPYC1-only STA case directory, because the shared parent directory also exists on
AGI without the source inputs. It checks coordinator ownership before every
submission. Classifications use the actual bound case libraries and original
plan, including analytical STA-added relay metadata and untimed coverage.

The existing real-scale STA case has87,013 instances; the original k16 GRT case
has80,377. Their manifests are preserved. These are related pathfinding cases,
not interchangeable release evidence; the real-scale GRT+STA remains pending.
Collector logs: /tmp/claude-1000/hbmdie13/collect_v13_codex.log. Next: collect
original FF clock completion, confirm preparation and both STA units start, then
classify SS/TT/FF endpoints and update the stream's top table.

After preserving these reports and the streaming spatial summary, generated
failed-route inputs, pooled raw map and wirelength CSV were deleted from AGI.
Its former149 MB GRT directory retains only8.6 MB of reports/logs/manifest.
The existing EPYC1 STA case and live clock trees remain intact.
