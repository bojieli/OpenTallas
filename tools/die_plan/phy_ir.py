#!/usr/bin/env python3
"""Measure a declared PHY supply domain with its own grid and dedicated PG bump rows.

This is a window PDNSim vehicle, not whole-die signoff. Density is an explicit
sweep assumption until the selected PHY's measured power is supplied.
"""
import argparse
import os
import json
import math
import hashlib
import csv
from pathlib import Path
import die_trial as D


def _window_kit(plan_path, out, rect, density=0.15, name="win", tile=86.4):
    """PDNSim on a WINDOW of the die (full-die PSM segfaults in IRSolver::solve at 119 GB on s81_head, 307 mm2):
    the die PG (die.pg.grid M8/M9 + partition M7 stripes, as the full kit), the die's own C4 bump lattice inside the
    window (minus die IO windows / channels), and one abstract load block covering the window with power =
    density x area (uniform).  With area bumps every 150 um the IR is local, so an interior window stands for the
    die interior and a window over a SerDes IO window (no power bumps there) gives the edge hotspot."""
    raw = D.S.load(plan_path)
    P = D.S.Plan(raw)
    g = P.die["grid_um"] if "grid_um" in P.die else 8.64
    x0, y0, x1, y1 = [round(v / g) * g for v in rect]
    w, h = x1 - x0, y1 - y0
    out = Path(out)
    (out / "psm").mkdir(parents=True, exist_ok=True)
    io = D.io_windows(P, Path(plan_path).parent)
    bumps = [(n, round(x - x0, 3), round(y - y0, 3)) for n, x, y in D.bump_grid(P, io) if x0 < x < x1 and y0 < y < y1]
    # load block LEF: M7 PG pins exactly as the partition kits (gen_phys.PDN M7 stripes), die-phase preserved
    # load = a grid of tile x tile blocks (PDNSim injects a block's current at its own pin nodes; one window-sized
    # block concentrates it and gives a false point-load hotspot)
    nx_t, ny_t = max(1, int(round(w / tile))), max(1, int(round(h / tile)))
    bw, bh = w / nx_t, h / ny_t
    w_full, h_full = w, h
    w, h = bw, bh
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', "MACRO irblk", "  CLASS BLOCK ;", "  ORIGIN 0 0 ;",
         f"  SIZE {w:.4f} BY {h:.4f} ;"]
    for net, j in (("VDD", 0), ("VSS", 1)):
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {'POWER' if net == 'VDD' else 'GROUND'} ;", "    PORT"]
        c = 4.128 + j * (0.288 + 0.096)
        while c + 0.144 < w:
            L += ["      LAYER M7 ;", f"        RECT {c - 0.144:.4f} 0 {c + 0.144:.4f} {h:.4f} ;"]
            c += 8.64
        L += ["    END", f"  END {net}"]
    L += ["  OBS", f"    LAYER M1 ;\n      RECT 0 0 {w:.4f} {h:.4f} ;", "  END", "END irblk", "END LIBRARY", ""]
    (out / "psm" / "irblk.lef").write_text("\n".join(L))
    blks = [(f"u_b{i}_{j}", i * bw, j * bh) for i in range(nx_t) for j in range(ny_t)]
    (out / "psm" / "psm.v").write_text("module irwin ();\n" + "".join(f"  irblk {n} ();\n" for n, _, _ in blks) + "endmodule\n")
    w, h = w_full, h_full
    (out / "psm" / "pdn.tcl").write_text(D.psm_pdn_tcl(P))
    (out / "psm" / "bumps.tcl").write_text(D.bumps_tcl(P, bumps))
    pw = density * w * h * 1e-6
    t = ["set t0 [clock seconds]", f"read_lef {D.TECH_LEF}", f"read_lef {D.SC_LEF}", "read_lef /work/psm/irblk.lef",
         f"foreach f [glob {D.PLAT}/lib/NLDM/*RVT_TT_nldm*.lib*] {{ read_liberty $f }}",
         "read_verilog /work/psm/psm.v", "link_design irwin",
         f"initialize_floorplan -die_area {{0 0 {w:g} {h:g}}} -core_area {{0 0 {w:g} {h:g}}} -site asap7sc7p5t",
         "source /work/psm/tracks.tcl",
         "set dbu [[ord::get_db_tech] getDbUnitsPerMicron]",
         "proc ot_pl {n x y} { global dbu; set i [[ord::get_db_block] findInst $n]; $i setOrient R0; "
         "$i setLocation [expr {round($x*$dbu)}] [expr {round($y*$dbu)}]; $i setPlacementStatus FIRM }"]
    t += [f"ot_pl {n} {x:.4f} {y:.4f}" for n, x, y in blks]
    t += [
         "source /work/psm/pdn.tcl", "pdngen", "puts \"OT_T pdngen [expr {[clock seconds]-$t0}]\"",
         "source /work/psm/bumps.tcl", "puts \"OT_T bumps [expr {[clock seconds]-$t0}]\"",
         f"source {D.PLAT}/setRC.tcl"]
    t += [f"set_pdnsim_inst_power -inst {n} -power {pw / len(blks):.8f}" for n, _, _ in blks]
    t += [
         "foreach n {VDD VSS} { if {[catch {check_power_grid -net $n} e]} { puts \"OT_PG_CHECK_FAIL $n $e\" } "
         "else { puts \"OT_PG_CHECK_OK $n\" } }",
         "if {[catch {analyze_power_grid -net VDD -error_file /work/psm/psm_VDD.rpt -voltage_file /work/psm/ir_VDD.csv} e]} "
         "{ puts \"OT_PSM_FAIL $e\" } else { puts OT_PSM_OK }",
         "puts \"OT_T psm [expr {[clock seconds]-$t0}]\"", "puts OT_DONE"]
    (out / "psm" / "tracks.tcl").write_text(D.coarse_tracks(P, 0.72))
    (out / "psm" / "psm.tcl").write_text("\n".join(t) + "\n")
    (out / "run_psm.sh").write_text(D.run_sh("psm", 64, 8, "/usr/bin/time -v openroad -no_init -threads 8 -exit "
                                                       "/work/psm/psm.tcl > /work/psm/psm.log 2>&1; echo EXIT \\$? >> /work/psm/psm.log"))
    os.chmod(out / "run_psm.sh", 0o755)
    meta = dict(plan=str(plan_path), die=P.name, name=name, window_um=[x0, y0, x1, y1], area_mm2=round(w * h * 1e-6, 3),
                density_w_mm2=density, power_w=round(pw, 4), load_blocks=len(blks), block_um=[round(bw, 3), round(bh, 3)], bumps=len(bumps), bumps_vdd=sum(1 for b in bumps if b[0] == "VDD"),
                io_in_window=[x["name"] for x in io if x["rect_um"][0] < x1 and x["rect_um"][2] > x0
                              and x["rect_um"][1] < y1 and x["rect_um"][3] > y0])
    (out / "irwin.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def make(plan, domain, out, density):
    if not math.isfinite(density) or density <= 0:
        raise ValueError('PHY density must be positive and finite')
    raw = D.S.load(plan)
    domains = raw['die']['pg'].get('domains', [])
    found = [d for d in domains if d['name'] == domain]
    if len(found) != 1:
        raise ValueError(f'Expected one declared PHY domain {domain!r}, found {len(found)}')
    pg = found[0]
    power, ground = pg['nets']
    if not pg.get('bumps'):
        raise ValueError('PHY domain has no explicit dedicated PG bump rectangle')
    x0, y0, x1, y1 = pg['rect_um']
    # Copy only immutable plan data into a small standalone supply-domain plan.
    # It uses exactly the declared domain dimensions, grid and PG bump rectangle.
    local = json.loads(json.dumps(raw))
    for key in ('partition_types','partitions','ports','lanes'):
        local[key] = {} if key == 'partition_types' else []
    local['die']['outline_um'] = [x1-x0, y1-y0]
    local['die']['grid_um'] = 0.001
    local['die']['channels'] = []
    local['die']['io'] = []
    local['die']['pg']['grid'] = pg['grid']
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    lp = out/'domain_plan.json'
    lp.write_text(json.dumps(local))
    m = _window_kit(lp, out, [0,0,x1-x0,y1-y0], density, domain)
    r = pg['bumps']['rect_um']
    pitch = pg['bumps']['pitch_um']
    nx, ny = int((r[2]-r[0])//pitch), int((r[3]-r[1])//pitch)
    if min(nx,ny)<1:
        raise ValueError('declared PHY bump rectangle has no complete row')
    sx=(r[0]+r[2]-(nx-1)*pitch)/2-x0
    sy=(r[1]+r[3]-(ny-1)*pitch)/2-y0
    bumps=[(power if (i+j)%2==0 else ground,round(sx+i*pitch,3),round(sy+j*pitch,3))
           for i in range(nx) for j in range(ny)]
    # Existing irwin emits VDD/VSS at the load pins and in PDNSim. Rename the
    # whole independent domain consistently, keeping its ground net as declared.
    for f in (out/'psm').iterdir():
        if f.suffix in {'.tcl','.lef','.v'}:
            s=f.read_text().replace('VSS','__GROUND__').replace('VDD','__POWER__')
            f.write_text(s.replace('__POWER__',power).replace('__GROUND__',ground))
    # bumps_tcl queries actual same-net metal after PDN generation. Its older
    # default net inventory is VDD/VSS, so rename before writing the domain kit.
    bt=D.bumps_tcl(D.S.Plan(local),[(('VDD' if n==power else 'VSS'),x,y) for n,x,y in bumps])
    bt=bt.replace('VSS','__GROUND__').replace('VDD','__POWER__').replace('__POWER__',power).replace('__GROUND__',ground)
    (out/'psm'/'bumps.tcl').write_text(bt)
    # This vehicle fails closed on a disconnected grid or failed solver.
    tf=out/'psm'/'psm.tcl'
    ts=tf.read_text().replace('puts \"OT_PG_CHECK_FAIL $n $e\"', 'error \"OT_PG_CHECK_FAIL $n $e\"').replace('puts \"OT_PSM_FAIL $e\"', 'error \"OT_PSM_FAIL $e\"')
    tf.write_text(ts)
    (out/'run_psm.sh').write_text(D.run_sh('psm',64,8,'/usr/bin/time -v openroad -no_init -threads 8 -exit /work/psm/psm.tcl > /work/psm/psm.log 2>&1'))
    (out/'run_psm.sh').chmod(0o755)
    m.update(plan=str(Path(plan).resolve()),plan_sha256=hashlib.sha256(Path(plan).read_bytes()).hexdigest(),domain=domain,domain_rect_um=pg['rect_um'],
             supply=power,ground=ground,bumps=len(bumps),bumps_vdd=sum(n==power for n,x,y in bumps),
             bump_pitch_um=pitch,bump_rect_um=r,grid=pg['grid'],
             assumptions=['Uniform PHY density sweep; actual PHY power not yet supplied',
                          'Standalone domain with shared VSS; coupled core-ground loading excluded',
                          'Declared PG bump rows are dedicated; package/PHY signal-map collision check pending'])
    (out/'irwin.json').write_text(json.dumps(m,indent=2)+'\n')
    (out/'bumps.json').write_text(json.dumps(bumps))
    render(out,m,bumps)
    return m


def render(out,m,bumps):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(12,4))
    x0,y0,x1,y1=m['domain_rect_um'];w=x1-x0;h=y1-y0
    for s in m['grid']:
        k=0
        while s['offset_um']+k*s['pitch_um']< (h if s['layer']=='M8' else w):
            v=s['offset_um']+k*s['pitch_um'];kw={'color':'#496070','alpha':.25,'linewidth':.5}
            (ax.axhline if s['layer']=='M8' else ax.axvline)(v,**kw);k+=1
    for n,c in [(m['supply'],'red'),(m['ground'],'blue')]:
        q=[(x,y) for net,x,y in bumps if net==n]
        ax.scatter([x for x,y in q],[y for x,y in q],s=7,c=c,label=f'{n} ({len(q)})')
    ax.set(xlim=(0,w),ylim=(0,h),aspect='equal',xlabel='um',ylabel='um',title=f"{m['die']} {m['domain']}: dedicated {m['bump_pitch_um']} um PG rows, {m['power_w']} W assumed")
    ax.legend(loc='upper right',fontsize=7);fig.tight_layout();fig.savefig(out/'domain_review.png',dpi=150);plt.close(fig)


def report(out):
    """Parse PDNSim completion, keeping modeled IR separate from die signoff."""
    out=Path(out)
    m=json.loads((out/'irwin.json').read_text())
    r=D.psm_report(out)
    r.update(domain=m['domain'],die=m['die'],density_w_mm2=m['density_w_mm2'],
             power_w=m['power_w'],supply=m['supply'],bumps=m['bumps'],
             assumptions=m['assumptions'],scope='standalone declared PHY domain')
    pg=dict((net,status) for status,net in r.get('pg_check',[]))
    r['verdict']='PASS' if r.get('status')=='OK' and all(pg.get(n)=='OK' for n in [m['supply'],m['ground']]) and not r.get('errors') else 'INCOMPLETE'
    if r.get('status')=='FAIL' or r.get('errors') or any(v=='FAIL' for v in pg.values()):
        r['verdict']='FAIL'
    vf=out/'psm'/f"ir_{m['supply']}.csv"
    if r['verdict']=='PASS' and vf.is_file():
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        rows=list(csv.DictReader(vf.open()))
        x=[float(q['X location']) for q in rows];y=[float(q['Y location']) for q in rows]
        drop=[(0.7-float(q['Voltage']))*1000 for q in rows]
        fig,ax=plt.subplots(figsize=(10,4))
        im=ax.scatter(x,y,c=drop,s=25,cmap='magma_r',vmin=0)
        ax.set(aspect='equal',xlabel='um',ylabel='um',title=f"{m['die']} {m['domain']}: modeled VDDPHY drop, max {max(drop):.3f}mV")
        fig.colorbar(im,ax=ax,label='IR drop (mV), nominal0.7V');fig.tight_layout()
        fig.savefig(out/'ir_drop.png',dpi=150);plt.close(fig)
        r['load_pin_max_drop_mv']=round(max(drop),6)
    (out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    return r


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan',nargs='?');ap.add_argument('--report',metavar='RUN_DIR');ap.add_argument('--domain');ap.add_argument('--out')
    ap.add_argument('--density',type=float,help='Explicit PHY power-density assumption W/mm2')
    a=ap.parse_args()
    if a.report:
        print(json.dumps(report(a.report),indent=2))
    else:
        if not a.plan or not a.domain or not a.out or a.density is None:
            ap.error('generation requires plan, --domain, --out and --density')
        print(json.dumps(make(a.plan,a.domain,a.out,a.density),indent=2))
