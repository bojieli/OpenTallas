DIE-HEAD-32 Thu Oct 29 05:28:40 PM PDT 2026 (HEAD die owner; successor DIE-HEAD-31). Data on intel2 /srv/opentallas-scratch2/claude/die-head-32.

(1) SHARED FIX ae4669e65 (READY ROOT-MERGE): landing ring_place=ff slot fill follows the bus bit order.
    landing_place.py tags an lsb_high bus's ff band '+ffr'; landing_placement.tcl cland_ffkey sorts bits descending
    for it. lsb_low/default keep '+ff' and the same order. Tests: tools/die_plan/test_landing_place_ringff.py.
    V1r = the DIE-HEAD-31 hk5m V1 kit (gen/hd_tile + PLACE_DENSITY .35) with only landing_placement.tcl regenerated
    (tag ring:i@1.8037+ffr + the ae4669e65 body); PLACE unit oth-ubuntu-2837944 exit 0 (tile_hk5m_r/v1r).
    Placed check (ot_face_flops.txt): s_d[*][565] at y 769.5 (pin y~709), s_d[*][0] near the band top (pin y 1008).
    AUTO-GEOM v1r/auto_geom.{json,png} (render VIEWED), V1 -> V1r (CHECKED):
      pin_reg_p90 238.2 -> 80.0 (worst now cland_dn_fault_i/ready_i 132.4, scalars, not the i bus)
      pin_reg_max 301.6 -> 132.4 PASS;  relay_collapse 8 -> 0 PASS;  r2r 530.0/2 -> 409.5/1 (flt_q[0] -> flt_h[0])
      unchanged: channel_h 1.37 (est., GRT ov 0), clock_reach 864 (one entry, 0 pre-placed clock cells),
      pin_unreg 1 (cland_fstart_in_i), channel_v/col_v WARN 0.759.
    Note (not changed): ring read-select flops u_ring.dch[c].u_dsel/y[j] do not match the 2-D key, sort by name at the
    band bottom (~60 um); they are not on the pin_reg list now.
    V2 knob estimate (no build): the channel y 699.8-734.4 std-cell util is 0.08-0.22 (V1 geom.tsv, CHECKED), below
    PLACE_DENSITY .35, so density/padding knobs do not bind there; channel_h is wire demand (963 nets cross x=500
    inside the channel, est. supply ~1100 tracks) -> no safe placement knob is estimated to move it. V2 not built.

(2) 25-TYPE SOURCE + hk5m: hk5m_delta.py (DIE-HEAD-31) applied to the 25-type source of record adddcbdc
    -> src25m/source_plan.json sha a7435da4 (same 17 field changes + 289 port orders as on hk5l; the hk5m plan of
    DIE-HEAD-31 was the 21-type hk5l lineage). G0C --completeness: base 2680 ERROR/26 WARN, src25m 2680/26,
    findings identical 2706/2706 (CHECKED).

(3) FACE-FLOP RE-KITS on src25m (head_rekit_hk5m.py = head_lep_hk5_kit.py for one type; root = ae4669e65):
    hd_host_n / hd_mesh_e / hd_spn / hd_spn_end gen rc 0; ot_dp_landing_face 2/2/4/4 (CHECKED);
    run_kit floorplan units oth-ubuntu-3673709/3673674/3673695/3673720: SELRANGE, PORT_BIND (1728/290/6359/5184 bits,
    0 missing/extra), FACE_GUARD (1675/274/6260/5099 ok), REG_FANOUT all PASS (CHECKED). LEC running inside the units.
