"""Install an explicit existing pad-source density tree; default kits stay untouched."""
import argparse
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\[[0-9]+\])?\Z")
CLOCK = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def validate(spec):
    if set(spec) != {'port', 'clock', 'target', 'dmax_um', 'radius_um'}:
        raise ValueError('explicit existing port/clock and local load/reach budget required')
    if not PORT.fullmatch(spec['port']) or not CLOCK.fullmatch(spec['clock']):
        raise ValueError('unsafe native clock identity')
    if isinstance(spec['target'], bool) or not isinstance(spec['target'], int) or not 1 <= spec['target'] <= 1500:
        raise ValueError('invalid declared leaf load')
    if not 0 < spec['dmax_um'] <= spec['radius_um'] <= 250:
        raise ValueError('invalid declared leaf geometry')
    return spec


def install(kit, spec=None):
    if spec is None:
        return False
    spec = validate(spec)
    kit = Path(kit)
    cfg = (kit/'config.mk').read_text()
    marker = 'override export PRE_CTS_TCL = /work/secondary_clock_pre_cts.tcl'
    if marker in cfg:
        if json.loads((kit/'secondary_clock.json').read_text()) != spec:
            raise ValueError('secondary clock already installed with another reviewed spec')
        return True
    values = re.findall(r'^(?:override\s+)?export PRE_CTS_TCL\s*=\s*(\S+)\s*$', cfg, re.M)
    if not values or not re.fullmatch(r'/work/[A-Za-z0-9_.-]+\.tcl', values[-1]):
        raise ValueError('existing PRE_CTS kit hook required')
    original = values[-1]
    if not (kit/Path(original).name).is_file():
        raise ValueError('missing existing PRE_CTS hook')
    if 'core_tap_align.tcl' in cfg:
        raise ValueError('cross-domain tap alignment needs its own explicit source scope')
    donor = HERE.parents[1]/'physical/die_plan/hbm_arch_cores/core_density_taps.tcl'
    shutil.copyfile(donor, kit/'core_density_taps.tcl')
    shutil.copyfile(HERE/'secondary_clock_taps.tcl', kit/'secondary_clock_taps.tcl')
    fields = ' '.join('{'+str(x)+'}' for pair in spec.items() for x in pair)
    (kit/'secondary_clock_pre_cts.tcl').write_text(
        f'source {original}\nset ::ot_secondary_clock_spec [dict create {fields}]\n'
        'source /work/secondary_clock_taps.tcl\n')
    (kit/'secondary_clock.json').write_text(json.dumps(spec, indent=2)+'\n')
    (kit/'config.mk').write_text(cfg+'\n# Explicit native-source clock distribution, no SDC changes.\n'+marker+'\n')
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('kit')
    p.add_argument('--port', required=True)
    p.add_argument('--clock', required=True)
    p.add_argument('--target', type=int, default=1000)
    p.add_argument('--dmax-um', type=float, default=80)
    p.add_argument('--radius-um', type=float, default=200)
    a = p.parse_args()
    install(a.kit, dict(port=a.port, clock=a.clock, target=a.target,
                       dmax_um=a.dmax_um, radius_um=a.radius_um))


if __name__ == '__main__':
    main()
