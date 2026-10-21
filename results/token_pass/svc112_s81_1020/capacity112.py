"""Actual allocator on the exact split112 retained inventory; geometry model only.

Run alongside a pinned root/ compiler snapshot and inventory.json. This changes
only the in-memory compiler inventory, never a live die source or RTL binding.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D / 'root/tools/s81_dv/layer_prog'))
import xs_capacity as XC
import xs_topo as TP
import lower_xs as LX

ORIGINAL = XC._die
inventory = json.loads((D / 'inventory.json').read_text())
names = {'u_' + x['name']: x for x in inventory}
assert len(names) == 112
inventory_hash = hashlib.sha256((D / 'inventory.json').read_bytes()).hexdigest()

def actual112(src):
    die = ORIGINAL(src)
    for name, item in names.items():
        assert die.inst[name]['master'].removesuffix('_l4') == item['master'], (name, item)
    die.plan['blocks'] = [b for b in die.plan['blocks']
                          if b['kind'] != 'frame' or 'u_' + b['name'] in names]
    die.inst = {k: v for k, v in die.inst.items()
                if not k.startswith('u_f_') or k in names}
    TP.set_from_die(die)
    actual = {f for sl in die.slices() for f in die.frames_of(sl)}
    assert actual == set(names), (actual - names.keys(), names.keys() - actual)
    os.environ['OT_XS_FRAME_INVENTORY_SHA256'] = inventory_hash
    return die

XC._die = actual112
if __name__ == '__main__':
    sys.exit(XC.main())
