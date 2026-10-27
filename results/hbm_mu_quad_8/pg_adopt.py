"""HBM-MU-QUAD-8 (COORD 12:35 PG-GRID-AUDIT one-grid rule + 12:19 PG-ACTIVITY-KVHBM): die.pg.grid := G12 (HEAD-5) =
M8 0.48@4.32 / M9 12.96@34.56, offsets pitch/2, VDD/VSS (the grid PG-ACTIVITY-KVHBM 48f939873f passed: HBM 30.1 mV SM flat-0.5
upper bound incl below-M7, CHECKED PDNSim / UNCHECKED power basis).  Core C4 lattice = EDGE-FILL rule of pg_meas_psm.py
(--edge-margin 60, pitch 150, centred, VDD/VSS checkerboard) written as sidecar PLANDIR/pg_bumps.json (the plan schema has no
core-bump field; die_trial.bump_grid must read it -> tool owner).  PHY domains unchanged."""
import json,sys
from pathlib import Path
d=Path(sys.argv[1]); p=json.loads((d/"die_plan.json").read_text())
old=p["die"]["pg"]["grid"]
p["die"]["pg"]["grid"]=[dict(layer="M8",width_um=0.48,pitch_um=4.32,offset_um=2.16,nets=["VDD","VSS"]),
                        dict(layer="M9",width_um=12.96,pitch_um=34.56,offset_um=17.28,nets=["VDD","VSS"])]
W,H=p["die"]["outline_um"]; M,P=60.0,150.0
nx,ny=int((W-2*M)//P)+1,int((H-2*M)//P)+1
x0,y0=(W-(nx-1)*P)/2,(H-(ny-1)*P)/2
bumps=dict(schema="opentallas.core_bumps.v1",rule="EDGE-FILL (pg_meas_psm.py --edge-margin 60): n=floor((L-2M)/pitch)+1 per axis, centred",
           pitch_um=P,edge_margin_um=M,pad_um=70.0,size_um=60.0,cols=nx,rows=ny,first_col_um=round(x0,3),first_row_um=round(y0,3),
           nets="VDD/VSS checkerboard (i+j even = VDD)",skip="die.channels + io windows (die_trial.bump_grid); PHY domains keep their 45-um rows",
           source="COORD 2026-10-27 12:19 PG-ACTIVITY-KVHBM ruling; claude/pg-act-kvhbm-1027@48f939873f",grid_old=old)
(d/"pg_bumps.json").write_text(json.dumps(bumps,indent=1)+"\n")
(d/"die_plan.json").write_text(json.dumps(p,indent=1)+"\n")
print("grid",p["die"]["pg"]["grid"]); print({k:bumps[k] for k in ("cols","rows","first_col_um","first_row_um")})
