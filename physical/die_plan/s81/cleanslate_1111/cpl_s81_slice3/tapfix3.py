# tapfix3.py PLAN TYPE TAP X,Y : nearest point to X,Y (4.32 lattice spiral) where taps.grid_explicit_taps passes
import sys; sys.path.insert(0, ".")
import schema, taps
P = schema.Plan(schema.load(sys.argv[1]), sys.argv[1]); tn, nm = sys.argv[2], sys.argv[3]
mx, my = map(float, sys.argv[4].split(","))
q = [x for x in P.types[tn]["clock"]["added_taps"] if x["name"] == nm][0]; x0 = list(q["xy"])
last = ""
for r in range(0, 40):
    for i in range(-r, r + 1):
        for j in sorted({-r + abs(i), r - abs(i)}):
            q["xy"] = [round(round(mx / 4.32) * 4.32 + i * 4.32, 3), round(round(my / 4.32) * 4.32 + j * 4.32, 3)]
            try:
                taps.grid_explicit_taps(P, tn)
                print(tn, nm, "from", x0, "to", q["xy"]); sys.exit(0)
            except ValueError as e:
                last = str(e)[:160]
print("none", last)
