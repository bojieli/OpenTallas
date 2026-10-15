#!/usr/bin/env python3
"""Bit-local pin plans of the S81 SU spine taps (el1013 s81su-kvsw, 2026-10-13).

The three taps are pin-bound register stages; their first kits let the pin placer choose the tracks:

  dsfd_su_t_swtl / dsfd_su_t_swth (36.72 x 453.6 each, el1013-s81su-qual): the SW tap as two half-taps after swt v1
      (FLOORPLAN_MARGIN) and v2 (EARLY_FAIL_DRC: 473 of the violations in one 60 x 60 um bin, the control cluster pulled
      to the middle of the 572-um tile by the 352 descriptor bits it captures); each half 4,096 b W -> E on M4.
  dsfd_su_t_qbt / (dsfd_su_t_swt until 10-13) (572.4 x 453.6; e_d <= dn_d, 8,192 b through one register):
      FLOORPLAN_MARGIN, pins packed on every track of ~200 um of each face (20 b/um/layer > 12).
      Plan: pins on every SECOND track over the whole face (10.4 b/um on W / E M4, <= 8.6 b/um on N / S M5 between the
      M5 power stripes); bit i enters and leaves on the SAME track (dn_dl[i] W -> e_dl[i] E, dn_dh[i] S -> e_dh[i] N),
      so the data crosses the tile as 4,096 straight M4 rows and 4,096 straight M5 columns.
      Cuts: any vertical line, 4,096 + ~250 of 9,450 M4 tracks = 0.46 (M2 free); any horizontal line, 4,096 of
      ~10,700 free M5 tracks = 0.38 (M3 free).

  dsfd_su_t_kvt (36.72 x 453.6; 16 slots x 128 b rotated into 32 positions x 128 b):
      EARLY_FAIL_CONGESTION, M3 235 % / M5 90 % (1.37 M + 0.39 M vertical demand over 1.01 M supply): the pins were
      ordered by POSITION, so every level of the barrel carried all 4,128 bits 12.5 .. 200 um along the 36.72-um column.
      Plan: order the pins by BIT.  Band b (3.264 um = 68 M4 tracks) holds dn_d[128 s + b] for the 16 slots and
      e_cs[128 j + b] (4 parameter rows) on W, e_d[128 j + b] for the 32 positions (+ e_ob / e_eps of that bit) on E:
      the 16 -> 32 rotation of a bit never leaves its band.  The control (pin flops, row numbering, the valid bit's
      rotation) sits in a 13-um band at mid height; the offset copies are one a bit bank (RTL NB 64).
      Cuts: a horizontal line carries only control (~150 nets of ~1,700 M3 + M5 tracks = 0.09); a vertical line inside a
      band carries <= 52 nets of 158 M2 + M4 tracks = 0.33.  Faces: E 34 pins a band = 10.4 b/um, W 20 = 6.1 b/um.

Output: place_pin files for the ref_tile spec key "io_tcl".
"""
from __future__ import annotations

import argparse
import pathlib

M4_OFF, M4_P = 0.012, 0.048        # horizontal tracks (y)
M5_OFF, M5_P = 0.012, 0.048        # vertical tracks (x)
PIN_L, PIN_W = 0.192, 0.024
CORE = 2.16                         # ref_tile core margin
PG_P, PG_LO, PG_HI = 5.4, 0.10, 1.00   # M5 power stripes: offset 0.30, 2 x 0.12 wide, 0.072 apart (core-relative window kept clear)


def bits(name: str, n: int) -> list:
    return [name] if n == 1 else [f"{name}[{i}]" for i in range(n)]


