"""R20: clock-channel keep-in for horizontal trunks (6 centre-row clock M7 stair / partition M7 pin DRC markers).
A host-less channel cell's trunk must stay inside its clock_channel rect so the M7 riser never crosses the partition
face (where the partition M7 pins sit)."""
import sys
d = sys.argv[1]
p = d + "/die_clock_128.py"
s = open(p).read()
old = '''    def place(self, layer, ideal, a0, a1, net):
        """(centre, mode) of the nearest legal track, or (None, None)"""
        tr = self.tracks[layer]'''
new = '''    def place(self, layer, ideal, a0, a1, net, keep=None):
        """(centre, mode) of the nearest legal track, or (None, None).  keep (R20, optional): (lo, hi) band the track
        centre must lie in (a clock-channel keep-in: the riser of a host-less channel cell never leaves the channel)."""
        tr = self.tracks[layer]'''
assert s.count(old) == 1; s = s.replace(old, new)
old = '''                c = round(offs + k * pitch, 4)
                if abs(c - ideal) > self.max_move + 1e-9:
                    continue
                e = self.tie_ext(layer, c, a0, a1)'''
new = '''                c = round(offs + k * pitch, 4)
                if abs(c - ideal) > self.max_move + 1e-9:
                    continue
                if keep is not None and not (keep[0] - 1e-9 <= c <= keep[1] + 1e-9):
                    continue
                e = self.tie_ext(layer, c, a0, a1)'''
assert s.count(old) == 1; s = s.replace(old, new)
old = '''    def track(layer, ideal, a0, a1, name, what):
        if router is None:
            last_ext[0] = None
            return ideal, DRAWN
        c, mode, e = router.place(layer, ideal, a0, a1, name)'''
new = '''    def track(layer, ideal, a0, a1, name, what, keep=None):
        if router is None:
            last_ext[0] = None
            return ideal, DRAWN
        c, mode, e = router.place(layer, ideal, a0, a1, name, **(dict(keep=keep) if keep else {}))'''
assert s.count(old) == 1; s = s.replace(old, new)
old = '''    txy = {t["port"]: tuple(t["xy"]) for t in M["taps"]}
    root = tuple(M["meta"]["root_um"])
    errs, out, last_ext = [], [], [None]
    port_moves = {}'''
new = '''    txy = {t["port"]: tuple(t["xy"]) for t in M["taps"]}
    root = tuple(M["meta"]["root_um"])
    errs, out, last_ext = [], [], [None]
    port_moves = {}
    # R20 (opt-in via meta.clock_channel_keep = [[x0, y0, x1, y1], ...]): a horizontal trunk whose driver pin sits in a
    # clock channel keeps its track inside the channel, CHANNEL_KEEP_UM off each channel edge
    chans = [tuple(r) for r in (M.get("meta", {}).get("clock_channel_keep") or [])]

    def chan_keep(pxy):
        for r in chans:
            if r[0] <= pxy[0] <= r[2] and r[1] <= pxy[1] <= r[3]:
                return (r[1] + CHANNEL_KEEP_UM, r[3] - CHANNEL_KEEP_UM)
        return None'''
assert s.count(old) == 1; s = s.replace(old, new)
old = '''            ty, tm = track("M8", D[1] + off, rsv[0], rsv[1], nm, "trunk")'''
new = '''            ty, tm = track("M8", D[1] + off, rsv[0], rsv[1], nm, "trunk", keep=chan_keep(D) if dcell else None)'''
assert s.count(old) == 1; s = s.replace(old, new)
old = '''STACK_RISER_MAX_UM = 2.5 '''
new = '''CHANNEL_KEEP_UM = 0.864     # R20: channel-cell trunk centre >= one track pair (TREE_OFF_UM) inside the channel edge
STACK_RISER_MAX_UM = 2.5 '''
assert s.count(old) == 1; s = s.replace(old, new)
open(p, "w").write(s)

p = d + "/die_clock_mesh.py"
s = open(p).read()
old = '''    ties = {us[0]: list(us) for us in groups.values() if len(us) > 1}
    # physical view: one pin stack per GROUP (the tie reaches the other units); logical nets keep every unit'''
new = '''    ties = {us[0]: list(us) for us in groups.values() if len(us) > 1}
    if chan_rects and spec.get("channel_keep", True):
        # R20: channel-hosted cells keep their trunk (and so the M7 riser) inside the clock channel
        out["meta"]["clock_channel_keep"] = [list(r) for r in chan_rects]
    # physical view: one pin stack per GROUP (the tie reaches the other units); logical nets keep every unit'''
assert s.count(old) == 1; s = s.replace(old, new)
open(p, "w").write(s)
print("patched")
