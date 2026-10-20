# L2H-RSTFB (HBM d4g H.RST.FB, 10-19): station-hosted reset carrier stage

Problem: the GEN2d reset forest needs hundreds of separate hbfd_rrl_c* tiles (12.96 x 6.48 hard view) in channels
already filled by ~56k lane relay stations; homing them is the bottleneck. LH-RSTHOP (1e3fbe31b) let a placed station
host a forest REACH HOP (ot_hbm_rly_rfhop, one flop async-cleared by rfi) -- not a carrier stage, and it breaks
SAFE-DESIGN item 1 (reset must land in 2 registered stages at the face).

Fix: `ot_hbm_rly_rfc` (rtl/hbm_accel/die_glue/ot_hbm_rly_rfc.sv), the structurally safe successor:
rfi async-clears ONLY the 2 landing flops; carrier flop q clears synchronously while land[1] is low; rfo = land[1] & q.
Assertion immediate; release exactly **3 edges** per hosted stage (fixed; a chain of k hosted stages releases its k-th
output 3k edges after the head). Masters `hbfd_rly_<W>_<flow>_rfc` / `_rrfc` (hbfd_rly_rfc_masters.sv) wrap the
UNCHANGED station (ot_hbm_rly / ot_hbm_rly_rr): no data path, row reset or schedule change. Leaf form (rfo also driving
the station's own rs) NOT built: the station rs stays on its row reset / forest leaf as before.

Planner: `reset_forest_layer.py --host-hops prefer|fallback --host-form rfc` remasters hosts to _rfc/_rrfc and charges
3 edges per hosted stage in every age sum (POR trunk, tree nodes, leaf ages, bridge leaves; HOST_AGE). die_case_v16's
reset gate accepts _rfc/_rrfc rfo (and _rrfc rso). Unit test test_host_form_rfc_charges_three_edges: an independent
age walk over the emitted layer equals the domain age; the same masters charged at 1 edge (mutant) break equal age.

Bench (fleet, Verilator 5.050): rtl/hbm_accel/die_glue/test/bench_rly_rfc.sh -- 6 stations chained rfi->rfo, 401
trials of random sub-cycle assertions / glitches / re-assertion during release, exact edge model, ages 3k, immediate
assertion, data / rso unchanged and independent of rfi. pass_48_WE_rrfc.log, pass_136_NS_rfc.log PASS;
fail_witness_{land1mut,combmut,nogatemut,datamut}.log FAIL. Per-kit witnesses: results/rtl/hbm_rly_rfc_1019/.

Kits: tools/ref_tile/specs_hbmrly_rfc (gen_kits.py), 32 = the 16 GEN2d station masters x {_rfc, _rrfc}; exact outline of
the closed station kit, rfi on the i face, rfo on the o face. SAFE-DESIGN checklist in each kit README.

Forest variants: artifacts/hdie-d4/d4g_gen2d/forest_var/hhfbK (prefer, ep7) and hhfbKf (fallback, ep6).
