#!/usr/bin/env python3
"""SYS_C partition-local split PG: actual PHY VDD -> VDDPHY, core VDD exclusion.

Install after gen.py phys, before floorplan. Uses the same ASAP7 M5/M6/M7 phase
as the canonical partition grid. Select the explicit M6 generated PHY power profile
for legal access above M5 OBS; historical M4 profile intentionally remains available.
M7 PHY pins are exported for the die's dedicated supply/bump domain.
"""
import argparse
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/'tools/die_plan'))
import pg_regions

W,H=2160.0,1036.8
PHY=[691.2,17.28,1468.8,794.88]
INST='u_bound.u_ucie_rom'
GRID=[dict(layer='M5',width_um=.12,pitch_um=4.32,offset_um=2.064),
      dict(layer='M6',width_um=.288,pitch_um=4.32,offset_um=1.968),
      dict(layer='M7',width_um=.288,pitch_um=8.64,offset_um=4.128)]


def emit(rect=PHY,inst=INST,phy_pg_layer="M4"):
    die=dict(outline_um=[W,H],pg=dict(grid=GRID,domains=[dict(rect_um=rect,nets=['VDDPHY','VSS'],grid=GRID)]))
    pieces=pg_regions.regions(die)
    exact=re.escape(inst)
    t=['# SYS_C actual separate PHY supply; replaces generic partition pdn.tcl.',
       'set b [ord::get_db_block]', 'set dbu [[ord::get_db_tech] getDbUnitsPerMicron]',
       f'set phy [$b findInst {{{inst}}}]',
       'if {$phy eq "NULL"} {error "SYS_C PHY macro absent: cannot invent PHY supply"}']
    for n,typ in [('VDD','POWER'),('VDDPHY','POWER'),('VSS','GROUND')]:
        t += [f'set n [$b findNet {n}]',f'if {{$n eq "NULL"}} {{set n [odb::dbNet_create $b {n}]}}',f'$n setSigType {typ}; $n setSpecial']
    t += [f'add_global_connection -net VDD -inst_pattern {{^(?!{exact}$).*$}} -pin_pattern {{^VDD$}} -power',
          f'add_global_connection -net VDDPHY -inst_pattern {{^{exact}$}} -pin_pattern {{^VDD$}} -power',
          'add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground',
          'global_connect',
          'set_voltage_domain -name Core -power VDD -ground VSS -secondary_power {VDDPHY}']
    core_names=[];phy_name=None;sram_name=None
    for k,p in enumerate(pieces):
        name=f'sysc_pg_{k}';power,ground=p['nets'];r=p['rect_um'];isphy=power=='VDDPHY'
        if isphy:phy_name=name
        else:
            core_names.append(name)
            if r[0]<=625<=r[2] and r[1]<=50<=r[3]:sram_name=name
        t += [f'set region [odb::dbRegion_create $b {name}]',
              'odb::dbBox_create $region '+' '.join(f'[expr {{round({x:g}*$dbu)}}]' for x in r),
              f'set_voltage_domain -name {name} -region {name} -power {power} -ground {ground}',
              f'define_pdn_grid -name {name} -voltage_domains {{{name}}} -pins {{M7}} -starts_with GROUND']
        if not isphy:
            t += [f'add_pdn_connect -grid {name} -layers {{M2 M5}}']
        for s in GRID:
            if isphy and phy_pg_layer=="M6" and s['layer']=="M5":continue
            axis=1 if s['layer']=='M6' else 0
            phase=(s['offset_um']-r[axis])%s['pitch_um']
            spacing=.072 if s['layer']=='M5' else .096
            t.append(f"add_pdn_stripe -grid {name} -layer {s['layer']} -width {s['width_um']} -spacing {spacing} -pitch {s['pitch_um']} -offset {phase:.6f}")
        if not isphy or phy_pg_layer!="M6":t += [f'add_pdn_connect -grid {name} -layers {{M5 M6}}']
        t += [f'add_pdn_connect -grid {name} -layers {{M6 M7}}']
    if not phy_name or not sram_name:raise ValueError('SYS_C PHY/SRAM domains unresolved')
    domains=' '.join(core_names)
    t += [f'define_pdn_grid -name core_rails -voltage_domains {{{domains}}} -starts_with GROUND',
          'add_pdn_stripe -grid core_rails -layer M1 -width .018 -pitch .54 -offset 0 -followpins',
          'add_pdn_stripe -grid core_rails -layer M2 -width .018 -pitch .54 -offset 0 -followpins',
          'add_pdn_connect -grid core_rails -layers {M1 M2}',
          f'define_pdn_grid -macro -cells {{d2d_sram_1r1w_64x137_m1_r2c2_p288}} -name sysc_sram -voltage_domains {{{sram_name}}} -halo {{2 2}} -grid_over_boundary',
          'add_pdn_connect -grid sysc_sram -layers {M4 M5}',
          f'define_pdn_grid -macro -cells {{ot_qkvd_ucie_x64_phy}} -name sysc_phy_macro -voltage_domains {{{phy_name}}} -halo {{0 0}} -grid_over_boundary',
          f'add_pdn_connect -grid sysc_phy_macro -layers {{{phy_pg_layer} '+('M7' if phy_pg_layer=='M6' else 'M5')+'}']
    t += ['# Fail closed on wrong physical supply assignment before generating straps.',
          'foreach i [$b getInsts] {',
          '  foreach it [$i getITerms] {',
          '    set pn [[$it getMTerm] getName]',
          '    if {$pn ne "VDD"} {continue}',
          '    set expected [expr {$i eq $phy ? "VDDPHY" : "VDD"}]',
          '    set actual [$it getNet]',
          '    if {$actual eq "NULL" || [$actual getName] ne $expected} {error "SYS_C supply mismatch [$i getName]/$pn expected=$expected"}',
          '  }',
          '}']
    return '\n'.join(t)+'\n',pieces


