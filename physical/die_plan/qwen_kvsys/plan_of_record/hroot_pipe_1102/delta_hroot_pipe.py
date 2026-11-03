"""DIE-KV-61/hroot 11-02: kv3_hroot one-block reach event (OWNER/COORD ruling 11-02: retiming / pipeline stages).

geom2 (die-kv-59/geom2 3_place, = current main kv3_hroot) has 19 r2r captures > 405 um (max 1010):
  * 8 ring -> u_bin_*/eq and 3 bin q: the single landing check u_efault takes the epoch eq of all 9 in-boundary
    stations, whose rings span the E and S faces (1757 um apart) -> no 2-hop placement exists.
    Fix: +1 registered stage per epoch (plan cells u_eqp_*, plan_cells_b3.json) and u_efault AGE 35->36, +1 stage
    u_fchp on the S-ring fault input of u_fch; o_fch_hroot_Q_q = the old stream delayed one edge (health plane only).
  * 10 u_rrl_101 (leaf tap 14) -> bin eq / u_efault reset: reset.consumer_localization onto the nearest equal-depth (7)
    tap relay; 0 cycles, release table unchanged.
  * u_u_fch.q -> o_fch bout 630 um: FIRM u_fch between u_efault and the E face.
  * 4 kvs_ctl bin q relay sites at 406-442 um from their ring dsel: moved to the minimax point.
Also: i_kvpc_Q_N_o_next landing band = the Codex FF-only band (codex/geom-1101@0a7ea64e1) against GRT window overflow.
"""
import json, sys
from pathlib import Path
here = Path(__file__).resolve().parent
p = Path(sys.argv[1] if len(sys.argv) > 1 else here.parent / "plan_c.json")
P = json.loads(p.read_text()); I = json.loads((here / "inputs.json").read_text())
t = P["partition_types"]["kv3_hroot"]
t["relay_sites"].update(I["relay_sites"])
t["reset"]["consumer_localization"] = [dict(instance=i, pin="rst_n", old_reset="rst_n", new_reset=n, clock_net="clk")
                                      for i, n in sorted(I["reset_localization"].items())]
b = t["clock"]["landing_contract"]["bands"]["i_kvpc_Q_N_o_next"]
old = list(b["rect_um"])
for k in ("max_pin_to_band_hop_um", "resized_from_um", "resize"):
    b.pop(k, None)
r = [1326.24, 86.4, 1412.64, 120.96]
b.update(rect_um=r, ring_place="ff", fill_axis="x", spread=1.0, area_reserve_um2=round((r[2]-r[0])*(r[3]-r[1]), 3),
         witness_correct_bit_storage_reach_um=140.343,
         placement="DIE-KV-61/hroot 11-02: Codex band PREP codex/geom-1101@0a7ea64e1 (FF-only, 1585 ring FF, comb to GPL, "
                   "bit storage reach 140.343 < 150, 0 new r2r) vs GRT50 overflow window x1350..1400/y0..50; was rect "
                   + json.dumps(old) + " ring_place all")
tag = "DIE-KV-61/hroot 11-02"
if tag not in t["note"]:
    t["note"] += (" | " + tag + " (OWNER/COORD retiming ruling, one-block): +1 eq stage per landing-check epoch (u_eqp_*, "
                  "efault AGE 36) + u_fchp; reset consumers localized to equal-depth taps; relay_sites for the efault/fch "
                  "cone + 4 kvs_ctl bin q; kvpc_o_next FF-only band (hroot_pipe_1102/)")
p.write_text(json.dumps(P, indent=1) + "\n")
print("relay_sites", len(I["relay_sites"]), "localized", len(I["reset_localization"]))
