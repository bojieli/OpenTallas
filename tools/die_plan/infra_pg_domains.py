#!/usr/bin/env python3
"""IR diagnostic: separate PHY supplies with a local M8/M9 grid and unchanged published bump sites.

Builds an open-edge window only. Reuses pg_regions for disjoint domain meshes,
phase and explicit same-net M7 contacts. It never changes a plan or a signed view.
"""
import argparse,json,math,os
from pathlib import Path
import infra_pg as I
import pg_regions as G
D,S=I.D,I.S

def isolation_tcl(domains,gap=.144):
    text=['set ot_phy_boxes {']
    text += [' {'+' '.join(f'{v:.6f}'for v in q['rect_um'])+'}'for q in domains]
    text += ['}',f'set ot_pg_gap {gap:g}']
    text += [r'''
proc ot_intersect {a b} {
 lassign $a x0 y0 x1 y1;lassign $b u0 v0 u1 v1
 set r [list [expr {max($x0,$u0)}] [expr {max($y0,$v0)}] [expr {min($x1,$u1)}] [expr {min($y1,$v1)}]]
 lassign $r a b c d;if {$a >= $c || $b >= $d} {return {}};return $r
}
proc ot_subtract {a b} {
 if {![llength [ot_intersect $a $b]]} {return [list $a]}
 lassign $a x0 y0 x1 y1;lassign $b u0 v0 u1 v1
 set out {};set aa [expr {max($x0,$u0)}];set cc [expr {min($x1,$u1)}]
 foreach r [list [list $x0 $y0 [expr {min($x1,$u0)}] $y1] [list [expr {max($x0,$u1)}] $y0 $x1 $y1] [list $aa $y0 $cc [expr {min($y1,$v0)}]] [list $aa [expr {max($y0,$v1)}] $cc $y1]] {
  lassign $r a b c d;if {$a < $c && $b < $d} {lappend out $r}
 };return $out
}
set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set outer {};set inner {}
foreach r $ot_phy_boxes {
 lassign $r a b c d
 lappend outer [list [expr {round(($a-$ot_pg_gap)*$dbu)}] [expr {round(($b-$ot_pg_gap)*$dbu)}] [expr {round(($c+$ot_pg_gap)*$dbu)}] [expr {round(($d+$ot_pg_gap)*$dbu)}]]
 lappend inner [list [expr {round(($a+$ot_pg_gap)*$dbu)}] [expr {round(($b+$ot_pg_gap)*$dbu)}] [expr {round(($c-$ot_pg_gap)*$dbu)}] [expr {round(($d-$ot_pg_gap)*$dbu)}]]
}
set clipped 0
foreach netname {VDD VDDPHY} {
 set net [$b findNet $netname]
 foreach sw [$net getSWires] {
  foreach s [$sw getWires] {
   set r [list [$s xMin] [$s yMin] [$s xMax] [$s yMax]];set rs {}
   if {$netname eq "VDDPHY"} {
    foreach q $inner {set rr [ot_intersect $r $q];if {[llength $rr]} {lappend rs $rr}}
   } else {
    set rs [list $r]
    foreach q $outer {set out {};foreach rr $rs {set out [concat $out [ot_subtract $rr $q]]};set rs $out}
   }
   if {[llength $rs] == 1 && [lindex $rs 0] eq $r} continue
   if {[$s isVia]} {
    # A via is retained only if its entire metal enclosure stays in its supply region.
    odb::dbSBox_destroy $s;incr clipped;continue
   }
   set layer [$s getTechLayer]
   foreach rr $rs {lassign $rr a b c d;if {$c-$a >= .04*$dbu && $d-$b >= .04*$dbu} {odb::dbSBox_create $sw $layer $a $b $c $d STRIPE}}
   odb::dbSBox_destroy $s;incr clipped
  }
 }
}
puts "OT_PG_POWER_ISOLATION_CLIPPED $clipped"
''']
    return '\n'.join(text)+'\n'

