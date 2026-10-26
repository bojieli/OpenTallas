#!/usr/bin/env python3
"""Build an admitted diagnostic of a die_clock tree with real global-route NDRs.

Inputs are an existing die_trial signal kit and die_clock artifact directory.
No abstract or sign-off verdict is changed. Run the emitted Tcl in ORFS with
/work=signal kit, /clock=clock artifacts, /out=output and CORNER=TT or FF.
"""
import argparse
import json
import math
import re
import shutil
from pathlib import Path


def legalize_cells(cells, plan):
    """Place fixed-width clock buffers on free native sites near their targets.

    The analytic tree intentionally puts all tap drivers at the leaf point.
    Physical probes must allocate separate sites and avoid core/PHY rectangles.
    """
    import schema as S
    import die_clock as DC
    P=S.Plan(S.load(plan))
    K=DC.KeepIndex(DC.keepouts(P),die=(P.W,P.H))
    occupied=set(); placed={}; maximum=0.0
    # BUFx24_ASAP7_75t_R is exactly 1.62 x 0.27 um on the native site.
    sx,sy,width,height=0.054,0.27,1.62,0.27
    ns=30
    for name,c in sorted(cells.items(),key=lambda z:(z[1]['kind'] in ('dummy','tapdrv'),z[0])):
        bx,by=round(c['x']/sx),round(c['y']/sy)
        found=None
        for ring in range(100):
            offsets=[(0,0)] if ring==0 else [(dx,dy) for dx in range(-ring,ring+1) for dy in range(-ring,ring+1) if max(abs(dx),abs(dy))==ring]
            # One horizontal step is a whole cell; one vertical step is one row.
            offsets.sort(key=lambda d: abs(d[0])*width+abs(d[1])*sy)
            for dx,dy in offsets:
                ix,iy=bx+dx*ns,by+dy;x,y=ix*sx,iy*sy
                if x<0 or y<0 or x+width>P.W or y+height>P.H:continue
                if any((iy,j) in occupied for j in range(ix,ix+ns)):continue
                if any(K.hit(a,b) for a,b in ((x,y),(x+width,y),(x,y+height),(x+width,y+height),(x+width/2,y+height/2))):continue
                found=ix,iy,x,y;break
            if found:break
        if found is None:raise ValueError(f'no legal clock island site for {name}')
        ix,iy,x,y=found
        occupied.update((iy,j) for j in range(ix,ix+ns))
        maximum=max(maximum,abs(x-c['x'])+abs(y-c['y']))
        placed[name]={**c,'x':round(x,6),'y':round(y,6),'orient':'MX' if iy%2 else 'R0'}
    return placed,dict(cells=len(placed),overlaps=0,keepout_hits=0,max_displacement_um=round(maximum,3),site_um=[sx,sy],master_um=[width,height])


