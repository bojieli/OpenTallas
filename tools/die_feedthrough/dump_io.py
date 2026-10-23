"""Readers for the odb_dump.py output directory (schema opentallas.die_feedthrough.dump.v1)."""
import gzip
import json
import os
from dataclasses import dataclass, field


@dataclass
class Bus:
    name: str
    dir: str            # INPUT / OUTPUT / INOUT
    nbits: int
    layers: tuple
    face: str           # N S E W A (area) ?
    lo: float           # along-face offset range, master frame (um)
    hi: float
    sig: str = "SIGNAL"


@dataclass
class Master:
    name: str
    w: float
    h: float
    npins: int
    pin_layers: dict
    obs_cover: dict     # layer -> covered fraction (sum of OBS rects / outline, clipped 1.0)
    buses: dict = field(default_factory=dict)

    def obs_top(self):
        ms = [int(k[1:]) for k, v in self.obs_cover.items() if k.startswith("M") and k[1:].isdigit() and v > 0.0]
        return max(ms) if ms else 0


@dataclass
class Inst:
    name: str
    master: str
    x: float
    y: float
    w: float
    h: float
    orient: str = "R0"

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2


def _open(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def _kv(s, cast=float):
    out = {}
    for tok in filter(None, s.split(",")):
        k, _, v = tok.partition(":")
        out[k] = cast(v) if v else 0
    return out


class Dump:
    def __init__(self, d):
        self.dir = d
        self.die = json.load(open(os.path.join(d, "die.json")))
        self.masters = {}
        for ln in _open(os.path.join(d, "masters.tsv")):
            f = ln.rstrip("\n").split("\t")
            while len(f) < 7:
                f.append("")
            self.masters[f[0]] = Master(f[0], float(f[1]), float(f[2]), int(f[3]), _kv(f[4], int), _kv(f[6]))
        for ln in _open(os.path.join(d, "mpins.tsv.gz")):
            f = ln.rstrip("\n").split("\t")
            m = self.masters.get(f[0])
            if m is None:
                continue
            m.buses[f[1]] = Bus(f[1], f[2], int(f[3]), tuple(filter(None, f[4].split(","))), f[5], float(f[6]),
                                float(f[7]), f[8] if len(f) > 8 else "SIGNAL")
        self.insts = {}
        for ln in _open(os.path.join(d, "blocks.tsv")):
            f = ln.rstrip("\n").split("\t")
            self.insts[f[0]] = Inst(f[0], f[1], float(f[2]), float(f[3]), float(f[4]), float(f[5]),
                                    f[6] if len(f) > 6 else "R0")
        self.bundles = []   # (src_inst, src_bus, dst_inst, dst_bus, bits, nbuf_max, nbuf_sum, sigtype)
        for ln in _open(os.path.join(d, "bundles.tsv.gz")):
            f = ln.rstrip("\n").split("\t")
            self.bundles.append((f[0], f[1], f[2], f[3], int(f[4]), int(f[5]), int(f[6]), f[7]))
        self.hifan = []
        p = os.path.join(d, "hifan.tsv")
        if os.path.exists(p):
            for ln in open(p):
                f = ln.rstrip("\n").split("\t")
                self.hifan.append(dict(inst=f[0], bus=f[1], nets=int(f[2]), sinks=int(f[3]), nbuf=int(f[4]), sig=f[5]))
        self.stdcells = {}
        p = os.path.join(d, "stdcells.tsv")
        if os.path.exists(p):
            for ln in open(p):
                f = ln.rstrip("\n").split("\t")
                self.stdcells[f[0]] = int(f[1])

    def layer(self, name):
        for L in self.die.get("layers", []):
            if L["name"] == name:
                return L
        return None
