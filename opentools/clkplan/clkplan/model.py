"""Technology model for the clock planner: repeated-wire stage delay, reach rules, local-tree cost, OCV table.

Default = ASAP7 (7.5-track RVT, BUFx24 clock repeaters on NDR M8/M9), from measured OpenTallas runs:
  * stage (BUFx24 -> 450 um NDR M8/M9 -> BUFx24): TT 100.24 ps, cell share 53.39 ps; FF 85.75 / 39.31 ps
    (ngspice BSIM-CMG Monte Carlo, results/clk_aocv_1026, 400 samples);
  * wire R 4.45 ohm/um, C 0.11 fF/um (NDR M8/M9, same deck);
  * reach rule 405 um per registered data hop, repeater spacing 450 um, max unrepeated clock leg 480 um
    (die_clock_mesh hop_max), street raster 8.64 um;
  * local tree (core / partition CTS stage): BUFx8 + 40 um + fanout 4 = 36.15 ps TT / 27.55 ps FF.
Stage delay of a segment of length L:   d(L) = d0 + k1 * L + k2 * L^2   (driver intrinsic + driver R x wire C +
distributed RC), with k2 = 0.5 r c scaled so that d(450) and the cell share at 450 match the measured stage.
Every number is a parameter: pass a JSON with the same keys to model.load() for another technology.
"""
import copy
import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

ASAP7 = dict(
    name="asap7_bufx24_ndr_m8m9",
    rep_um=450.0, leg_max_um=480.0, reach_um=405.0, raster_um=8.64,
    wire_r_ohm_um=4.45, wire_c_ff_um=0.11,
    # measured stage at rep_um (TT/FF) and its cell part
    stage_ps={"TT": 100.239, "FF": 85.751}, stage_cell_ps={"TT": 53.386, "FF": 39.313},
    # driver intrinsic share of the cell part at rep_um (rest = driver R x wire C, linear in L).  ASSUMED 0.67:
    # BUFx24 process-only delay at 184 fF is 72.8 ps TT (clk_aocv basis) -> ~0.26 ps/fF; 450 um x 0.11 = 49.5 fF
    # -> ~13 ps of the 53.4 ps cell part is load-dependent.
    d0_frac=0.75,
    # an H-tree node drives two children: its stage sees ~2x wire load on the first segment (extra cell delay)
    branch_extra_ps={"TT": 13.0, "FF": 10.0},
    local_stage_ps={"TT": 36.154, "FF": 27.549}, local_cell_share={"TT": 0.8789, "FF": 0.8348},
    local_fanout=4, local_leaf_sinks=12,
    buf_w_um=1.62, row_h_um=0.27,
    aocv_table="aocv_asap7_g021.json",
)


def load(path=None):
    m = copy.deepcopy(ASAP7)
    if path:
        m.update(json.loads(Path(path).read_text()))
    return Model(m)


class Model:
    def __init__(self, m):
        self.m = m
        self.k = {}
        L = m["rep_um"]
        for c in m["stage_ps"]:
            cell = m["stage_cell_ps"][c]
            wire = m["stage_ps"][c] - cell
            d0 = cell * m["d0_frac"]
            k1 = (cell - d0) / L
            k2 = wire / (L * L)
            self.k[c] = (d0, k1, k2)
        self.T = json.loads((DATA / m["aocv_table"]).read_text()) if m.get("aocv_table") else None
        if self.T is not None:
            self.T = self.T.get("clock_aocv", self.T)

    def __getitem__(self, k):
        return self.m[k]

    def seg_ps(self, L, corner="TT"):
        """one driven segment (buffer + wire of length L um)."""
        d0, k1, k2 = self.k[corner]
        return d0 + k1 * L + k2 * L * L

    def seg_cell_ps(self, L, corner="TT"):
        d0, k1, _ = self.k[corner]
        return d0 + k1 * L

    def wire_ps(self, L, corner="TT"):
        """ideally repeated wire of length L: n = ceil(L / rep) equal segments."""
        if L <= 0:
            return 0.0
        n = max(1, math.ceil(L / self.m["rep_um"] - 1e-9))
        return n * self.seg_ps(L / n, corner)

    def local_ps(self, n_sinks, corner="TT"):
        """local (leaf) tree below a tap for n flop sinks: fanout-4 levels of class-B stages."""
        if n_sinks <= 1:
            return 0.0
        lv = max(1, math.ceil(math.log(max(n_sinks, 2), self.m["local_fanout"]) - 1e-9))
        return lv * self.m["local_stage_ps"][corner]
