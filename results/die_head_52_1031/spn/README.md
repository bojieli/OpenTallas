DIE-HEAD-52 helper spn (2026-10-31). hd_spn_end l49s AUTO-GEOM clock_reach 345.64 / clock_tap_sinks 1512.
- far sink = u_rrl_145 (q rst_n_t38) = plan reset.local_taps_um[5] (146.88,155.52); nearest clock tap clk_t1 (354.5,17.3) 345.9 um Manhattan.
  Also beyond 220: local taps (60.48,17.28) 294.0 and (43.2,1537.92) 273.7. hd_spn: (43.2,1537.92) 222.3.
- pre-existing: kit-wave l47 hd_spn_end attempt_2 AUTO-GEOM had clock_reach 345.86 at the same relay and tap_sinks 1557.
- clk_t30 1512 = geometric nearest-tap count (t30.py); the sinks sit in the station band y 1882-1887, x 86-132.
- probe.py: any clock tap edit regenerates the reset tree (reset_tree consumer_taps = clock taps first):
  add 3 taps + 3 sink rows: 133/151 relays change on hd_spn_end (hd_spn +1 tap: 143/225);
  add 1 tap: 125 change; move clk_t30 only: 21 change. Sink rows alone change nothing but fail the explicit-tap radius check.
- kit_l49x.sh: hd_spn / hd_spn_end kits on l49x (rekit + place + AUTO-GEOM GRT).
