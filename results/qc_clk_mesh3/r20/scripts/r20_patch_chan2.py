"""R20 refinement: the channel keep-in applies only when the unconstrained nearest legal track would leave the channel
(so every other trunk keeps its R17 track: no cascade)."""
import sys
p = sys.argv[1] + "/die_clock_128.py"
s = open(p).read()
old = '''    def place(self, layer, ideal, a0, a1, net, keep=None):'''
new = '''    def place(self, layer, ideal, a0, a1, net, keep=None, dry=False):'''
assert s.count(old) == 1; s = s.replace(old, new)
old = '''                    mode = DRAWN
                elif flanked(self.pg, sh[0], flank_gap(self.nd)):
                    mode, sh, e = FLANK, sh[:1], None
                else:
                    continue
                return self._take(layer, ideal, c, mode, e, sh)'''
new = '''                    mode = DRAWN
                elif flanked(self.pg, sh[0], flank_gap(self.nd)):
                    mode, sh, e = FLANK, sh[:1], None
                else:
                    continue
                if dry:
                    return c, mode, e
                return self._take(layer, ideal, c, mode, e, sh)'''
assert s.count(old) == 1; s = s.replace(old, new)
old = '''        if untied is not None:
            self.modes[f"{layer}:untied"] += 1'''
new = '''        if untied is not None and dry:
            return untied[0], DRAWN, None
        if untied is not None:
            self.modes[f"{layer}:untied"] += 1'''
assert s.count(old) == 1; s = s.replace(old, new)
old = '''        c, mode, e = router.place(layer, ideal, a0, a1, name, **(dict(keep=keep) if keep else {}))'''
new = '''        if keep:      # R20: constrain only a track that would leave the clock channel (others unchanged)
            c0 = router.place(layer, ideal, a0, a1, name, dry=True)[0]
            if c0 is not None and keep[0] - 1e-9 <= c0 <= keep[1] + 1e-9:
                keep = None
            else:
                router.modes[f"{layer}:channel_keep"] += 1
        c, mode, e = router.place(layer, ideal, a0, a1, name, **(dict(keep=keep) if keep else {}))'''
assert s.count(old) == 1; s = s.replace(old, new)
open(p, "w").write(s)
print("patched2")