def make(P, plan_dir, pg, window, out, pitch):
    core_grid={g['layer']:g for g in pg['grid']}
    division=round(core_grid['M8']['pitch_um']/pitch)
    if division < 1 or division%2 != 1 or abs(core_grid['M8']['pitch_um']/division-pitch)>1e-6:
        raise ValueError('PHY grid must use an odd core-pitch subdivision so shared ground rails land')
    phy_grid=[]
    for layer in ['M8','M9']:
        pp=core_grid[layer]['pitch_um']/division;ww=min(I.STRIPE_W,pp/2-.048)
        if ww < .04 or pp/2-ww < I.spacing(ww)-1e-8:raise ValueError('PHY pitch violates width/spacing rule')
        phy_grid.append(I.grid_entry(layer,pp,ww))
    x0,y0,x1,y1=window['window_um']; W,H=x1-x0,y1-y0
    model=I.load_model(P,plan_dir,phy_w_per_macro=pg['phy_w_per_macro'],core_w_mm2=pg['core_w_mm2'])
    phy=[]
    for r in model['regions']:
        if r['kind']!='phy':continue
        q=r['rect_um'];a=[max(q[0],x0)-x0,max(q[1],y0)-y0,min(q[2],x1)-x0,min(q[3],y1)-y0]
        if a[0]<a[2] and a[1]<a[3]:phy.append(dict(name=r['name'],rect_um=a,nets=['VDDPHY','VSS'],grid=phy_grid))
    if not phy:raise ValueError('window contains no PHY')
    die=dict(outline_um=[W,H],pg=dict(grid=pg['grid'],domains=phy))
    blocks=[];masters={};loads=[]
    for reg in G.regions(die):
        a,b,c,d=reg['rect_um'];nx=max(1,round((c-a)/86.4));ny=max(1,round((d-b)/86.4));bw,bh=(c-a)/nx,(d-b)/ny
        master=masters.setdefault((round(bw,4),round(bh,4)),f'irblk{len(masters)}')
        for ix in range(nx):
            for iy in range(ny):
                xx,yy=a+ix*bw,b+iy*bh;rect=[xx+x0,yy+y0,xx+bw+x0,yy+bh+y0]
                pw=sum(dens*I._ov(rect,rr)for rr,dens in model['loads'])*1e-6
                name=f'u_b{len(blocks)}';blocks.append((name,master,xx,yy,pw,reg['nets'][0]))
                for net,j in [(reg['nets'][0],0),('VSS',1)]:
                    pins=[];q=4.128+j*(.288+.096)
                    while q+.144<bw:
                        pins.append([xx+q-.144,yy+(.144 if j==0 else 0),xx+q+.144,yy+bh-(.144 if j==0 else 0)]);q+=8.64
                    loads.append(dict(inst=name,net=net,pin='VDD'if j==0 else'VSS',rects=pins))
    out=Path(out);(out/'psm').mkdir(parents=True,exist_ok=True)
    lef=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;']
    for (bw,bh),master in masters.items():
        lef += [f'MACRO {master}',' CLASS BLOCK ;',' ORIGIN 0 0 ;',f' SIZE {bw:.4f} BY {bh:.4f} ;']
        for net,j in [('VDD',0),('VSS',1)]:
            lef += [f' PIN {net}','  DIRECTION INOUT ;',f'  USE {"POWER"if net=="VDD"else"GROUND"} ;','  PORT','   LAYER M7 ;']
            q=4.128+j*(.288+.096)
            while q+.144<bw:
                lef += [f'   RECT {q-.144:.4f} {(.144 if j==0 else 0):.4f} {q+.144:.4f} {bh-(.144 if j==0 else 0):.4f} ;'];q+=8.64
            lef += ['  END',f' END {net}']
        lef += [f'END {master}']
    lef += ['END LIBRARY'];(out/'psm/irblk.lef').write_text('\n'.join(lef)+'\n')
    (out/'psm/psm.v').write_text('module irwin ();\n'+''.join(f'{m} {n} ();\n'for n,m,*_ in blocks)+'endmodule\n')
    (out/'psm/pdn.tcl').write_text(G.pdn_tcl(die,loads))
    (out/'psm/isolate.tcl').write_text(isolation_tcl(phy))
    bumps=[('VDDPHY'if n=='VDD'and any(q['rect_um'][0]<=x-x0<=q['rect_um'][2]and q['rect_um'][1]<=y-y0<=q['rect_um'][3]for q in phy)else n,round(x-x0,3),round(y-y0,3))for n,x,y in I.pg_bumps(P,D.io_windows(P,plan_dir),pitch=pg['bump_pitch_um'])if x0<x<x1 and y0<y<y1]
    t=D.bumps_tcl(P,bumps).replace('foreach net_name {VDD VSS}','foreach net_name {VDD VSS VDDPHY}')
    # Legacy helper labels every secondary supply GROUND. Preserve true supply type.
    import re
    t=re.sub(r'(dbBTerm_create \[\$block findNet VDDPHY\].*?\$bt setSigType )GROUND',r'\1POWER',t)
    (out/'psm/bumps.tcl').write_text(t)
    t=['set t0 [clock seconds]',f'read_lef {D.TECH_LEF}',f'read_lef {D.SC_LEF}','read_lef /work/psm/irblk.lef',f'foreach f [glob {D.PLAT}/lib/NLDM/*RVT_TT_nldm*.lib*] {{read_liberty $f}}','read_verilog /work/psm/psm.v','link_design irwin',f'initialize_floorplan -die_area {{0 0 {W:g} {H:g}}} -core_area {{0 0 {W:g} {H:g}}} -site asap7sc7p5t','source /work/psm/tracks.tcl','set dbu [[ord::get_db_tech] getDbUnitsPerMicron]','proc pl {n x y} {global dbu;set i [[ord::get_db_block] findInst $n];$i setOrient R0;$i setLocation [expr {round($x*$dbu)}] [expr {round($y*$dbu)}];$i setPlacementStatus FIRM}']
    t += [f'pl {n} {x:.4f} {y:.4f}'for n,m,x,y,pw,net in blocks]
    t += ['source /work/psm/pdn.tcl','pdngen','source /work/psm/isolate.tcl','ot_pg_connect_pins','source /work/psm/bumps.tcl',f'source {D.PLAT}/setRC.tcl','write_db /work/psm/pdn_bumps.odb']
    t += [f'set_pdnsim_inst_power -inst {n} -power {pw:.8f}'for n,m,x,y,pw,net in blocks if pw>0]
    t += ['foreach n {VDD VDDPHY VSS} {check_power_grid -net $n;puts "OT_PG_CHECK_OK $n"}','foreach n {VDD VDDPHY} {set_pdnsim_net_voltage -net $n -voltage 0.7;puts "OT_ANALYZE_NET $n";analyze_power_grid -net $n -error_file /work/psm/psm_${n}.rpt -voltage_file /work/psm/ir_${n}.csv;puts "OT_PSM_OK $n"}','puts "OT_T psm [expr {[clock seconds]-$t0}]"','puts OT_DONE']
    (out/'psm/psm.tcl').write_text('\n'.join(t)+'\n');(out/'psm/tracks.tcl').write_text(D.coarse_tracks(P,.72))
    (out/'run_psm.sh').write_text(D.run_sh('psm',32,8,'/usr/bin/time -v openroad -no_init -threads 8 -exit /work/psm/psm.tcl > /work/psm/psm.log 2>&1'))
    os.chmod(out/'run_psm.sh',0o755)
    meta=dict(window=window['window'],window_um=window['window_um'],die=die,bumps=bumps,load_blocks=len(blocks),power_w=round(sum(b[4]for b in blocks),6),phy_grid=phy_grid,subdivision=division,scope='separate PHY-local grid; original bump positions and load densities unchanged; open window boundaries; no plan adoption')
    (out/'domains.json').write_text(json.dumps(meta,indent=1)+'\n');return meta

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('plan');a.add_argument('--pg',required=True);a.add_argument('--window',required=True);a.add_argument('--out',required=True);a.add_argument('--phy-pitch',type=float,required=True);args=a.parse_args()
    p=Path(args.plan);P=S.Plan(S.load(p),p);m=make(P,p.parent,json.loads(Path(args.pg).read_text()),json.loads(Path(args.window).read_text()),args.out,args.phy_pitch);print(json.dumps({k:v for k,v in m.items()if k not in {'bumps','die'}},indent=1))
if __name__=='__main__':main()