class Plan:
    def __init__(self, w: float, h: float):
        self.w, self.h, self.rows, self.used = w, h, [], {}

    def _put(self, face: str, name: str, k: int):
        key = (face, k)
        if key in self.used:
            raise SystemExit(f"track clash {face} {k}: {name} / {self.used[key]}")
        self.used[key] = name
        if face in "WE":
            y = M4_OFF + M4_P * k
            if not 3.0 <= y <= self.h - 3.0:
                raise SystemExit(f"{name}: y {y:.3f} off the {face} face")
            x = PIN_L / 2 if face == "W" else self.w - PIN_L / 2
            self.rows.append((face, "M4", y, f"place_pin -pin_name {{{name}}} -layer M4 -location {{{x:.4f} {y:.4f}}} "
                                             f"-pin_size {{{PIN_L:.4f} {PIN_W:.4f}}}"))
        else:
            x = M5_OFF + M5_P * k
            if not 3.0 <= x <= self.w - 3.0:
                raise SystemExit(f"{name}: x {x:.3f} off the {face} face")
            y = PIN_L / 2 if face == "S" else self.h - PIN_L / 2
            self.rows.append((face, "M5", x, f"place_pin -pin_name {{{name}}} -layer M5 -location {{{x:.4f} {y:.4f}}} "
                                             f"-pin_size {{{PIN_W:.4f} {PIN_L:.4f}}}"))

    def run(self, face: str, names: list, k0: int, step: int = 2) -> int:
        """names on tracks k0, k0 + step, ...; returns the next free track"""
        for i, n in enumerate(names):
            self._put(face, n, k0 + step * i)
        return k0 + step * len(names)

    def density(self, win: float = 100.0) -> dict:
        out = {}
        for f in "WESN":
            pos = sorted(p for ff, _, p, _ in self.rows if ff == f)
            best, j = 0, 0
            for i, p in enumerate(pos):
                while pos[j] < p - win:
                    j += 1
                best = max(best, i - j + 1)
            if pos:
                out[f] = (len(pos), round(best / win, 2))
        return out

    def write(self, path: pathlib.Path, head: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        order = {"W": 0, "E": 1, "S": 2, "N": 3}
        rows = sorted(self.rows, key=lambda r: (order[r[0]], r[2]))
        path.write_text("# " + head + "\n# generated by tools/s81_suhc/su_tap_io.py (do not edit)\n"
                        + "\n".join(r[3] for r in rows) + "\n")


def m5_free_tracks(w: float) -> list:
    """M5 tracks of the N / S faces clear of the M5 power stripes, every second track"""
    out, k = [], int((6.0 - M5_OFF) / M5_P) + 1
    while M5_OFF + M5_P * k <= w - 6.0:
        r = (M5_OFF + M5_P * k - CORE) % PG_P
        if not PG_LO <= r <= PG_HI:
            out.append(k)
            k += 2
        else:
            k += 1
    return out


def through_tap(w: float, h: float, w_ctl: list, e_ctl: list) -> Plan:
    """qbt / swt: dn_dl W -> e_dl E on one M4 track a bit, dn_dh S -> e_dh N on one M5 track a bit; control low on W / E
    (next to dn_dl[0 ..], the descriptor words the control captures)."""
    p = Plan(w, h)
    k = int((6.0 - M4_OFF) / M4_P) + 1
    kw = p.run("W", w_ctl, k)
    ke = p.run("E", e_ctl, k)
    k0 = max(kw, ke) + 8
    p.run("W", bits("dn_dl", 4096), k0)
    p.run("E", bits("e_dl", 4096), k0)
    free = m5_free_tracks(w)
    if len(free) < 4096:
        raise SystemExit(f"N / S: {len(free)} free M5 tracks < 4096")
    # centre the 4,096 columns on the face
    f0 = (len(free) - 4096) // 2
    for i in range(4096):
        p._put("S", f"dn_dh[{i}]", free[f0 + i])
        p._put("N", f"e_dh[{i}]", free[f0 + i])
    return p


def half_tap(w_ctl: list, e_ctl: list, din: str, dout: str) -> Plan:
    """SW / QB half-tap column (36.72 x 453.6, as kvt / qnt): 4,096 data bits W -> E, bit i in and out on the same M4 track,
    every second track (393 um of the 453.6-um face, 10.4 b/um); the control low on both faces, next to data bit 0
    (the descriptor words the control captures are bits 0..511)."""
    p = Plan(36.72, 453.6)
    k = int((6.0 - M4_OFF) / M4_P) + 1
    kw = p.run("W", w_ctl, k)
    ke = p.run("E", e_ctl, k)
    k0 = max(kw, ke) + 8
    p.run("W", bits(din, 4096), k0)
    p.run("E", bits(dout, 4096), k0)
    return p


def qbtl() -> Plan:
    w_ctl = ["ck", "rst", "dn_st", *bits("dn_kind", 4), *bits("dn_gsel", 2), "dn_fp4", *bits("dn_jid", 8), *bits("dn_v", 16)]
    e_ctl = [*bits("e_v", 16), *bits("e_t", 192), *bits("e_ob", 14), "e_f4", "o_fu", "o_fo", "o_alive", "o_den", "o_rdy",
             *bits("o_rjid", 8)]
    return half_tap(w_ctl, e_ctl, "dn_dl", "e_dl")


def swtl() -> Plan:
    w_ctl = ["ck", "rst", "dn_st", *bits("dn_kind", 4), *bits("dn_gsel", 2), "dn_fp4", *bits("dn_jid", 8), *bits("dn_v", 16)]
    e_ctl = [*bits("e_gv", 4), *bits("e_uv", 4), *bits("e_t", 12), *bits("e_w", 32), *bits("e_lim", 32), *bits("e_ob", 14),
             *bits("i_f", 32), "o_fu", "o_fo", "o_alive", "o_den", "o_rdy", *bits("o_rjid", 8)]
    return half_tap(w_ctl, e_ctl, "dn_dl", "e_dl")


def swth() -> Plan:
    return half_tap(["ck"], [], "dn_dh", "e_dh")


def kvt() -> Plan:
    w, h = 36.72, 453.6
    p = Plan(w, h)
    BAND = 68                                   # M4 tracks a bit band (3.264 um)
    CTL = 272                                   # control band (13.056 um) between bit bands 63 and 64
    k0 = int((8.0 - M4_OFF) / M4_P) + 1

    def base(b: int) -> int:
        return k0 + BAND * b + (CTL if b >= 64 else 0)

    for b in range(128):
        kb = base(b)
        p.run("W", [f"dn_d[{128 * s + b}]" for s in range(16)] + [f"e_cs[{128 * j + b}]" for j in range(4)], kb + 1, 3)
        e = [f"e_d[{128 * j + b}]" for j in range(32)]
        if b < 14:
            e.append(f"e_ob[{b}]")
        if b >= 96:
            e.append(f"e_eps[{b - 96}]")
        p.run("E", e, kb, 2)
    kc = k0 + BAND * 64 + 4
    p.run("W", ["ck", "rst", "dn_st", *bits("dn_kind", 4), *bits("dn_gsel", 2), *bits("dn_jid", 8), *bits("dn_v", 16),
                *bits("i_f", 65)], kc, 2)
    p.run("E", [*bits("e_v", 32), "e_gk", *bits("e_gr", 2), *bits("e_gw", 2), "e_go", "o_fu", "o_fo", "o_alive", "o_den",
                "o_rdy", *bits("o_rjid", 8)], kc, 2)
    return p


TILES = {"s81su_qbtl_ref": (qbtl, "dsfd_su_t_qbtl: QB half-tap (slots 0-7 + control), 4,096 straight M4 bit tracks W -> E; slots 8-15 = dsfd_su_t_swth"),
         "s81su_swtl_ref": (swtl, "dsfd_su_t_swtl: SW half-tap (slots 0-7 + control), 4,096 straight M4 bit tracks W -> E"),
         "s81su_swth_ref": (swth, "dsfd_su_t_swth: SW half-tap (slots 8-15), 4,096 straight M4 bit tracks W -> E"),
         "s81su_kvt_ref": (kvt, "dsfd_su_t_kvt: bit-local bands (16 slots W, 32 positions E), control at mid height")}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="physical/s81su_taps")
    a = ap.parse_args()
    for name, (fn, head) in TILES.items():
        p = fn()
        p.write(pathlib.Path(a.out) / f"{name}_io.tcl", head)
        print(name, len(p.rows), "pins; face: (pins, max b/um over 100 um)", p.density())


if __name__ == "__main__":
    main()
