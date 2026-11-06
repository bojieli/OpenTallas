Complete native M6 clock landing (explicit standalone opt-in)

This tool routes a complete real driver-to-hard-macro clock connection. It supports only R0 instances of one explicitly selected master/count, a single native M5 `clk` PORT rectangle, actual child OBS below M6, native VIA56 enclosures, and native M5/M6 track grids. NDRs are refused. Planning checks the real PORT, via enclosures and M5/M6 special-wire and via clearance before writing any fixture. No GEN recipe is activated.

Run on the physical host with an immutable retained GRT DB and its complete matching tools cohort:

    python3 tools/die_plan/complete_clock_landing.py stage --db ORIGINAL.odb --out NEW --master MASTER --count COUNT
    ot-run --hosts HOST --mem 8 --threads 4 --dir NEW -- bash run.sh prepare 8 4
    python3 tools/die_plan/complete_clock_landing.py render --fixture NEW/fixture_geom.json --out NEW/review.png

View the image and record actual findings in NEW/REVIEW.txt. Then:

    ot-run --hosts HOST --mem 8 --threads 4 --dir NEW -- bash run.sh route 8 4

The source DB is bound read-only and its SHA256 must remain unchanged across phases. NEW must be fresh. The component retains every placed physical instance, macro and PG obstacle. Its only routed nets are the selected real drivers to temporary M5 waypoints outside the macro body. Normal GRT/DRT routes those connections on M2-M5; a nonempty DRC report stops the tool. The temporary waypoints exist only in that discarded component fixture.

Native wire operations are exported with explicit names and real driver placement/master/orientation contracts. Junction, NDR, block-via and unhandled operations fail closed. Merge reads the original complete DB again and encodes the real driver route plus native VIA56/M6 lateral escape as a complete FIXED wire. The receiver tag binds to the actual native macro `clk` PORT. Original net connections, other wires, placed cells, child ports, LEFs, RTL and SDCs remain in the original complete DB. Added cycles: 0.

The native graph audit checks real wire and via metal against transformed actual ITerm PORT rectangles. Every selected driver must connect physically to its real macro port, with no orphan metal, no wire above M6, no special-wire bypass and no M1-M5 access inside the macro body outside its real PORT. A partial FIXED landing fails this check even if DRT reports zero violations.

A mechanism PASS is pending normal full-core routing and signoff. The isolated component does not represent interactions with other signal/clock routes. Adopt its complete_clock_merged.odb only into a new private full-core continuation, preserving the original GRT and failed verdict. Review the new clock resource/baseline, run normal full data/clock DRC, layer/access checks, TT/FF/DRV, signoff and routed LEC, and export actual final PG/OBS views. M6 must already be covered by the owner's reviewed resource/parent interface event. No gate, timing mode, margin, clock, child interface or cycle exception is supplied here.

Focused native evidence (2026-11-06 BKSEL):
- Original real routed baseline: 16/16 physically connected; all 16 expose the known illegal M5 takeoff inside OBS.
- Inherited L2 partial FIXED prototype: DRT 0, but the audit rejects 16/16 disconnected drivers, each retaining only six landing metal shapes.
- Complete component: native GRT 0 in 11 s, 16 real driver connections, native DRT 0, peak 4.63 GB. Full original interface merged with complete fixed clocks: graph PASS 16/16, no illegal OBS access or orphan metal.
- Actual native via enclosures are M5 [-12,-27,12,27] and M6 [-23,-16,23,16] DBU, with M6 width/spacing32 DBU. Cached PG-via layer membership avoids repeated shape scans; both M5 and M6 landing segments are checked against existing special metal and conservative actual via bounds. The guarded plan remains identical on the measured fixture.
- Canonical prepare produces a byte-identical fixture to that completed native component (SHA256 d3e2b463e56d5a88b892634f236f11386b7f3bd70319d935e3c222f8847ec06a). Its canonical export/merge/audit passes using that exact completed component; no redundant physical rerun was used.

Actual artifacts: intel1:/srv/opentallas-scratch2/claude/codex-bksel-land-1106/{canonical_l2,complete_clock_native_audit.json}; old connected/illegal control on epyc6:/srv/opentallas-scratch3/claude/codex-idx-cb50-1106/baseline_connected_illegal.json. These are mechanism evidence, not a signed BKSEL view.
