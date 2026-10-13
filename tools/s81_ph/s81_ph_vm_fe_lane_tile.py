#!/usr/bin/env python3
"""el1011-ds-vm/fe (2026-10-11): pin plan of the hardened capture-lane tile dsfd_vm_clt (rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv).

Tile 80.64 x 230.04 um (one per f_cap lane slice: the FE's 16 lanes sit under their 79.9-um slices of the N face).
N face: f_c (832 b = 8 roots x 104) on M5 at 2 tracks, root order W -> E as on the FE N face.
S face: w_v / w_row / w_m / w_d / flt (547 b, registered outputs) + ck / rn / sok / gid on M5 at 2 tracks (v2: no W / E
pins, the tiles abut).  Routed on M2-M6 only (pdn_clt.tcl: PG pins on M6), so the parent routes M7 over the tiles.
Writes physical/s81_ph_views/ports/contract_vm28/dsfd_vm_clt/{ports.json, io_place.tcl, ports.svh}."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_ph_coll_tiles as T   # noqa: E402

T.CONTRACT = 'contract_vm28'
W, H = 80.64, 230.04   # 190.08 -> 230.04 (x1.21): route util 65.7% -> ~54%; width stays at the 80-um f_cap slice pitch


def main():
    p = T.Plan('dsfd_vm_clt', W, H)
    p.bus('f_c', 832, 'input', 'N', 'M5', 0.396)
    x = p.bus('w_v', 1, 'output', 'S', 'M5', 0.396)
    x = p.bus('w_row', 14, 'output', 'S', 'M5', x)
    x = p.bus('w_m', 16, 'output', 'S', 'M5', x)
    x = p.bus('w_d', 512, 'output', 'S', 'M5', x)
    x = p.bus('flt', 4, 'output', 'S', 'M5', x)
    # v2 (hierarchical FE): ck / rn / sok on the S face too (the W / E faces abut the neighbour tiles)
    x = p.bus('ck', 1, 'input', 'S', 'M5', x + 1.92)
    x = p.bus('rn', 1, 'input', 'S', 'M5', x)
    x = p.bus('sok', 1, 'input', 'S', 'M5', x)
    p.bus('gid', 4, 'input', 'S', 'M5', x)   # v3: lane-index strap (registered in the tile)
    p.emit('el1011-ds-vm/fe hardened capture-lane tile: N = 832-b f_cap slice, S = registered row-write port, S = row-write port + ck / rn / sok; top layer M6')


if __name__ == '__main__':
    main()
