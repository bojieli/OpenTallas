"""RELAY-PLACE-1 read-only sweep: current-plan kits (kit_wave_stages.tsv plan_current=yes) joined to their
kit_wave_state.json item (die|item|b<block12>); relay_collapse / r2r from the item's last AUTO-GEOM line.
Prints one TSV row per kit with a geom line: die item attempt stage status relay_collapse r2r geom_dir."""
import csv, json, re, sys
st = json.load(open(sys.argv[2]))["items"]
for r in csv.DictReader(open(sys.argv[1]), delimiter="\t"):
    if r["plan_current"] != "yes":
        continue
    v = st.get(f"{r['die']}|{r['item']}|b{r['block_sha'][:12]}")
    g = (v or {}).get("geom") or ""
    m = re.search(r"relay_collapse=\w+\((\d+)\)", g)
    if not m:
        print("\t".join([r["die"], r["item"], str((v or {}).get("attempt")), r["stage"], r["status"], "NA", "NA", ""]))
        continue
    q = re.search(r"r2r=\w+\(([\d.]+)\)", g)
    print("\t".join([r["die"], r["item"], str(v.get("attempt")), r["stage"], r["status"], m.group(1),
                     q.group(1) if q else "NA", v.get("geom_dir", "")]))
