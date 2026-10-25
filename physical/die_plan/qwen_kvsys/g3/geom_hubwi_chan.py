#!/usr/bin/env python3
"""PATH-KV-HUBWI 10-25: kv3_hub_Wi host-core re-place for a full-height E feed-through channel.

Diagnosis (f7 + per-bit channel FT sites): 1,138 FT bits run between the S strip (E/W pins y 6..116) and the N strip
(E/W pins y 1559..1668) and ft5/ft24 (1,264 bits) between the S strip and the mid band (y 613..855); the four host-core
bands (y 121..346, 363..613, 855..1175, 1192..1555) leave only a ~7-um core-free x strip (x > 1253), so
ft_bit_sites_chan finds no x channel and the PROTO per-bit scan puts 5,425 stations inside cores.

Fix (type-frame origins/orients only; outline, face pins, buses, FT slots, station counts unchanged): every host core
ends at x <= 1131.84 um, opening a core-free channel x 1131.84..1278.72 (121 um after the 6-um core clearance and the
20-um face keep) over the full height, next to the E face that carries 2,300+ of the FT bits:
  band S  (y 120.96): pad + 2x4 adapters unchanged; cdc_ci / cdc_hi shift W by 95 um (17.28-um gaps, as before);
          host_qm (3 data pins to cdc_ch / guard) leaves the band.
  band L  (top-aligned y 613.44, under the mid band): guard, prompt, rx, queue (34.56-um gaps); rx (259.2 um) leaves
          the full band above: it sits under tx (rx<->tx 1,079 bits), prompt under peer/tx (876 / 1,415 bits), queue
          under host_qm / cdc_ch (548 bits).
  band U  (y 855.36): cdc_pc, peer, tx (34.56-um gaps), host_qm under cdc_ch.
  band T  (y 1192.32): ingest, order, cdc_ch unchanged.
Core pins: g3/core_reface.py re-faces every port check.py core_faces FAILs after the move (planned cores, none
hardened).
usage: geom_hubwi_chan.py IN_PLAN OUT_PLAN"""
import json
import sys
from pathlib import Path

G = 8.64
NEW = {   # inst -> (x, y, orient)
    "host__qkd_hr_cdc_ci": (665.28, 120.96, "R0"), "host__qkd_hr_cdc_hi": (907.2, 120.96, "R0"),
    "host__qkd_hr_core_guard": (25.92, 362.88, "R0"), "host__qkd_hr_core_prompt": (319.68, 380.16, "R0"),
    "host__qkd_hr_core_rx": (587.52, 354.24, "R0"), "host__qkd_hr_core_queue": (881.28, 371.52, "R0"),
    "host__qkd_hr_cdc_pc": (25.92, 855.36, "R0"), "host__qkd_hr_core_peer": (380.16, 855.36, "R0"),
    "host__qkd_hr_core_tx": (725.76, 855.36, "R0"), "host__qkd_hr_host_qm": (1036.8, 1088.64, "R0"),
}
XMAX = 1131.84


def check(t):
    """fail-closed: every host core ends at x <= XMAX (the E FT channel x XMAX..W stays core-free over the full
    height) and core pairs keep >= 17.28 um (2 x 8.64 grid) between them.  Returns the core boxes."""
    bx = [(c["inst"], c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
           c["origin_um"][1] + c["outline_um"][1]) for c in t["hard_cores"]]
    for i, a in enumerate(bx):
        if a[3] > XMAX + 1e-6:
            raise ValueError(f"core {a[0]} reaches x {a[3]:.2f} > {XMAX} (inside the E FT channel)")
        for b in bx[i + 1:]:
            gx = max(b[1] - a[3], a[1] - b[3])
            gy = max(b[2] - a[4], a[2] - b[4])
            if max(gx, gy) < 17.28 - 1e-6:
                raise ValueError(f"cores {a[0]} / {b[0]} gap {max(gx, gy):.2f} < 17.28 um")
    return bx


def main():
    src, dst = sys.argv[1:3]
    raw = json.loads(Path(src).read_text())
    t = raw["partition_types"]["kv3_hub_Wi"]
    for c in t["hard_cores"]:
        if c["inst"] in NEW:
            x, y, o = NEW[c["inst"]]
            assert abs(x / G - round(x / G)) < 1e-9 and abs(y / G - round(y / G)) < 1e-9, c["inst"]
            c["origin_um"], c["orient"] = [x, y], o
    bx = check(t)
    t["note"] = t.get("note", "") + (" | PATH-KV-HUBWI 10-25: host cores re-placed (geom_hubwi_chan.py) -> full-height "
                                     "core-free E FT channel x 1131.84..1278.72 um")
    Path(dst).write_text(json.dumps(raw, indent=1) + "\n")
    print("geom_hubwi_chan: %d cores moved; max core x %.2f" % (len(NEW), max(b[3] for b in bx)))


if __name__ == "__main__":
    main()
