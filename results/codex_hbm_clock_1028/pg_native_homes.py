"""HBM native home prototype aligned to the measured PG gap lattice.
Derived from retained obs_pg.tcl: M9 PG stripes12.96/17.28um leave
[6.48,10.8]um gaps; native1.62um body home is phase7.83. M8 stripes
.48/2.16um leave [.24,1.92]um gaps; native row phase1.08 clears them.
No PG/clock contract changes, trims, pads or post-balance move overlay.
"""
import math,inspect

def install(D,site):
    original=site.nearest;legal=site.legal
    def home(q):
        return legal(q) and abs((q[0]-7.83)/17.28-round((q[0]-7.83)/17.28))<1e-7 and abs((q[1]-1.08)/2.16-round((q[1]-1.08)/2.16))<1e-7
    site.native_home_legal=home
    def nearest(p,axis=None):
        q=original(p,axis);ix=round((q[0]-7.83)/17.28);iy=round((q[1]-1.08)/2.16);pool=[]
        for dx in range(-2,3):
            for dy in range(-3,4):
                z=(round(7.83+17.28*(ix+dx),6),round(1.08+2.16*(iy+dy),6))
                if home(z):pool.append(z)
        if not pool:raise ValueError('no native PG-gap clock home near '+str(p))
        return min(pool,key=lambda z:(D._man(p,z)+(2*abs(z[1]-p[1])if axis=='x'else 2*abs(z[0]-p[0])if axis=='y'else 0),z))
    site.nearest=nearest
    # Use the existing home allocator and physical DME body checks with the
    # new home legality predicate. No generic tools are changed on disk.
    src=inspect.getsource(D.physical_pack).replace('site.legal(q) and not any','site.native_home_legal(q) and not any')
    exec(src,D.__dict__)
    src=inspect.getsource(D.dme_region_tree)
    old='q = (t[2], t[3]) if site.legal((t[2], t[3])) else site.nearest((t[2], t[3]))'
    assert old in src
    src=src.replace(old,'q = site.nearest((t[2], t[3]))')
    exec(src,D.__dict__)
    return dict(M9_gap_phase_um=[6.48,10.8],M9_native_home_x_phase_um=7.83,M9_pitch_um=17.28,M8_gap_phase_um=[.24,1.92],native_y_phase_um=1.08,M8_pitch_um=2.16)
