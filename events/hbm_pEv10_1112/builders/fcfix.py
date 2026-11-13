# fcfix.py IN OUT TSV : price kit-inserted stations (LATCHECK-1 UNPRICED_KIT_STATIONS): lane fixed_cycles += delta
import csv,json,sys
src,out,tsv=sys.argv[1:4]
d=json.load(open(src)); L={x["id"]:x for x in d["lanes"]}; n=0
for r in csv.DictReader(open(tsv),delimiter="\t"):
    if r["verdict"]=="PASS": continue
    assert r["class"]=="UNPRICED_KIT_STATIONS", r
    x=L[r["lane"]]; old=int(x.get("fixed_cycles",0)); new=old+int(r["delta"])
    x["fixed_cycles"]=new
    x["note"]=(x.get("note","")+f" | DIE-HBM-101 11-12 LATCHECK-1: fixed_cycles {old} -> {new} (kit stations src {r['src_kit_ist']} + dst {r['dst_kit_ist']} priced; as-built delivered {r['delivered']})").strip(" |")
    n+=1
json.dump(d,open(out,"w")); print("fcfix lanes",n)
