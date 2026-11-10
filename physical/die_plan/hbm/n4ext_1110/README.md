# n4ext1110 (HBM-COLLECT-1 / N4-PLAN, COORD ruling (A) 11-10): adopt the grown n4ext outline

This is a die-local HBM plan event. It adopts the signed-off `ot_hnx_fused_hub_n4ext` view (`n4c_eco2pin`, routed LEC
EQUIVALENT 57654/57654, `6_final.odb` sha256 `eb531164288d7bb0...`) at its built outline:

* Outline goes from 216 x 207.36 to **293.76 x 250.56 um**. The origin is kept at (734.4, 5503.68) in the root frame.
  The core grows east and north only, into [950.4, 1028.16] x [5503.68, 5754.24] plus the top strip
  [734.4, 950.4] x [5711.04, 5754.24]. Pin cycles added: 0. No rebuild.
* The delta is DIE-HBM-89's `mk_plan_n4rf.py`, copied here unchanged. As DIE-HBM-97 ruled (11-10 03:49),
  `apply_event.py` re-applies it on the wave plan `die-hbm-97/plan_r2_restore` and writes a copy,
  `hbm-collect-1/n4plan/plan_r2_n4ext`. It changes only these items:
  * type root `hard_cores` / `contents` `u_mu_fused_root`: outline and `pins_file`;
  * `internal_stations` `bus:n4x_up_ne_i` / `bus:n4x_dn_ne_o`: landing x moves from 950.4 to 1028.16. The stations stay
    at 1440 and 1195.2, so the last hop drops from 244.8 to 167.04 um;
  * the clock tap `u_mu_fused_root.clk` and `clock_entries` root.u_mu_fused_root move to the re-centred island;
  * `core_macros` `ot_hnx_fused_hub_n4ext` (3 SRAMs, one centred column);
  * the pins table `cores/ot_hnx_fused_hub_n4ext__293.76x250.56__n4rf.json`. It moves the 444 E pins (x = W - 0.096),
    rst_n (y = H - 0.096) and the clk entry; the W and S faces are unchanged.
* Pins against the signed view: all 1126 signal pins have the same name and layer, and every table position lies
  inside its routed pin box in `6_final.odb` (only VDD/VSS are extra). The clk pin is M5 at (146.88, 120.96). The 3
  macros match the plan rectangles to within 0.012 um.
* Plan check: `plan_check.txt` (tools/die_plan/check.py --completeness --plan-geom report, base vs new, same tool).
* Root clearance: in the new plan, no other root plan object (hard core, station register, ft object, tap or entry)
  lies inside the added area or within 20 um of it. The only points inside are the two re-landed E stations. The
  nearest hard core, u_mu_fused_program, keeps its 34.56 um S gap.
* Parent pins and route: the parent-side pin refresh is the two E station landings, moved onto the new E face. W and
  S faces are unchanged, root partition pins are unchanged, and no other type or pin table changes. A root route or
  GRT around the box cannot run today. Root (hbm_arch_root) is a soft 8.9M-cell partition, and its wave rows are at
  preflight FAIL, so there is no built root. The M2-M5 demand through the added 28,815 um2 (macro OBS to M5) is
  therefore UNMEASURED until the first root GRT.
* Die STA of the new pins: there is no real-view die STA either, for the same reason (every n4ext pin lands on root
  logic). The closest real measurement is the signed view's own sign-off, which times all 1126 pins against the IO
  virtual clock: TT setup +16.25 ps (TNS 0), FF hold +4.97 ps (SDC), DRC 0. The E-station hop is 167.04 um, under the
  450 um target. The root tap moves 38.88 / 17.28 um (881.28, 5624.64). The signed TT pin-flop insertion is 292.47 ps
  against the tap's plan insertion of 250 ps; under OWNER 11-03 that goes to the die clock / die STA band, not to this
  core. It stays NEEDS_PARENT until the root is built.
