"""shared OCV width model for the DIE-QC-10 estimate: main clk_aocv (approved 0.21 %/mm table) on the unshared
branches + declared core latency (class B), droop not shared across regions, + in-region spread of both regions."""
import sys, json, math
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/die-qc9-1028/tools/die_plan')
import clk_aocv as CA
T=CA.load('/srv/opentallas-scratch2/claude/wt/die-qc9-1028/tools/die_plan/clk_aocv_table_g021.json')
LAT={'TT':250.0,'FF':202.5}
def spread(region, corner, c_spread=150.0):
    s = c_spread if region.startswith('c_') else (92.4 if region.endswith('su_c') else 41.0)
    return s * (1.0 if corner=='TT' else 0.85)
def ocv(ua, ub, dist_um, corner, same_droop=False):
    A=T['classes']['A'][corner]; B=T['classes']['B'][corner]; fc=A['cell_share']; lat=LAT[corner]
    nB=max(1,round(lat/B['mu_stage_ps']))
    def br(u):
        u=max(u,0.0); return dict(cell_ps=fc*u+B['cell_share']*lat, net_ps=(1-fc)*u+(1-B['cell_share'])*lat,
                                stages={'A':max(1,round(u/A['mu_stage_ps'])),'B':nB})
    a,b=br(ua),br(ub)
    return (CA.branch_pessimism(T,corner,a,b,dist_um,same_droop,'setup'),
            CA.branch_pessimism(T,corner,a,b,dist_um,same_droop,'hold'))
