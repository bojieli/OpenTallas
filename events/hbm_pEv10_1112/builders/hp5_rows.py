"""DIE-HBM-101 hp5 (COORD-approved): seam turnaround lanes each on their own existing hub gcell row below the seam.
hp3 puts every N->N hub turnaround station line at the hub top edge (local y = H = the die seam row).  Here each
family moves to its own 32.4-um die gcell row below the seam (row centre), 0 cycles: regs_um[0] stays at the in pin
(the kit puts station 0 there), regs_um[1:] move to the family's row y.  Bit sites of moved stages shift by the same
dy.  Stations on macros are cleared afterwards by tools/die_plan/ft_nudge.py.
usage: hp5_rows.py IN OUT 'type:slot=row_below,...'   (row_below 1 = first gcell row under the seam row)"""
import json, sys
src, dst, spec = sys.argv[1], sys.argv[2], sys.argv[3]
G = 32.4
D = json.load(open(src)); T = D["partition_types"]; PO = {p["type"]: p["origin_um"] for p in D["partitions"]}
out = []
for it in spec.split(","):
    k, v = it.split("="); tn, sl = k.split(":"); kb = int(v)
    t = T[tn]; H = t["outline_um"][1]; oy = PO[tn][1]
    seam_row = int((oy + H - 1e-6) // G)                   # die gcell row holding the hub top edge
    y_die = (seam_row - kb) * G + G / 2; y = round(y_die - oy, 4)
    s = next(x for x in t["ft_slots"] if x["name"] == sl)
    regs = s["regs_um"]; bs = s.get("bit_sites_um")
    for r_i in range(1, len(regs)):
        dy = y - regs[r_i][1]; regs[r_i][1] = y
        if bs is not None and len(bs) == len(regs) - 1:
            bs[r_i - 1] = [[b[0], round(b[1] + dy, 4)] for b in bs[r_i - 1]]
    if bs is not None and len(bs) != len(regs) - 1:
        for kk in [kk for kk in s if kk.startswith("bit_site")]: s.pop(kk)
    s["note"] = s.get("note", "") + " | DIE-HBM-101 hp5: turnaround line on die gcell row %d (local y %g), 0 cycles" % (seam_row - kb, y)
    out.append((tn, sl, seam_row - kb, y))
D["die"]["label"] = D["die"].get("label", "") + " | DIE-HBM-101 hp5: seam turnaround lines spread to %d rows" % len(set(o[2] for o in out))
json.dump(D, open(dst, "w"), indent=1); open(dst, "a").write("\n")
for o in out: print(o)
