#!/usr/bin/env python3
"""S81/PORTFIX-DEAD (2026-10-25): die-top rewrite for the dead-port items D-CAPEND and D-MURT (D-SVCARITY: run
tools/s81_dv/svc_rs/svc_rs_face_bind.py first; D-XWV / D-GLUE are inside the slice masters, no die-top change).

  dead_die_rewrite.py IN.v OUT.v REPORT.json

Per slice instance u_s_<c><N|S>:
  .rt({<k>'d0, lanes...})  ->  .rt({lanes...})      k = 350 (3 frames) or 140 (6 frames); any other tie is an error
  module                    ->  its row-end variant:
      ot_s81sl_slice_c1x_k8_cap5r_w   -> _w_w3 / _w_e6      ot_s81sl_slice_c3x_k8_cap5r_w -> _w_w3
      ot_s81sl_slice_sukv_raw512      -> _w3                ot_s81sl_slice_iq             -> _iq_w3
      ot_s81sl_slice_lep*_mu_72       -> unchanged name (the four die lep masters are 6-frame row ends: rt 420 b in place)
  3 frames: the .ck_CAP_CE(...) connection is removed (capc5r_w3 has no CE region); the net is reported (clock plan).
D-MURT check: u_s_0S / u_s_7S must carry no .mu_rt connection (their masters have no mu_rt port).
"""
import json, re, sys

VAR = {"ot_s81sl_slice_c1x_k8_cap5r_w": {3: "ot_s81sl_slice_c1x_k8_cap5r_w_w3", 6: "ot_s81sl_slice_c1x_k8_cap5r_w_e6"},
       "ot_s81sl_slice_c3x_k8_cap5r_w": {3: "ot_s81sl_slice_c3x_k8_cap5r_w_w3"},
       "ot_s81sl_slice_sukv_raw512": {3: "ot_s81sl_slice_sukv_raw512_w3"},
       "ot_s81sl_slice_iq": {3: "ot_s81sl_slice_iq_w3"}}
LEP = re.compile(r"ot_s81sl_slice_lep\w*_mu_72$")
INST = re.compile(r"^(\s*)(\w+)(\s+#\([^;]*?\))?\s+(u_s_[0-7][NS])\s*\(")


def main():
    src, dst, rep_path = sys.argv[1:4]
    lines = open(src).read().split("\n")
    rep = {"instances": {}, "unloaded_clock_nets": [], "errors": []}
    for i, ln in enumerate(lines):
        m = INST.match(ln)
        if not m:
            continue
        mod, inst = m.group(2), m.group(4)
        r = re.search(r"\.rt\(\{(\d+)'d0, ", ln)
        if inst in ("u_s_0S", "u_s_7S") and ".mu_rt(" in ln:
            rep["errors"].append(f"{inst}: .mu_rt still connected (D-MURT)")
        if not r:
            rep["instances"][inst] = {"module": mod, "frames": 8, "change": "none"}
            continue
        k = int(r.group(1)); nf = (560 - k) // 70
        if nf not in (3, 6) or k % 70:
            rep["errors"].append(f"{inst}: rt tie {k}'d0 not a 3- / 6-frame end"); continue
        new = ln.replace(r.group(0), ".rt({", 1)
        if LEP.match(mod):
            if nf != 6:
                rep["errors"].append(f"{inst}: lep master with {nf} frames (variants exist for 6 only)"); continue
            nmod = mod
        elif mod in VAR and nf in VAR[mod]:
            nmod = VAR[mod][nf]
            new = new.replace(f"{m.group(1)}{mod}", f"{m.group(1)}{nmod}", 1)
        else:
            rep["errors"].append(f"{inst}: no {nf}-frame variant of {mod}"); continue
        dropped = []
        if nf == 3:
            c = re.search(r",?\s*\.ck_CAP_CE\(([^)]*)\)", new)
            if c:
                new = new.replace(c.group(0), "", 1); dropped.append(f".ck_CAP_CE({c.group(1)})")
                rep["unloaded_clock_nets"].append(c.group(1))
        lines[i] = new
        rep["instances"][inst] = {"module": mod, "new_module": nmod, "frames": nf, "rt_tie_removed_bits": k,
                                  "connections_removed": dropped}
    open(dst, "w").write("\n".join(lines))
    json.dump(rep, open(rep_path, "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "instances"}))
    for k, v in sorted(rep["instances"].items()):
        print(k, v)
    sys.exit(1 if rep["errors"] else 0)


if __name__ == "__main__":
    main()
