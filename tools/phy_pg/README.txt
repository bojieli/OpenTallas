ASSUMED PHY power-access contract v1

The historical Qwen UCIe and SerDes abstracts enclose their M4 PG rails below
M4/M5 OBS. A parent M4 perimeter extension would also cross M4 OBS. They do not
provide legal PG access. This candidate revises the explicitly assumed PHY
interface, with coordinator authorization; it does not represent vendor layout.

The candidate reserves two 0.4um vertical M5 columns near the local east edge.
Their two 0.12um PG straps have 0.14um clearance on each side, above ASAP7's
0.072um wide-M5 spacing. Existing M4 pin rectangles, every signal pin, M1-M4
OBS, dimensions, and timing interfaces stay identical. Only the two declared
M5 access columns are removed from the old body obstruction. No die area or
latency increase. Reserved M5 area: SerDes1250.536um2 (0.0345% of3.6276mm2),
UCIe621.760um2 (0.1028% of0.604662mm2). This is a PG routing reservation, not
extra silicon or a measured power/IR guarantee.

Adoption is EXPLICIT. Fresh case generation uses OT_ASSUMED_PHY_PG_ACCESS=1.
Both tools/qwen_kv_die/kv_die.py case() and qwen_rom_fulldie_b3r2.py case_pdn()
call the hook. After any later bind_real replacement, use the manual hook on a
NEW case before running floorplanning:
  python3 tools/phy_pg/apply_case.py CASE --ack-assumed-phy-contract
The hook refuses any existing *.odb and repeat application. Preserve frozen
runs. Historical LEFs remain in the repository; each new case preserves its
original LEF and PDN text in *.historical-original.*.txt and records exact
source/candidate/helper hashes in assumed_phy_pg_access.json. Rebinding a PHY
after the hook will fail the runtime M5 access preflight. Prefer binding all
real views first and then applying the manual hook once.

The helper removes the PHY from old macro grids and installs a two-track
M4->M5->M8 grid. R0/MX use the eastern access; MY/R180 use its mirrored western
location. Quarter-turn orientations fail closed. OT_PDN_BBOX_OBS must keep the
small exact PHY OBS; its shared helper recognizes the explicit case manifest
and preserves these masters unchanged. The default historical flow is unchanged.

Reproduce the mechanism fixture:
  python3 tools/phy_pg/fixture/prepare.py REPOSITORY OUTPUT_DIR
Stage OUTPUT_DIR under /srv/opentallas-scratch on eligible fleet hosts. Check
the coordinator lock, then run with ot-run --mem4 --threads1 --dirDIR --
docker run --rm -v DIR:/work openroad/orfs:asap7lock bash /work/run.sh
(Use normal shell spaces in flags: --mem 4 --threads 1 --dir DIR.)

Actual fixture source in fixture/; source-bound receipts in evidence_20261015/.
Final admitted ot-run EPYC4 unit2911565-1792125166 exited0 on pinned ORFS
OpenROAD26Q3-1510-g6cb3f2b704. Eight PHYs (both types at R0/MX/MY/R180) pass
check_power_grid for both VDD and VSS. Geometry readback verifies86,016 routing
shapes including via routing enclosures;40,824 shapes inside macros;16 M5
straps;1,118,889 opposite-net comparisons;zero shorts, zero obstruction
violations, zero signal-pin overlaps, and72nm M5-to-OBS spacing. The historical
LEF mutant is rejected; an injected opposite-net wire produces364 detected
shorts. Nine Python regression checks pass.

This fixture proves the declared access geometry and connectivity only. It does
not close any die, qualify foundry PHY IP, prove analog/IP internals, or replace
full-die route/DRC/IR/EM and timing checks. Actual full-die integration must retain
the explicit ASSUMED_UNQUALIFIED PHY boundary and check neighboring geometry.
