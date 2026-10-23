# Main-based Qwen segment-calendar functional restore

Base: 59c4ffb8c. Source commits b35014d2d (exact cherry-pick ff9abcf4f) and 9555927bd (two filename fixes from 2d8838dfe). No h16y branch ancestry imported. Historical img0/imgh fixtures are exactly the four blobs at 2d8838dfe and are separately hashed in SOURCE_SHA256.json.

Fresh Verilator 5.050 jobs on ot-epyc9: oth-ubuntu-4084511-1792753063 and oth-ubuntu-4090177-1792753140, both terminal exit 0. Remote root /srv/opentallas-scratch/claude/codex-qw-segcal-main-1023.

Soft and hard head each pass the base image (123/123) and LM-head stage37 image (131/131). Late first segment-G row bmut3 is caught in both (129/131). Hard-head actual RTL mutations 36 (base0-only head calendar) and37 (base0-only G-XPF start) fail128/131 and130/131. Default-off SEG_CAL=0 base image passes123/123. Raw logs and return codes retained.

Scope: source-functional compiler/programme replay, not full token datapath or physical closure. The stage37 events, fixed issues/END, ROM command and G-XPF are checked. Slice/native neighbours respond on compiled schedules. Existing landed-parent lp RTL has a separate stale segment-calendar wiring gap and is NOT qualified by these tests. Historical current-main token NO_RESULT remains preserved; this fresh positive does not overwrite it.
