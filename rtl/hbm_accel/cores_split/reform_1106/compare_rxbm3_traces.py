"""compare_traces.py BASE_DIR FORM_DIR RX_OFF ST0_OFF ST1_OFF [FROM]: form(t) == base(t - off) on rx / st[0] / st[1] for
t >= FROM (default 90: rst_n is released at cycle 80; OT_S81_RM_STAGED r_d carries no reset by design), and the base
decodes the sent beats."""
import sys
def tr(d):
    out = {}
    for ln in open(d + "/trace.txt"):
        c, rx, st = ln.split(); out[int(c)] = (rx, st)
    return out
b, f = tr(sys.argv[1]), tr(sys.argv[2]); ro, s0, s1 = map(int, sys.argv[3:6])
from_c = int(sys.argv[6]) if len(sys.argv) > 6 else 90
sent = [ln.split() for ln in open(sys.argv[1] + "/sent.txt")]
idx = {}
for i, (fr, ne, d) in enumerate(sent): idx.setdefault(d.lstrip("0") or "0", (i, int(fr), int(ne)))
# base decode: non-idle rx beats that equal a sent beat, in order
seq = []; nonidle = 0
for c in sorted(b):
    rx = b[c][0].lstrip("0") or "0"
    if rx == "2": continue
    nonidle += 1
    if rx in idx: seq.append(idx[rx])
ordered = all(seq[i][0] < seq[i+1][0] for i in range(len(seq) - 1))
frames_ok = {}
for i, fr, ne in seq: frames_ok[fr] = frames_ok.get(fr, 0) + 1
exact = sum(1 for fr, n in frames_ok.items() if n == 10)
corr_frames = sum(1 for fr in {int(s[0]) for s in sent} if int(sent[10 * fr][1]) <= 15)
mm = {"rx": 0, "st0": 0, "st1": 0}; n = 0; first = None
for c in sorted(f):
    if c < from_c: continue
    for key, off, get in (("rx", ro, lambda v: v[0]), ("st0", s0, lambda v: v[1][1]), ("st1", s1, lambda v: v[1][0])):
        if c - off in b:
            if get(f[c]) != get(b[c - off]):
                mm[key] += 1
                if first is None: first = (key, c)
    n += 1
st0_rise_b = next((c for c in sorted(b) if b[c][1][1] == "1"), None)
st0_rise_f = next((c for c in sorted(f) if f[c][1][1] == "1"), None)
ok = all(v == 0 for v in mm.values()) and ordered and exact >= 0.8 * corr_frames and nonidle > 0
print(f"COMPARE cycles={n} mismatches={mm} first={first} base_nonidle={nonidle} base_exact_frames={exact}/"
      f"{corr_frames}correctable ordered={ordered} st0_rise base={st0_rise_b} form={st0_rise_f} -> {'PASS' if ok else 'FAIL'}")
