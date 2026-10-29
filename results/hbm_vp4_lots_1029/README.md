VP4 isolated slot search on root C25c_fold actual plan, 2026-10-29 00:15 PDT.

Run `pack.py SRC_DIR OUT_DIR`, then `render.py SRC_DIR/die_plan.json`. No plan is mutated and no physical job runs. The report names its source plan/hash. Search covers all8.64um-grid origins for501.12x311.04um VP4 outline, retains all other hard cores including track offsets, all declared soft lots, clock branch buffers and published internal-register cell sites, and excludes an8.64um clearance around every obstacle. Station footprint1.404x.27um. Both hubs have zero ft_slots: explicit FT-bit-cell count is zero there, and unpublished per-bus bit spreading cannot be certified. Existing published site rectangles alone already rule out isolated placement.

Result: NO all-obstacle legal lot for any of the four VP4instances. There are8304hard/soft-clear positions in NW and7440in NE; every one hits at least9(NW)/12(NE) published internal station sites. Nearest hard/soft-clear locations require centre displacement3137.832/639.792/1702.512/795.312um for NWq0/NWq1/NEq0/NEq1, respectively; preserving old endpoints/stations would fail33/37/33/37legs over405um. All exact collision-site indices and normalized same-face endpoint lower bounds are in the report. Pin regeneration and real corridor paths are not claimed.

For a JOINT re-pack, nearby partial alternatives within405um centre displacement require at least2/2/2/1other lots moved (NWq0/NWq1/NEq0/NEq1). The first alternatives are:

- NWq0 origin2384.64,786.24: move hard u_smw_Q__q0 and u_xl_Q_ctl__q0;100station sites collide;15endpoint legs exceed405um, worst711.813um lower bound.
- NWq1 origin7223.04,492.48: move hard u_hb_idx__op_Q__q1 and soft u_hb_vms_Q;39station sites;32legs exceed405, worst906.590um.
- NEq0 origin2790.72,414.72: move hard u_hb_coll_Q_vm__q0 and soft u_hcollks_Q_p1__q0;29sites;31legs exceed405, worst859.477um.
- NEq1 origin6929.28,388.8: move hard u_xq_Q_p1_bfq3;21sites;34legs exceed405, worst862.272um.

`nearby_conflicts.png` viewed: expanded VP4 boxes visibly overlap these compact neighbors and station corridors. Verdict FAIL for isolated relocation. These are planning inputs, never accepted origins or routing clearance. Die owner must jointly re-pack neighbors, update exact pins/clock islands and re-place affected stations within reach405 (price added stages if required). This avoids treating a local channel-feasible core outline as a feasible die plan.
