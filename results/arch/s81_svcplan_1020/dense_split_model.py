"""DRIVE-S81-SVCPLAN 10-20: MODEL -- minimum pinned stage count when a die has F < 112 frames.
The actual allocator refuses F < 112 (wq_a 320 rows one-phase: probe_f98/f84/f106 logs).  Model: per-frame words scale
112/F from the actual 112-frame probes (slope 72, dense N0 q); every dense layer's attention is split over TWO consecutive
stage die-groups (half the dense q each; never two attention halves on one stage); experts fill as xs_stage_map.build.
Rate: +456 cycles per added stage (139-stage calendar: added_hops 19,152 over 42 stages), clock 1.2 GHz; MU users not modelled."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "root/tools/s81_dv/layer_prog"))
import xs_stage_map as SM
D = json.loads(Path("stage_model.json").read_text())["costs"]
layers, _ = SM.census(); NL = len(layers); NE = 384
def stages(F, split):
    k = 112.0 / F; slope = D["slope"] * k; halves = 2 if split else 1
    order = []
    for L in range(NL):
        dq = D["dense"][SM.cls_of(L)]["q"] * k / halves
        order += [("d", dq)] * halves + [("e", slope)] * NE
    n, load, att = 0, 0.0, False
    for kind, add in order:
        if (kind == "d" and att) or load + add > 8191:
            n += 1; load, att = 0.0, False
        load += add; att = att or kind == "d"
    return n + 1
T_AR, T_MTP, HOP, N0 = 1186042.6, 1668506.8, 456.0, 139
FCLK = 1011.8 * T_AR; TAU = 2991.2 * T_MTP / FCLK
rows = {}
for F, split in ((112, False), (112, True), (98, True), (84, True)):
    n = stages(F, split); dt = HOP * (n - N0)
    rows[f"F{F}{'_split' if split else ''}"] = dict(frames=F, dense_split_2=split, stages=n, layer_dies=4 * n,
        total_dies=4 * n + 32 + 52, ar_per_user_G16=round(FCLK / (T_AR + dt), 1), mtp_per_user_G16=round(TAU * FCLK / (T_MTP + dt), 1),
        ar_per_user_G4=round(FCLK / (T_AR + dt) * (1 - 0.033), 1), mtp_per_user_G4=round(TAU * FCLK / (T_MTP + dt) * (1 - 0.0138), 1))
print(json.dumps(rows, indent=1))
