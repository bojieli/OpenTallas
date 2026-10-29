# T2 geometry preparation, 2026-10-29

Personally viewed `t2_candidate.png` after generating it from the T2 macro and
pin tables. This is a candidate estimate, with no physical run submitted.

The same 55 SRAMs sit on the six-column lattice, with continuous vertical
channels and a wider middle channel holding the existing centre clock entry.
The 4.32-um macro halos are disjoint. The top macro ends at y432.888; the
candidate outline is y444.96, leaving 12.072 um for the N pin band. The source
shape used 40.152 um. All data pin x coordinates and all macro sites stay fixed.
The candidate pin table and LEF explicitly put the clock at the existing
planned island (147.948,236.52), fixing the old plan-LEF/physical-entry mismatch
in the candidate contract before any parent composition.

The parent preview has four children along its link face and one uninterrupted
street for the other link-face windows. This removes the large sideways
coll_i/coll_o landing buses in the prior uniform-row proposal. The west/east
hard-child module names and pin files are distinct; N-face parent copies use
MX. The rest of the parent remains available for its mapped logic and SRAMs.

Estimate: aspect 1.504; standard-cell fill of the free area 0.15050, using
LP2 synthesis's 10,485.6 um2 logic and 62,002.4 um2 SRAM. This has little fill
headroom, so actual geometry decides. The N pin-band packing and parent clock
and PG connections still need an actual placed view; the parent requires
signed child LEF/lib abstracts and its fix-only window event before build.

Verdict: prepared estimate only. No CTS/route authority. First resolve the
current full-shape LEC failure, then judge the actual placed image and clock
model under GEOM-55's existing conditions. No data/control cycles added.

Reproduce with `prepare_t2.py` then `render_t2.py`. Generated large candidate
plan/pin/LEF files are left in the worktree's `t2/`; they are not canonical
physical plans or signed views.
