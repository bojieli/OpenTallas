"""R21 probe: why the lane-0 channel trunks (ckm_w_ckt_1198_0 / 20123 / 20160) leave the channel.  Re-runs the dry
build in-process with TrackRouter.place instrumented for those nets: every M8 candidate centre and its reject reason."""
import json, math, sys
import die_clock_128 as C, die_clock_mesh as DM
NETS = {"ckm_w_ckt_1198_0", "ckm_w_ckt_20123_0", "ckm_w_ckt_20160_0"}
orig = C.TrackRouter.place
log = []
hit_ex = {}


def place(self, layer, ideal, a0, a1, net, keep=None, dry=False, avoid=()):
    if net in NETS and layer == "M8" and not dry:
        tr = self.tracks[layer]; pitch, offs = tr["pitch_um"], tr["offset_um"]
        k0 = round((ideal - offs) / pitch); rows = []
        for k in range(k0 - 40, k0 + 80):
            c = round(offs + k * pitch, 4)
            e = self.tie_ext(layer, c, a0, a1)
            sh = C.seg_shapes(layer, c, a0, a1, net, self.nd, self.shield, ext=e)
            hh = self.ix.hits(sh[0])
            if hh and 13132.0 < c < 13138.2 and len(log) < 3:
                hit_ex.setdefault(round(c, 2), [self.ix.shapes[k][:7] for k, _ in hh[:3]])
            why = "metal_hit" if hh else (
                "shield_hit" if any(self.ix.hits(s, first=True) for s in sh[1:]) else ("untied" if e is None else "OK"))
            rows.append((c, why))
        log.append(dict(net=net, ideal=ideal, span=[a0, a1], rows=rows))
    r = orig(self, layer, ideal, a0, a1, net, keep=keep, dry=dry, avoid=avoid)
    if net in NETS and layer == "M8" and not dry:
        log[-1]["chosen"] = r[0]
    return r


C.TrackRouter.place = place
try:
    DM.main(["build", sys.argv[1], "--explicit-cells", sys.argv[2], "--ndr", "16w", "--out", sys.argv[3]])
except SystemExit:
    pass
for L in log:
    print(L["net"], "ideal", L["ideal"], "span", [round(v, 1) for v in L["span"]], "chosen", L.get("chosen"))
    run, prev = [], None
    for c, why in L["rows"]:
        if why != prev:
            run.append([c, c, why]); prev = why
        else:
            run[-1][1] = c
    print("   ", [(a, b, w) for a, b, w in run if 13125 < b and a < 13180])
print("HITS", json.dumps({k: v for k, v in list(hit_ex.items())[::8]}))
json.dump(log, open(sys.argv[3] + "_probe.json", "w"))