def build(kit, clock, out, plan=None, width_corrected_rc=False):
    tree = json.loads((clock/'tree.json').read_text())
    cells = json.loads((clock/'place.json').read_text())
    legalization=None
    if plan is not None:cells,legalization=legalize_cells(cells,plan)
    nets = json.loads((clock/'nets.json').read_text())['nets']
    signal = (kit/'grt/route.v').read_text()
    cv = (clock/'ctree.v').read_text()
    sm = re.search(r'\s*module\s+\w+\s*\(([^)]*)\);', signal)
    cm = re.search(r'\s*module\s+\w+\s*\(([^)]*)\);', cv)
    if not sm or not cm:
        raise ValueError('expected flat artifact module headers')
    sp, cp = [x.strip() for x in sm[1].split(',')], [x.strip() for x in cm[1].split(',')]
    if set(sp)&set(cp):
        raise ValueError('signal/clock port collision')
    body = cv[cm.end():cv.rindex('endmodule')]
    # Prefix only identifiers private to the clock netlist; never cell masters or ports.
    private = set(cells)
    private.update(n['name'] for n in nets if n['name'] not in cp)
    body = re.sub(r'\b[A-Za-z_]\w*\b', lambda m: 'ck_'+m[0] if m[0] in private else m[0], body)
    out.mkdir(parents=True, exist_ok=True)
    (out/'combo.v').write_text('module die_combo ('+', '.join(sp+cp)+');\n'+
        signal[sm.end():signal.rindex('endmodule')]+body+'\nendmodule\n')
    t = (kit/'grt/grt.tcl').read_text().split('source /work/grt/obs.tcl')[0]
    t = t.replace('read_verilog /work/grt/route.v',
        'foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }\nread_verilog /out/combo.v')
    t = re.sub(r'link_design \S+', 'link_design die_combo', t)
    (out/'clock_place.json').write_text(json.dumps(cells))
    lines = ['source /work/grt/obs.tcl']
    root=tree['meta']['root_um']
    pins=[('root',root)]+[(x['port'],x['xy']) for x in tree['taps']]
    for name,(x,y) in pins:
        lines.append(f'place_pin -pin_name {name} -layer M9 -location {{{x} {y}}} -pin_size {{0.04 0.32}}')
    for name,c in cells.items():
        lines.append(f'place_inst -name ck_{name} -location {{{c["x"]} {c["y"]}}} -orient {c.get("orient","R0")} -status FIRM')
    lines += ['create_clock -name dck -period 833.000 [get_ports root]',
        'set_routing_layers -signal M4-M9 -clock M8-M9']
    for n in [4,5,6,7]: lines.append(f'set_global_routing_layer_adjustment M{n} 0.75')
    for n in [8,9]: lines.append(f'set_global_routing_layer_adjustment M{n} 0.4')
    lines += ['create_ndr -name ot_die4w -width {M8 0.16 M9 0.16} -spacing {M8 0.08 M9 0.08}',
              'create_ndr -name ot_die8w -width {M8 0.32 M9 0.32} -spacing {M8 0.08 M9 0.08}',
              'set blk [ord::get_db_block]', 'set n4 [$blk findNonDefaultRule ot_die4w]',
              'set n8 [$blk findNonDefaultRule ot_die8w]',
              'if {$n4 == "NULL" || $n8 == "NULL"} {error "missing block NDR"}']
    counts={4:0,8:0}
    for n in nets:
        drv = cells.get(n['drv'],{})
        lv = 0 if n['drv'].startswith('port:') else ((drv.get('level') or 0)+1 if drv.get('kind')=='node' else (drv.get('level') or 0) if drv.get('kind')=='rep' else 99)
        width=8 if lv<=6 else 4
        counts[width]+=1
        name=n['name'] if n['name'] in cp else 'ck_'+n['name']
        lines.append(f'[$blk findNet {name}] setNonDefaultRule $n{width}')
    lines += [f'puts "OT_NDR nets4={counts[4]} nets8={counts[8]}"',
        'global_route -congestion_iterations 5 -allow_congestion -verbose -congestion_report_file /out/congestion_$::env(CORNER).rpt',
        'write_guides /out/route_$::env(CORNER).guide',
        'write_global_route_segments /out/segments_$::env(CORNER).txt',
        'source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl',
        'delete_clock [get_clocks dck]', 'estimate_parasitics -global_routing',
        'create_clock -name vclk -period 833.000',
        'set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]',
        'set_input_delay 0 -clock vclk [get_ports root]', 'set_load 3.0 [get_ports t_*]',
        'set_output_delay 0 -clock vclk [get_ports t_*]',
        'set fh [open /out/arr_$::env(CORNER).txt w]',
        'foreach p [get_ports t_*] {puts $fh "T [get_full_name $p] [expr {833.000-[get_property $p slack_max_rise]}] [get_property $p slack_min_rise] [get_property $p slew_max_rise]"}',
        'foreach i [get_cells ck_n*] {set q [get_pins [get_full_name $i]/Y]; puts $fh "N [string range [get_full_name $i] 3 end] [get_property $q arrival_max_rise] [get_property $q arrival_min_rise]"}',
        'close $fh', 'report_check_types -max_slew -max_capacitance -violators',
        'write_db /out/combo_$::env(CORNER).odb', 'puts OT_DONE']
    if width_corrected_rc:
        for helper in ['mix_clock_spef.py','restore_clock_spef_caps.py']:
            shutil.copyfile(Path(__file__).with_name(helper),out/helper)
        rc=[
          'foreach scale {4 8} {',
          '  set rr 1.0; if {$scale == 4} {set cc 1.3} else {set cc 1.6}',
          '  set_layer_rc -layer M8 -resistance [expr {8.44765e-3*$rr}] -capacitance [expr {.103962*$cc}]',
          '  set_layer_rc -layer M9 -resistance [expr {8.89556e-3*$rr}] -capacitance [expr {.0928446*$cc}]',
          '  estimate_parasitics -global_routing -spef_file /out/routed${scale}w_$::env(CORNER).spef',
          '  if {![file exists /out/routed${scale}w_$::env(CORNER).spef] || [file size /out/routed${scale}w_$::env(CORNER).spef] == 0} {error "missing native estimated SPEF"}',
          '  exec python3 /out/restore_clock_spef_caps.py /out/routed${scale}w_$::env(CORNER).spef --out /out/fixed${scale}w_$::env(CORNER).spef --width $scale --clock /clock --prefix ck_',
          '}',
          'exec python3 /out/mix_clock_spef.py /out/fixed4w_$::env(CORNER).spef /out/fixed8w_$::env(CORNER).spef --clock /clock --prefix ck_ --out /out/routed_mixed_$::env(CORNER).spef',
          'read_spef /out/routed_mixed_$::env(CORNER).spef',
          'puts OT_MIXED_NDR_RC_LOADED']
        at=lines.index('estimate_parasitics -global_routing')
        lines[at:at+1]=rc
    (out/'combo.tcl').write_text(t+'\n'.join(lines)+'\n')
    (out/'probe.json').write_text(json.dumps(dict(clock_meta=tree['meta'],ndr_nets=counts,period_ps=833.0,diagnostic=True,legalization=legalization,width_corrected_rc=width_corrected_rc,rc_scope="Native per-net NDR R with profile C and restored terminal caps; GRT estimate, not RCX" if width_corrected_rc else "Native per-net NDR R with platform C; GRT estimate, not RCX"),indent=2))
    return dict(signal_ports=len(sp),clock_ports=len(cp),clock_cells=len(cells),ndr_nets=counts)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('kit',type=Path);p.add_argument('clock',type=Path);p.add_argument('out',type=Path);p.add_argument('--plan',type=Path);p.add_argument('--width-corrected-rc',action='store_true')
    a=p.parse_args();print(json.dumps(build(a.kit,a.clock,a.out,a.plan,a.width_corrected_rc)))
