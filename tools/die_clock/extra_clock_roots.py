"""Find GEN5 roots from actual scalar connections and declared pin directions."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from die_port_bind import parse_die, expr_bits

SOURCES = {('qfd_ckdiv6', 'blk_o'), ('ot_qfd_ucie_x64_phy', 'lclk')}


def roots(die, dirs):
    nets, _, _, instances = parse_die(die)
    actual, selected = {}, []
    for master, inst, _, ports in instances:
        for port, expression in ports.items():
            bits = expr_bits(expression, nets)
            if dirs.get(master, {}).get(port) == 'output' and bits:
                for bit in bits:
                    actual.setdefault(bit, []).append(f'{inst}/{port}')
            if (master, port) not in SOURCES:
                continue
            if dirs.get(master, {}).get(port) != 'output' or not bits or len(bits) != 1 or \
                    bits[0][0] not in nets or nets[bits[0][0]][0] != 1 or bits[0][1] != 0:
                raise ValueError(f'{inst}/{port}: GEN5 root must be an actual scalar declared output')
            selected.append((f'{inst}/{port}', bits[0]))
    for pin, bit in selected:
        if actual.get(bit) != [pin]:
            raise ValueError(f'{pin}: unknown or multiple source clock root: {actual.get(bit)}')
    return [pin for pin, _ in selected]


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--die-v', type=Path, required=True)
    ap.add_argument('--port-dirs', type=Path, required=True)
    a = ap.parse_args()
    # A legacy die has no new roots and does not need the additional manifest.
    declared = json.loads(a.port_dirs.read_text()) if a.port_dirs.is_file() else {}
    print(','.join(roots(a.die_v, declared)))
