# DIE-KV-13: render the step-5 KV pair image assets (bind5) for a visual check
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, numpy as np
O = Path(sys.argv[1]); W = json.load(open(sys.argv[2])); out = sys.argv[3]
A = O / "assets"; pair = json.load(open(A / "pair_transport_txdp.json"))
dcfg = [int(l, 16) for l in open(A / "native_dcfg_target10.hex").read().split()]
ages = [int(l, 16) for l in open(A / "native_boot_age_words.hex").read().split()]
C = json.load(open(O / "kv_constants2.json"))["constants"]
fig, ax = plt.subplots(2, 2, figsize=(15, 10))
bits = np.array([[(w >> b) & 1 for b in range(63, -1, -1)] for w in dcfg])
ax[0, 0].imshow(bits, aspect="auto", cmap="Greys", interpolation="nearest")
ax[0, 0].set_title(f"native DCFG target10: {len(dcfg)} x 64-bit words (bit 63 left)"); ax[0, 0].set_xlabel("bit"); ax[0, 0].set_ylabel("word")
p = W["ports"]; vs = sorted(p); x = np.arange(len(vs))
rt = [C["VPORT_RT"]["value"][v] for v in vs]
ax[0, 1].bar(x - 0.2, rt, 0.4, label="VPORT_RT (bind5 regen)"); ax[0, 1].bar(x + 0.2, [p[v]["pad"] for v in vs], 0.4, label="W pad stages (boot DQ model)")
ax[0, 1].axhline(95, color="r", ls="--", label="RT bound 95"); ax[0, 1].set_xticks(x); ax[0, 1].set_xticklabels([v[6:] for v in vs], rotation=90)
ax[0, 1].legend(fontsize=8); ax[0, 1].set_title("vports: round trip vs bound, W request pads")
seams = [int(s) for s in pair["XDIE_SEAM_K"].split(",")]; b48 = [68, 68, 66, 66, 66, 67, 67]; names = ["KS_RXV", "KS_RXP", "KS_TXS", "KS_TXK", "KS_TXB", "SK_TXV", "SK_TXP"]
xs = np.arange(7); ax[1, 0].bar(xs - 0.2, b48, 0.4, label="B48 seams"); ax[1, 0].bar(xs + 0.2, seams, 0.4, label="step-5 bind5 seams")
ax[1, 0].set_xticks(xs); ax[1, 0].set_xticklabels(names); ax[1, 0].legend(); ax[1, 0].set_title(f"KV<->QC seam stages; TXDP_K {pair["sv_literal"]}  TXDP_C {pair["D2D_TXDP_C"]}")
ax[1, 1].bar(range(len(ages)), [a & 0xffff for a in ages]); ax[1, 1].set_title(f"native boot age words ({len(ages)}), low 16 bits"); ax[1, 1].set_xlabel("word")
fig.suptitle("DIE-KV-13 step-5 KV pair image (bind5, inverter clock event)"); fig.tight_layout(); fig.savefig(out, dpi=80)
print("rendered", out)
