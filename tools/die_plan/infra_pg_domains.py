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
set ot_iso_block [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set outer {};set inner {}
foreach r $ot_phy_boxes {
 lassign $r a b c d
 lappend outer [list [expr {round(($a-$ot_pg_gap)*$dbu)}] [expr {round(($b-$ot_pg_gap)*$dbu)}] [expr {round(($c+$ot_pg_gap)*$dbu)}] [expr {round(($d+$ot_pg_gap)*$dbu)}]]
 lappend inner [list [expr {round(($a+$ot_pg_gap)*$dbu)}] [expr {round(($b+$ot_pg_gap)*$dbu)}] [expr {round(($c-$ot_pg_gap)*$dbu)}] [expr {round(($d-$ot_pg_gap)*$dbu)}]]
}
set clipped 0
foreach netname {VDD VDDPHY} {
 set net [$ot_iso_block findNet $netname]
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

def stitch_tcl(core_grid):
    maxgap=max(q['pitch_um']for q in core_grid)*2
    return f'set ot_pg_maxgap {maxgap:g}\n'+r'''
set ot_mesh_block [ord::get_db_block]
set ot_mesh_count 0
foreach ot_mesh_name {VDD VSS} {
 set ot_mesh_net [$ot_mesh_block findNet $ot_mesh_name];set ot_mesh_groups {}
 foreach sw [$ot_mesh_net getSWires] {foreach s [$sw getWires] {
  if {[$s isVia]} continue
  set layer [[$s getTechLayer] getName]
  if {$layer eq "M9"} {set key [list $layer [expr {([$s xMin]+[$s xMax])/2.0}]];set range [list [$s yMin] [$s yMax] [expr {[$s xMax]-[$s xMin]}]]} elseif {$layer eq "M8"} {set key [list $layer [expr {([$s yMin]+[$s yMax])/2.0}]];set range [list [$s xMin] [$s xMax] [expr {[$s yMax]-[$s yMin]}]]} else {continue}
  dict lappend ot_mesh_groups $key $range
 }}
 set ot_mesh_sw [odb::dbSWire_create $ot_mesh_net ROUTED];set ot_net_stitches 0
 foreach key [dict keys $ot_mesh_groups] {
  lassign $key layer center;set end -1e30;set prev_width 0
  foreach r [lsort -real -index 0 [dict get $ot_mesh_groups $key]] {
   lassign $r lo hi width
   if {$lo>$end && $lo-$end <= $ot_pg_maxgap*$dbu} {
    set half [expr {min($width,$prev_width)/2.0}]
    set aa [expr {round($center-$half)}];set cc [expr {round($center+$half)}]
    if {$layer eq "M9"} {set rect [list $aa $end $cc $lo]} else {set rect [list $end $aa $lo $cc]}
    set blocked 0
    if {$ot_mesh_name eq "VDD"} {foreach q $outer {if {[llength [ot_intersect $rect $q]]} {set blocked 1;break}}}
    if {!$blocked} {odb::dbSBox_create $ot_mesh_sw [[ord::get_db_tech] findLayer $layer] {*}$rect STRIPE;incr ot_net_stitches}
   }
   if {$hi>$end} {set prev_width $width;set end $hi}
  }
 }
 puts "OT_PG_SEAM_STITCHES $ot_mesh_name $ot_net_stitches"
 incr ot_mesh_count $ot_net_stitches
}
puts "OT_PG_CORE_SEAM_STITCHES $ot_mesh_count"
'''

def make(P, plan_dir, pg, window, out, pitch, phy_bumps=None, phy_grid_override=None, phy_m7_pitch=None, power=None, phy_m6_pitch=None, phy_m5_pitch=None):
    """phy_m7_pitch: LOCAL PHY-footprint reinforcement -- the PHY load blocks expose VDDPHY/VSS M7 PG straps at this
    pair pitch (default None = the partition 8.64-um M7 pin pitch). power: explicit worst-case power dict for load_model.
    phy_m6_pitch: also lay VDDPHY/VSS 0.288-um M6 straps (horizontal) at this pair pitch inside the PHY footprint, contacted
    to the M7 straps (V6) -- PHY-owned layers under the PHY outline only."""
    if phy_m6_pitch is not None and phy_m6_pitch < .768-1e-9:raise ValueError("PHY M6 strap pair pitch < 0.768 um violates M6 wide-metal spacing")
    if phy_m7_pitch is not None and (phy_m7_pitch < .768-1e-9):raise ValueError("PHY M7 strap pair pitch < 0.768 um violates M7 0.072-um wide-metal spacing at 0.288-um straps")
    core_grid={g['layer']:g for g in pg['grid']}
    if phy_grid_override is not None:
        supplied={g['layer']:g for g in phy_grid_override}
        if set(supplied)!={'M8','M9'}:raise ValueError('explicit PHY grid requires M8 and M9')
        for layer,g in supplied.items():
            c=core_grid[layer]
            if abs(g['pitch_um']-c['pitch_um'])>1e-6 or abs(g['offset_um']-c['offset_um'])>1e-6:raise ValueError('explicit PHY grid must align shared ground with core grid')
            if g['width_um']<=0 or g['pitch_um']/2-g['width_um']<I.spacing(g['width_um'])-1e-8:raise ValueError('explicit PHY grid violates width/spacing rule')
        phy_grid=list(phy_grid_override);division=1
    else:
        division=round(core_grid['M8']['pitch_um']/pitch)
        if division < 1 or division%2 != 1 or abs(core_grid['M8']['pitch_um']/division-pitch)>1e-6:
            raise ValueError('PHY grid must use an odd core-pitch subdivision so shared ground rails land')
        phy_grid=[]
        for layer in ['M8','M9']:
            pp=core_grid[layer]['pitch_um']/division;ww=min(I.STRIPE_W,pp/2-.048)
            if ww < .04 or pp/2-ww < I.spacing(ww)-1e-8:raise ValueError('PHY pitch violates width/spacing rule')
            phy_grid.append(I.grid_entry(layer,pp,ww))
    x0,y0,x1,y1=window['window_um']; W,H=x1-x0,y1-y0
    model=I.load_model(P,plan_dir,power=power,phy_w_per_macro=pg['phy_w_per_macro'],core_w_mm2=None if power else pg['core_w_mm2'])
    phy=[]
    for r in model['regions']:
        if r['kind']!='phy':continue
        q=r['rect_um'];a=[max(q[0],x0)-x0,max(q[1],y0)-y0,min(q[2],x1)-x0,min(q[3],y1)-y0]
        if a[0]<a[2] and a[1]<a[3]:phy.append(dict(name=r['name'],rect_um=a,nets=['VDDPHY','VSS'],grid=phy_grid))
    if not phy:raise ValueError('window contains no PHY')
    die=dict(outline_um=[W,H],pg=dict(grid=pg['grid'],domains=phy))
    blocks=[];masters={};loads=[];region_instances={}
    for regnum,reg in enumerate(G.regions(die)):
        a,b,c,d=reg['rect_um'];nx=max(1,round((c-a)/86.4));ny=max(1,round((d-b)/86.4));bw,bh=(c-a)/nx,(d-b)/ny
        step=phy_m7_pitch if (phy_m7_pitch and reg['nets'][0]!='VDD') else 8.64
        master=masters.setdefault((round(bw,4),round(bh,4),step),f'irblk{len(masters)}')
        for ix in range(nx):
            for iy in range(ny):
                xx,yy=a+ix*bw,b+iy*bh;rect=[xx+x0,yy+y0,xx+bw+x0,yy+bh+y0]
                pw=sum(dens*I._ov(rect,rr)for rr,dens in model['loads'])*1e-6
                name=f'u_b{len(blocks)}';blocks.append((name,master,xx,yy,pw,reg['nets'][0]));region_instances.setdefault(regnum,[]).append(name)
                for net,j in [(reg['nets'][0],0),('VSS',1)]:
                    pins=[];q=4.128+j*(.288+.096)
                    while q+.144<bw:
                        pins.append([xx+q-.144,yy+(.144 if j==0 else 0),xx+q+.144,yy+bh-(.144 if j==0 else 0)]);q+=step
                    loads.append(dict(inst=name,net=net,pin='VDD'if j==0 else'VSS',rects=pins))
    out=Path(out);(out/'psm').mkdir(parents=True,exist_ok=True)
    lef=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;']
    for (bw,bh,step),master in masters.items():
        lef += [f'MACRO {master}',' CLASS BLOCK ;',' ORIGIN 0 0 ;',f' SIZE {bw:.4f} BY {bh:.4f} ;']
        for net,j in [('VDD',0),('VSS',1)]:
            lef += [f' PIN {net}','  DIRECTION INOUT ;',f'  USE {"POWER"if net=="VDD"else"GROUND"} ;','  PORT','   LAYER M7 ;']
            q=4.128+j*(.288+.096)
            while q+.144<bw:
                lef += [f'   RECT {q-.144:.4f} {(.144 if j==0 else 0):.4f} {q+.144:.4f} {bh-(.144 if j==0 else 0):.4f} ;'];q+=step
            lef += ['  END',f' END {net}']
        lef += [f'END {master}']
    lef += ['END LIBRARY'];(out/'psm/irblk.lef').write_text('\n'.join(lef)+'\n')
    (out/'psm/psm.v').write_text('module irwin ();\n'+''.join(f'{m} {n} ();\n'for n,m,*_ in blocks)+'endmodule\n')
    pdn=G.pdn_tcl(die,loads).replace("add_pdn_stripe -grid ","add_pdn_stripe -extend_to_boundary -grid ")
    for k,insts in region_instances.items():
        pdn+=f'define_pdn_grid -name pins_{k} -voltage_domains {{ot_pg_{k}}} -macro -instances {{{" ".join("^"+n+"$"for n in insts)}}} -orient {{R0 R180 MX MY}} -halo {{0 0 0 0}}\n'
        pdn+=f'add_pdn_connect -grid pins_{k} -layers {{M7 M8}}\n'
        if phy_m6_pitch and G.regions(die)[k]['nets'][0]!='VDD':
            ry0=G.regions(die)[k]['rect_um'][1]
            pdn+=f'add_pdn_stripe -grid ot_pg_{k} -layer M6 -width 0.288 -pitch {phy_m6_pitch:g} -offset {(0.144-ry0)%phy_m6_pitch+0.0:g} -spacing {phy_m6_pitch/2-0.288:g}\n'
            pdn+=f'add_pdn_connect -grid pins_{k} -layers {{M6 M7}}\n'
            if phy_m5_pitch:   # 0.312-um M5 straps (vertical), V5 to the M6 straps; spacing 0.072
                rx0=G.regions(die)[k]['rect_um'][0]
                pdn+=f'add_pdn_stripe -grid ot_pg_{k} -layer M5 -width 0.312 -pitch {phy_m5_pitch:g} -offset {(0.156-rx0)%phy_m5_pitch+0.0:g} -spacing {phy_m5_pitch/2-0.312:g}\n'
                pdn+=f'add_pdn_connect -grid ot_pg_{k} -layers {{M5 M6}}\n'
    (out/'psm/pdn.tcl').write_text(pdn)
    (out/'psm/isolate.tcl').write_text(isolation_tcl(phy))
    (out/'psm/stitch.tcl').write_text(stitch_tcl(pg['grid']))
    io=D.io_windows(P,plan_dir)
    all_bumps=I.pg_bumps(P,io,pitch=pg['bump_pitch_um'])
    if phy_bumps is not None:
        if len(phy)!=1:raise ValueError('explicit source-map prototype requires one complete PHY window')
        seen=set()
        for n,x,y in phy_bumps:
            if n not in {'VDD','VSS'} or not all(math.isfinite(v)for v in (x,y)):raise ValueError('invalid PHY source')
            if not any(q['rect_um'][0]<x-x0<q['rect_um'][2] and q['rect_um'][1]<y-y0<q['rect_um'][3]for q in phy):raise ValueError('PHY source outside its window')
            key=round(x,6),round(y,6)
            if key in seen:raise ValueError('duplicate PHY source site')
            seen.add(key)
        all_bumps=list(D.bump_grid(P,io,pitch=pg['bump_pitch_um']))+list(phy_bumps)
    bumps=[('VDDPHY'if n=='VDD'and any(q['rect_um'][0]<=x-x0<=q['rect_um'][2]and q['rect_um'][1]<=y-y0<=q['rect_um'][3]for q in phy)else n,round(x-x0,3),round(y-y0,3))for n,x,y in all_bumps if x0<x<x1 and y0<y<y1]
    t=D.bumps_tcl(P,bumps).replace('foreach net_name {VDD VSS}','foreach net_name {VDD VSS VDDPHY}')
    # Legacy helper labels every secondary supply GROUND. Preserve true supply type.
    import re
    t=re.sub(r'(dbBTerm_create \[\$block findNet VDDPHY\].*?\$bt setSigType )GROUND',r'\1POWER',t)
    t='set block [ord::get_db_block]\nforeach name {VDD VDDPHY VSS} {set bt [$block findBTerm $name];if {$bt ne "NULL"} {odb::dbBTerm_destroy $bt}}\n'+t
    (out/'psm/bumps.tcl').write_text(t)
    t=['set t0 [clock seconds]',f'read_lef {D.TECH_LEF}',f'read_lef {D.SC_LEF}','read_lef /work/psm/irblk.lef',f'foreach f [glob {D.PLAT}/lib/NLDM/*RVT_TT_nldm*.lib*] {{read_liberty $f}}','read_verilog /work/psm/psm.v','link_design irwin',f'initialize_floorplan -die_area {{0 0 {W:g} {H:g}}} -core_area {{0 0 {W:g} {H:g}}} -site asap7sc7p5t','source /work/psm/tracks.tcl','set dbu [[ord::get_db_tech] getDbUnitsPerMicron]','proc pl {n x y} {global dbu;set i [[ord::get_db_block] findInst $n];$i setOrient R0;$i setLocation [expr {round($x*$dbu)}] [expr {round($y*$dbu)}];$i setPlacementStatus FIRM}']
    t += [f'pl {n} {x:.4f} {y:.4f}'for n,m,x,y,pw,net in blocks]
    t += ['source /work/psm/pdn.tcl','pdngen','source /work/psm/isolate.tcl','source /work/psm/stitch.tcl','source /work/psm/bumps.tcl',f'source {D.PLAT}/setRC.tcl','write_db /work/psm/pdn_bumps.odb']
    t += [f'set_pdnsim_inst_power -inst {n} -power {pw:.8f}'for n,m,x,y,pw,net in blocks if pw>0]
    t += ['foreach n {VDD VDDPHY VSS} {check_power_grid -net $n;puts "OT_PG_CHECK_OK $n"}','foreach n {VDD VDDPHY} {set_pdnsim_net_voltage -net $n -voltage 0.7;puts "OT_ANALYZE_NET $n";analyze_power_grid -net $n -error_file /work/psm/psm_${n}.rpt -voltage_file /work/psm/ir_${n}.csv;puts "OT_PSM_OK $n"}','puts "OT_T psm [expr {[clock seconds]-$t0}]"','puts OT_DONE']
    (out/'psm/psm.tcl').write_text('\n'.join(t)+'\n');(out/'psm/tracks.tcl').write_text(D.coarse_tracks(P,.72))
    (out/'run_psm.sh').write_text(D.run_sh('psm',32,8,'/usr/bin/time -v openroad -no_init -threads 8 -exit /work/psm/psm.tcl > /work/psm/psm.log 2>&1'))
    os.chmod(out/'run_psm.sh',0o755)
    meta=dict(window=window['window'],window_um=window['window_um'],die=die,bumps=bumps,load_blocks=len(blocks),power_w=round(sum(b[4]for b in blocks),6),phy_grid=phy_grid,subdivision=division,phy_m7_pitch_um=phy_m7_pitch,phy_m6_pitch_um=phy_m6_pitch,phy_m5_pitch_um=phy_m5_pitch,contacts='native per-domain macro PG grid',explicit_phy_sources=phy_bumps is not None,explicit_phy_grid=phy_grid_override is not None,scope=('separate PHY-local grid; explicit candidate PHY sources; core sources and load densities unchanged; open window boundaries; no plan adoption' if phy_bumps is not None else 'separate PHY-local grid; original bump positions and load densities unchanged; open window boundaries; no plan adoption'))
    (out/'domains.json').write_text(json.dumps(meta,indent=1)+'\n');return meta

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('plan');a.add_argument('--pg',required=True);a.add_argument('--window',required=True);a.add_argument('--out',required=True);a.add_argument('--phy-pitch',type=float,required=True);a.add_argument('--phy-bumps',help='explicit global PHY PG source-map JSON from ucIe_bump_field');args=a.parse_args()
    p=Path(args.plan);P=S.Plan(S.load(p),p);m=make(P,p.parent,json.loads(Path(args.pg).read_text()),json.loads(Path(args.window).read_text()),args.out,args.phy_pitch,json.loads(Path(args.phy_bumps).read_text())['bumps'] if args.phy_bumps else None);print(json.dumps({k:v for k,v in m.items()if k not in {'bumps','die'}},indent=1))
if __name__=='__main__':main()
