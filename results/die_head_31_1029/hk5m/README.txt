DIE-HEAD-31 Thu Oct 29 03:10:55 PM PDT 2026 hk5m = fix-only plan delta on hk5l + hd_tile V1/V2 kits (COORD 14:5x: class B default (A) approved).
DELTA  hk5m_delta.py IN=intel2 die-head-30/hk5l/source_plan_hk5l.json OUT=die-head-31/hk5m/source_plan_hk5m.json
       (sha256 10787b972d52bffe...):
       (1) hd_tile cland_tstart_in + clock.start_capture_um (362.4,354.208) -> (380.16,862.944) (in the landing band);
       (2) 565-bit hd_tile i/o abutment group lsb_low -> lsb_high on EVERY member (hd_tile i/o, hd_spn + hd_spn_end
       be_i/bw_i/xe_o/xw_o, 4 spine shim link slots, hd_turn_a/hd_turn_b t slots) + the 289 explicit die-frame port
       orders mirrored (group closed under abutment: asserted).  o[512] now at (708.38,736.58) (io.tcl CHECKED).
       Reversal instead of rotation: same data reach (est. worst data r2r 278.5 -> 308.8 rev / 307.1 rot, on the
       actual V1 launch sites) and no schema change.  0 cycles, 0 flops.
G0C    check.py --completeness --landing source7 sidecar: hk5l 3842 ERROR / hk5m 3842 ERROR, error sets identical
       (0 new, 0 gone), 21/21 types clean, 16 warnings both (CHECKED).  [A first hk5m run showed +561 'pins_file not
       found' = relative core_pins path from a new plan dir; fixed by the same input4 link hk5l uses.]
KIT    hk5m_tile_kit.py = head_tile_source7_kit.py (main da6a5e79e1) on hk5m + class-A patches:
       u_cland_rst_i.d rst_rl_11 -> rst_rl_39 (both depth-3 plain raw chains from rst_root_n, same release cycle);
       15 FIRM targets: sf/s0 (380,863) s1 (420,866) copy0 (600,866) fstart_o (700,867) s2/pd (240,860) agg_1 (250,862)
       agg_2 (480,862) rst_i (480,800) goo/xvo/o_rv (480,600).  RTL diff vs gen5 = that one line (CHECKED).
       V1 = PLACE_DENSITY .35, V2 = 40 % channel blockage y 699.9-734.4 (the die-head-29/30 V1/V2 knobs).
       PLACE intel2 die-head-31/tile_hk5m/v{1,2}/hd_tile units oth-ubuntu-2968755 / 2968760 (15:01, ~50 min).
LEP    head_lep_hk5_kit.py: first hd_lep0N kit (365,496 cells) on the hk5 HEAD-START source (die-head-30/ctl/source):
       gen rc 0, 44 strap pins, 7 private raw exports; V1/V2 PLACE stop at KIT_PREFLIGHT module_closure:
       ot_s81hd_lep_pair (5 hard instances) has NO view (CLOSURE HEAD-013 'core kit missing').  Parent placement needs
       the lep_pair child view first.
