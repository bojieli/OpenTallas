"""SC-REFLOOR-1: port the LAYER-BUDGET-1 leftover-M8 grant hunks (main 14f492184f) into a src tree's gen_phys.py
(kit_core_margins + LAND-RING-2 env opt-in of the tree stay).  usage: port_m8.py GEN_PHYS"""
import sys
p = sys.argv[1]; s = open(p).read()
if "import m8_grant as MG" in s:
    print("already"); sys.exit(0)
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:90]
    s = s.replace(old, new)
rep("""    top = P.type_top_layer(tn)
    pdn = PDN
""", """    top = P.type_top_layer(tn)
    import m8_grant as MG
    m8g = MG.kit_grant(P, tn)        # LAYER-BUDGET-1: leftover-M8 grant (None = off, kit unchanged)
    if m8g is not None and int(top[1:]) < 8:
        top = "M8"
    pdn = PDN
""")
rep("""            ln = f"M{li}"
            pitch, cen, half = S.PART_PG_BANDS[ln]""", """            ln = f"M{li}"
            if ln == MG.LAYER and m8g is not None:
                obs.append(MG.obstruction_tcl(m8g))   # die PG + die tracks from the plan grid, not the default band
                continue
            pitch, cen, half = S.PART_PG_BANDS[ln]""")
rep("""    (kd / "pdn.tcl").write_text(pdn)
""", """    (kd / "pdn.tcl").write_text(pdn)
    if m8g is not None:
        (kd / "m8_grant.json").write_text(json.dumps(m8g, indent=1) + "\\n")
        shutil.copyfile(Path(__file__).with_name("m8_grant.py"), kd / "m8_grant.py")
""")
old = """  if [ \\$rc = 0 ] && { [ $GOAL = route ] || [ $GOAL = finish ]; }; then \\$M do-generate_abstract; rc=\\$?; fi; \\
"""
rep(old, old + """  if [ \\$rc = 0 ] && [ -f /work/m8_grant.json ] && { [ $GOAL = route ] || [ $GOAL = finish ]; }; then for L in /work/run/results/asap7/*/base/*.lef; do [ -f \\"\\$L\\" ] && python3 -I /work/m8_grant.py fixlef --grant /work/m8_grant.json \\"\\$L\\"; done; fi; \\
""")
open(p, "w").write(s)
print("ported")