def macro_place_tcl():
    """Exact selected SYS_C macro coordinates; resolve escaped flattened bus names."""
    macros=[(f'u_bound.u_d2d_kv.u_core.u_end.u_link.g_bank[{b}].u_store.g_p288.u_sram',596.16,17.28+86.4*b) for b in range(4)]
    macros.append((INST,PHY[0],PHY[1]))
    lines=['set b [ord::get_db_block]','set dbu [[ord::get_db_tech] getDbUnitsPerMicron]']
    for name,x,y in macros:
        lines += ['set matched {}', 'foreach candidate [$b getInsts] {', r'  regsub -all {\\} [$candidate getName] {} clean',
                  f'  if {{$clean eq {{{name}}}}} {{lappend matched $candidate}}', '}',
                  f'if {{[llength $matched] != 1}} {{error {{SYS_C macro missing/ambiguous: {name}}}}}',
                  'set i [lindex $matched 0]', f'$i setLocation [expr {{round({x:g}*$dbu)}}] [expr {{round({y:g}*$dbu)}}]',
                  '$i setOrient R0', '$i setPlacementStatus FIRM']
    lines.append('cut_rows -halo_width_x 2 -halo_width_y 2')
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser();p.add_argument('kit');p.add_argument('--phy-pg-layer',choices=['M4','M6'],default='M4');a=p.parse_args();k=Path(a.kit)
    text,pieces=emit(phy_pg_layer=a.phy_pg_layer);(k/'pdn.tcl').write_text(text)
    (k/'macro_place.tcl').write_text(macro_place_tcl())
    (k/'phy_pg_contract.json').write_text(json.dumps(dict(type='kv3_sys_c',phy_inst=INST,phy_rect_um=PHY,nets=['VDD','VDDPHY','VSS'],pieces=pieces,physical_gate='PHY ITerm VDD -> VDDPHY; coreVDD M5/M6/M7 disjoint PHYbox; VDDPHY M7 exported; connectivity required',phy_pg_layer=a.phy_pg_layer,phy_model_only=(a.phy_pg_layer=='M6'),ir='NOT RUN'),indent=1)+'\n')

if __name__=='__main__':main()
