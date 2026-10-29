import re,sys
def parse(f):
    out={};cur=None;seen=False
    for l in open(f):
        m=re.match(r'LEAFHDR (\S+) (\S+) fo (\d+) sink (\S+)',l)
        if m: cur=m.groups(); seen=False; continue
        if cur and not seen:
            m=re.match(r'\s*([\d.]+)\s+([\d.]+) \^ (\S+)/Y',l)
            if m and m.group(3)==cur[0]:
                out[cur[0]]=(cur[1],int(cur[2]),float(m.group(1)),float(m.group(2))); seen=True
    return out
r=parse(sys.argv[1]); g=parse(sys.argv[2])
rows=[(k,)+r[k]+(g[k][2],g[k][3]) for k in r if k in g]
rows.sort(key=lambda x:-(x[3]-x[5]))
print("leaf master fo stage_rt arr_rt stage_grt arr_grt d_stage")
for x in rows[:20]: print(x[0],x[1],x[2],x[3],x[4],x[5],x[6],round(x[3]-x[5],2))
leaves=[x for x in rows if x[2]<=40 and not x[0].endswith(('_br','_r0'))]
import statistics as s
a=[x[4] for x in rows if x[0].count('_')==2 and not re.search(r'_(br|r0)$',x[0])]
