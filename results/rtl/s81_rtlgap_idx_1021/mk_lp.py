# synthetic land plan for the idx72 cut: every landing of the cut gets a lane flight F inside its window
# [K-D+1, K-1] (D=4): corner tt -> F = K-1 (window top), ff -> F = max(K-3, 0) (window bottom). The landing output is
# independent of F inside the window (dv_slice_cut --land-plan doc), so both corners must give the same bench result.
import json,re,sys
sv=open(sys.argv[1]).read(); T=833.0
rows=[]
for m in re.finditer(r'dsfd_dvland_\d+ (ld_\w+) \(.*?\.k\((\d+)\'d(\d+)\)', sv):
    K=int(m.group(3)); rows.append(dict(link=m.group(1)[3:], E=K, K=K, D=4,
        s1={'tt': -(K-1)*T + 1.0, 'ff': -max(K-3,0)*T + 1.0}))
json.dump(dict(T_ps=T, D=4, note='RG-IDX synthetic idx72 land plan (window-top tt / window-bottom ff flights)', links=rows), open(sys.argv[2],'w'), indent=1)
print(len(rows))
