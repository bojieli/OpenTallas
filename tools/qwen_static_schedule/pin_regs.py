"""Per-port pin-register latency of hardened tiles, read from each kit (owner rule 19:50 PT 2026-10-15).

A recipe-3 kit carries physical/ref_tile/<kit>/pin_regs.json: one register on every data input and every output at the
pin, +latency_cycles.input / .output edges per port, ports matching "exclude" (a regexp, with a recorded reason) and the
clock / reset ports pass straight through.  The compiler never hard-codes these edges: seam latencies are composed here
from the producer's output registers, the die-assigned relay edges and the consumer's input registers.  A kit built
before recipe 3 (kit.env RECIPE < 3) has no pin registers by construction; any other kit without pin_regs.json is an
error, never a silent zero.
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


def port_edges(kit, port, direction, root=ROOT):
    """pin-register edges added on one port of a kit (direction 'input' / 'output')"""
    if direction not in ('input', 'output'):
        raise ScheduleError('direction must be input or output')
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
