import csv,sys
def rd(f): return {r["net"]:r for r in csv.DictReader(open(f),delimiter="\t")}
e,r=rd(sys.argv[1]),rd(sys.argv[2])
def fl(x):
    try: return float(x)
    except: return None
rows=[]
for n in e:
    if n not in r: continue
    rows.append((n,fl(e[n]["drv_out"]),fl(r[n]["drv_out"]),fl(e[n]["stage"]),fl(r[n]["stage"]),fl(e[n]["wire_max"]),fl(r[n]["wire_max"]),e[n]["nsink"]))
import statistics as s
ds=[x[4]-x[3] for x in rows if x[3] is not None and x[4] is not None]
dw=[x[6]-x[5] for x in rows]
print("nets",len(rows),"stage delta mean %.2f max %.2f  wire delta mean %.2f max %.2f"%(s.mean(ds),max(ds),s.mean(dw),max(dw)))
for x in rows:
    if any(k in x[0] for k in sys.argv[3:]):
        print("%-24s out %7.2f %7.2f | stage %6.2f %6.2f | wire %6.2f %6.2f n%s"%x)
