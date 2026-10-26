#!/usr/bin/env python3
"""Detailed-route a reviewed, physically connected clock/reset infrastructure ODB.

Run via ot-run inside an OpenROAD Python process. The input contains placed real
clock cells, actual PG, and connected mesh metal/vias/pin-access stacks. GRT
handles the remaining clock/reset nets; detailed_route must produce DRC0. This
never turns GRT guides, footprint reservations, or skew estimates into routes.

  openroad -python infra_clock_route.py --source clock_placed.odb --sdc clock.sdc \
    --nets all_infra.txt --preconnected mesh_and_pg.txt \
    --liberty '/platform/lib/*RVT_TT*.lib*' --out clock_physical \
    --clock-nets clock_nets.txt --access-regions reviewed_islands.json

Output infra.odb is suitable for infra_replay.py. Die timing, skew and IR gates
remain separate; this tool never qualifies a die freeze or tile sign-off.
"""
import argparse
import glob
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def tcl_path(path):
    text = str(Path(path).resolve())
    if any(c in text for c in '{}\n\r'):
        raise ValueError('unsupported Tcl path characters')
    return '{' + text + '}'


def names_file(path):
    names = [s.strip() for s in Path(path).read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')]
    if not names or len(set(names)) != len(names):
        raise ValueError('nonempty unique exact net names required: ' + str(path))
    return names


def route(source, sdc, names, preconnected, libraries, out, signal_layers='M1-M7', clock_layers='M8-M9', iterations=50,
          extra_clearance_um=0.0, clock_names=None, access_regions=None):
    import openroad
    from infra_connectivity import check_database,check_basic_clearance
    from infra_replay import physical_snapshot, reserve_actual_routes
    if iterations < 50 or extra_clearance_um < 0:
        raise ValueError('at least50 GRT iterations and nonnegative extra clearance required')
    if not set(preconnected) <= set(names):
        raise ValueError('preconnected nets must be included in all-infrastructure inventory')
    out = Path(out).resolve()
    if out.exists():
        raise ValueError('use a new output directory; preserve previous results: ' + str(out))
    out.mkdir(parents=True)
    record = dict(schema='opentallas.infra_clock_route.v1', source=str(source), out=str(out),
                  verdict='RUNNING', freeze_qualified=False, stages={}, iterations=iterations,
                  signal_layers=signal_layers,clock_layers=clock_layers)
    def save():
        (out/'clock_route.json').write_text(json.dumps(record, indent=2)+'\n')
    save()
    try:
        before = check_database(source, preconnected)
        (out/'preconnected.json').write_text(json.dumps(before, indent=2)+'\n')
        if before['verdict'] != 'CONNECTED':
            raise ValueError('pre-routed mesh/PG/reset is not physically connected or has cross-net overlaps')
        meshes=[n for n in preconnected if n=='ck_mesh' or n.startswith('ck_mesh_r')]
        clearance=check_basic_clearance(source,preconnected,meshes)
        (out/'fixed_clearance.json').write_text(json.dumps(clearance,indent=2)+'\n')
        if clearance['verdict'] != 'PASS':
            raise ValueError('fixed pre-routed mesh/PG metal violates technology/NDR basic clearance')
        tech = openroad.Tech()
        if not libraries:
            raise ValueError('explicit actual liberty files required')
        for library in libraries:
            tech.readLiberty(str(library))
        design = openroad.Design(tech)
        design.readDb(str(source))
        def run_tcl(command):
            status = design.evalTclString('catch {'+command+'} ot_infra_result')
            if str(status) != '0':
                raise ValueError(design.evalTclString('set ot_infra_result'))
        block = design.getBlock()
        selected = set(names)
        missing = [n for n in names if not block.findNet(n)]
        if missing:
            raise ValueError('missing infrastructure nets: '+', '.join(missing))
        foreign = [n.getName() for n in block.getNets() if n.getName() not in selected and n.getTermCount() > 1]
        if foreign:
            raise ValueError('clock-only source contains unselected routable nets: '+', '.join(foreign))
        cells = {t.getInst().getName():t.getInst() for name in names for t in block.findNet(name).getITerms()}
        bad_pg = []
        for name, cell in cells.items():
            for terminal in cell.getITerms():
                kind = str(terminal.getMTerm().getSigType())
                if kind in ('POWER', 'GROUND'):
                    net = terminal.getNet()
                    if not net or str(net.getSigType()) != kind or net.getName() not in preconnected:
                        bad_pg.append(name+'.'+terminal.getMTerm().getName())
            cell.setDoNotTouch(True)
            cell.setPlacementStatus('LOCKED')
        if bad_pg:
            raise ValueError('clock/reset cell PG terminals missing/wrong/unrouted: '+', '.join(bad_pg))
        preserved = {name:physical_snapshot(block.findNet(name)) for name in preconnected}
        for name in preconnected:
            net = block.findNet(name)
            net.setWireType('FIXED')
            for wire in net.getSWires():
                wire.setWireType('FIXED')
            net.setDoNotTouch(True)
        # Snapshot after permitted route-status changes; cell placement is locked.
        preserved = {name:physical_snapshot(block.findNet(name)) for name in preconnected}
        record['reservations'] = reserve_actual_routes(block, preconnected, out/'infra_obs.tcl', extra_clearance_um)
        record['locked_cells'] = sorted(cells)
        record['stages']['preconnected'] = 'PASS'
        save()
        run_tcl('read_sdc '+tcl_path(sdc))
        bounds = []
        for span in (signal_layers, clock_layers):
            if not re.fullmatch(r'[A-Za-z0-9_]+-[A-Za-z0-9_]+', span):
                raise ValueError('invalid layer range '+span)
            for name in span.split('-'):
                layer = tech.getDB().getTech().findLayer(name)
                if not layer or layer.getRoutingLevel() <= 0:
                    raise ValueError('unknown routing layer '+name)
                bounds.append((layer.getRoutingLevel(),name))
        bottom, top = min(bounds)[1], max(bounds)[1]
        record['detailed_routing_layers'] = [bottom,top]
        run_tcl(f'set_routing_layers -signal {signal_layers} -clock {clock_layers}')
        run_tcl('set_global_routing_layer_adjustment * 0.0')
        run_tcl(f'global_route -verbose -congestion_iterations {iterations} -guide_file '+tcl_path(out/'clock.guide'))
        design.writeDb(str(out/'grt.odb'))
        record['stages']['grt'] = 'PASS'
        save()
        # The detailed router uses the signal-layer range even for clock guides.
        # Widen that *after* GRT to the union of requested infrastructure layers;
        # retain the clock/signal guides generated under the original split.
        # Current OpenROAD rejects the deprecated detailed_route layer flags.
        run_tcl(f'set_routing_layers -signal {bottom}-{top} -clock {clock_layers}')
        run_tcl('detailed_route -output_drc '+tcl_path(out/'drc.rpt')+
                ' -output_maze '+tcl_path(out/'maze.log')+' -verbose 1')
        design.writeDb(str(out/'routed.odb'))
        drc = out/'drc.rpt'
        if not drc.is_file():
            raise ValueError('detailed_route produced no DRC report')
        violations = len(re.findall(r'violation type:', drc.read_text(), re.I))
        if drc.read_text().strip() and violations == 0:
            raise ValueError('unrecognized nonempty DRC report; refusing DRC0 claim')
        record['drc_violations'] = violations
        if violations:
            raise ValueError(f'detailed_route has {violations} DRC violations')
        for name, expected in preserved.items():
            if physical_snapshot(block.findNet(name)) != expected:
                raise ValueError('detailed routing changed fixed infrastructure '+name)
        if clock_names is not None:
            from infra_clock_audit import audit_block
            if access_regions is None:
                raise ValueError('clock layer audit requires explicit reviewed access-region contract')
            audit = audit_block(block,clock_names,clock_layers,access_regions)
            (out/'clock_layer_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
            if audit['verdict'] != 'PASS':
                raise ValueError('decoded clock metal leaves spine layers/explicit endpoint islands')
            record['stages']['clock_layers'] = 'PASS'
        else:
            record['stages']['clock_layers'] = 'NOT RUN (physical mechanism diagnostic only)'
        for name in names:
            net = block.findNet(name)
            net.setWireType('FIXED')
            for wire in net.getSWires():
                wire.setWireType('FIXED')
            net.setDoNotTouch(True)
        design.writeDb(str(out/'infra.odb'))
        design.writeDef(str(out/'infra.def'))
        connected = check_database(out/'infra.odb', names)
        (out/'connected.json').write_text(json.dumps(connected, indent=2)+'\n')
        if connected['verdict'] != 'CONNECTED':
            raise ValueError('routed clock/reset/PG connectivity or cross-net overlap check fails')
        final_clearance=check_basic_clearance(out/'infra.odb',names,meshes)
        (out/'routed_clearance.json').write_text(json.dumps(final_clearance,indent=2)+'\n')
        if final_clearance['verdict'] != 'PASS':
            raise ValueError('routed clock/reset/PG metal violates basic fixed-metal clearance')
        record['stages']['basic_clearance'] = 'PASS'
        record['stages']['detailed_route'] = 'PASS'
        record['stages']['connectivity'] = 'PASS'
        record['verdict'] = 'CONNECTED_DRC0'
        record['note'] = 'Actual routed infrastructure only; timing, CPPR skew, slew, IR and die freeze remain unqualified'
        save()
        return record
    except Exception as error:
        record['verdict'] = 'FAIL'
        record['failure'] = str(error)
        save()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--sdc', required=True)
    parser.add_argument('--nets', required=True)
    parser.add_argument('--preconnected', required=True)
    parser.add_argument('--liberty', action='append', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--signal-layers', default='M1-M7')
    parser.add_argument('--clock-layers', default='M8-M9')
    parser.add_argument('--iterations', type=int, default=50)
    parser.add_argument('--extra-clearance-um', type=float, default=0.0)
    parser.add_argument('--clock-nets',help='Exact clock-net inventory for mandatory production layer audit')
    parser.add_argument('--access-regions',help='Reviewed endpoint islands/pins JSON; never derived from routed metal')
    args = parser.parse_args()
    libraries = []
    for pattern in args.liberty:
        files = sorted(glob.glob(pattern))
        if not files:
            parser.error('no liberty files match '+pattern)
        libraries.extend(files)
    if args.clock_layers != 'M1-M7' and not (args.clock_nets and args.access_regions):
        parser.error('production clock routing requires --clock-nets and --access-regions')
    result = route(args.source, args.sdc, names_file(args.nets), names_file(args.preconnected),
                   libraries, args.out, args.signal_layers, args.clock_layers, args.iterations, args.extra_clearance_um,
                   names_file(args.clock_nets) if args.clock_nets else None,
                   json.loads(Path(args.access_regions).read_text()) if args.access_regions else None)
    print('INFRA_CLOCK_ROUTE', result['verdict'], 'no freeze qualification')


if __name__ == '__main__':
    main()
