"""Per-port pin-register latency of hardened tiles, read from each kit (owner rule 19:50 PT 2026-10-15).

A recipe-3 kit carries physical/ref_tile/<kit>/pin_regs.json: one register on every data input and every output at the
pin, +latency_cycles.input / .output edges per port, ports matching "exclude" (a regexp, with a recorded reason) and the
clock / reset ports pass straight through.  The compiler never hard-codes these edges: seam latencies are composed here
from the producer's output registers, the die-assigned relay edges and the consumer's input registers.  A kit built
before recipe 3 (kit.env RECIPE < 3) has no pin registers by construction; any other kit without pin_regs.json is an
error, never a silent zero.

EXACT STAGES (ROOT 2215): once the tile's route has run, the closure loop records the ELABORATED per-port table as
physical/ref_tile/<kit>/views/<top>/port_latency.json (tools/ref_tile/port_latency.py: schema
opentallas.ref_tile.port_latency.v1, bound to the route's full source SHA and the sha256 of the synthesis table and
wrapper).  port_edges() prefers that report: the per-port register_edges and direction come from the netlist the tile was
built from; a port the report does not list is an error.  pin_regs.json (generation-time intent) is the fallback only
until the first route of the kit.
"""
import json
import re
from pathlib import Path

from .calendar import ScheduleError

ROOT = Path(__file__).resolve().parents[2]


def _recipe(kit_dir):
    env = kit_dir / 'kit.env'
    if not env.is_file():
        raise ScheduleError(f'kit not found: {kit_dir}')
    m = re.search(r'^RECIPE=(\d+)', env.read_text(), re.M)
    return int(m[1]) if m else 1


def load(kit, root=ROOT):
    kit_dir = Path(root) / 'physical/ref_tile' / kit
    f = kit_dir / 'pin_regs.json'
    if not f.is_file():
        if _recipe(kit_dir) < 3:
            return dict(kit=kit, enable=False, input=0, output=0, exclude=None, clock_ports=[], reset=None,
                        basis=f'kit.env RECIPE {_recipe(kit_dir)} < 3: no pin registers')
        raise ScheduleError(f'recipe-3 kit {kit} lacks pin_regs.json')
    d = json.loads(f.read_text())
    if d.get('schema') != 'opentallas.ref_tile.pin_regs.v1':
        raise ScheduleError(f'{kit}: unknown pin_regs schema')
    lat = d.get('latency_cycles', {})
    if d.get('enable') and (type(lat.get('input')) is not int or type(lat.get('output')) is not int):
        raise ScheduleError(f'{kit}: pin_regs.json lacks integer latency_cycles')
    return dict(kit=kit, enable=bool(d.get('enable')), input=lat.get('input', 0) if d.get('enable') else 0,
                output=lat.get('output', 0) if d.get('enable') else 0, exclude=d.get('exclude') or None,
                clock_ports=d.get('clock_ports', []), reset=d.get('reset') or None, basis=str(f.relative_to(root)))


PORT_LATENCY_SCHEMA = 'opentallas.ref_tile.port_latency.v1'


def exact_report(kit, root=ROOT):
    """the recorded elaborated port-latency report of a kit (views/<top>/port_latency.json), or None before its first
    route.  The top comes from pin_regs.json; a report for another top or schema is an error."""
    kit_dir = Path(root) / 'physical/ref_tile' / kit
    f = kit_dir / 'pin_regs.json'
    if not f.is_file():
        return None
    top = json.loads(f.read_text()).get('top')
    rep_f = kit_dir / 'views' / str(top) / 'port_latency.json'
    if not top or not rep_f.is_file():
        return None
    rep = json.loads(rep_f.read_text())
    if rep.get('schema') != PORT_LATENCY_SCHEMA or rep.get('top') != top:
        raise ScheduleError(f'{kit}: {rep_f.name} schema/top mismatch (want {PORT_LATENCY_SCHEMA} for {top})')
    if not re.fullmatch(r'[0-9a-f]{40}', str(rep.get('source_commit', ''))) or not isinstance(rep.get('ports'), dict):
        raise ScheduleError(f'{kit}: {rep_f.name} lacks a full source SHA / ports')
    return dict(rep, basis=str(rep_f.relative_to(root)))


def port_edges(kit, port, direction, root=ROOT):
    """pin-register edges added on one port of a kit (direction 'input' / 'output')"""
    if direction not in ('input', 'output'):
        raise ScheduleError('direction must be input or output')
    rep = exact_report(kit, root)
    if rep is not None:
        rec = rep['ports'].get(port)
        if rec is None:
            raise ScheduleError(f'{kit}: elaborated port table {rep["basis"]} has no port {port}')
        if rec.get('dir') not in (direction, 'inout'):
            raise ScheduleError(f'{kit}: port {port} is {rec.get("dir")} in {rep["basis"]}, not {direction}')
        e = rec.get('register_edges')
        if type(e) is not int or e < 0:
            raise ScheduleError(f'{kit}: port {port} register_edges not a non-negative integer')
        return e
    p = load(kit, root)
    if not p['enable'] or port in p['clock_ports'] or (p['reset'] and re.fullmatch(p['reset'], port)):
        return 0
    if p['exclude'] and re.fullmatch(p['exclude'], port):
        return 0
    return p[direction]


def seam_edges(src_kit, src_port, dst_kit, dst_port, relay_edges, root=ROOT):
    """fixed edges of a die seam: producer output registers + die relay edges + consumer input registers"""
    if type(relay_edges) is not int or relay_edges < 0:
        raise ScheduleError('die-assigned relay edges must be a non-negative integer')
    return port_edges(src_kit, src_port, 'output', root) + relay_edges + port_edges(dst_kit, dst_port, 'input', root)
