import sys, statistics as S
def rd(p):
    d = {}
    for ln in open(p):
        f = ln.split()
        if len(f) >= 4: d[(f[0], f[1])] = (float(f[2]), float(f[3]))
    return d
T, F = rd(sys.argv[1]), rd(sys.argv[2])
ks = [k for k in T if k in F and k[1].startswith("L_") and T[k][0] > 0]
r = sorted(F[k][0] / T[k][0] for k in ks)
re_ = sorted(F[k][1] / T[k][1] for k in ks)
lt = [T[k][0] for k in ks]; lf = [F[k][0] for k in ks]
print(f"leaf pins {len(ks)} TT late {min(lt):.1f}..{max(lt):.1f} FF late {min(lf):.1f}..{max(lf):.1f}")
print(f"FF/TT late ratio min {r[0]:.4f} med {S.median(r):.4f} max {r[-1]:.4f}; early med {S.median(re_):.4f}; model 0.8666")
print(f"FF spread {max(lf)-min(lf):.1f} vs TTx0.8666 spread {(max(lt)-min(lt))*0.8666:.1f}; max |FF - 0.8666 TT| {max(abs(F[k][0]-0.8666*T[k][0]) for k in ks):.1f} ps")
