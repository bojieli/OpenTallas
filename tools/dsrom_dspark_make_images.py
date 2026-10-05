#!/usr/bin/env python3
"""Generate DS ROM DSpark MTP RTL images on the GPU host, for cached RTL runs elsewhere.

The image path of tools/rtl_hdc_dspark_v41x_campaign.py (golden_run, make_images,
hdc_images_v41x.write, isa.json), with no Verilator build and no simulation, so the
golden model never executes on a CPU-only simulation host. Image directory names
match the campaign's (i_<prompt>_<drafter>_g<gamma>_n<ngen>_<arith>), so the
images drop into a campaign --workdir or feed tools/dsrom_dspark_cached_rtl.py.
An image is written only if the ISA model's tokens equal the golden's greedy
stream and its committed logits are bit-exact with the golden's; a manifest
records every file's SHA-256.

    python3 tools/dsrom_dspark_make_images.py --out DIR --image gold4:dspark:3:12 ...
"""
import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
# Importing the campaign as a module fixes its default units (he,me) and sets the
# R-ARITH classes of the golden and ISA model exactly as the campaign does.
import rtl_hdc_dspark_v41x_campaign as campaign  # noqa: E402

C, IMG, P, V, X = campaign.C, campaign.IMG, campaign.P, campaign.V, campaign.X
I = campaign.I
_ME_OPS = IMG.me_ops
ZERO_ROW_ME_OPS = {}


def me_ops_reading_weights(lay, prog):
    """hdc_images_v41x.me_ops over the ME ops that read weight rows. At gamma < dspark_block
    the draft rows i >= gamma are emitted with me_nout = 0 (they skip, keeping slots aligned),
    on the same weight base as the live op; such an op reads no row, so it contributes nothing
    to the weight bank, but the pinned writer's one-shape-per-base assertion refuses it.
    The pinned writer is left byte-identical; a gamma-5 program has no such op (recorded)."""
    keep = [f for f in prog if not (f["unit"] == I.UNIT_ME and not f.get("me_wsrc", 0) and f.get("me_nout", 0) == 0)]
    ZERO_ROW_ME_OPS["last"] = len(prog) - len(keep)
    return _ME_OPS(lay, keep)


IMG.me_ops = me_ops_reading_weights


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def spec(text):
    prompt, drafter, gamma, ngen = text.split(":")
    if drafter not in ("dspark", "forced"):
        raise argparse.ArgumentTypeError(f"drafter {drafter!r}")
    return prompt, drafter, int(gamma), int(ngen)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--image", type=spec, action="append", required=True,
                    help="PROMPT:DRAFTER:GAMMA:NGEN (prompts of rtl_hdc_v41_mtp_campaign.prompts)")
    a = ap.parse_args()
    assert campaign.UNITS == ("he", "me") and V.ARITH == X.arith(), (campaign.UNITS, V.ARITH)
    model = V.Model()
    ps = C.prompts()
    programs, goldens, manifest = {}, {}, []
    a.out.mkdir(parents=True, exist_ok=True)
    for pn, d, gamma, ngen in a.image:
        img = a.out / f"i_{pn}_{d}_g{gamma}_n{ngen}_{V.ARITH.replace(',', '')}"
        if img.exists():
            raise SystemExit(f"refusing to overwrite {img}")
        if gamma not in programs:
            lay = P.mtp_layout(model, gamma)
            prog, entry = P.build_mtp(lay, gamma, 1)
            assert not any(f.get("mx_m", 0) > 1 for f in prog), "m = 1"
            programs[gamma] = (lay, prog, entry)
        lay, prog, entry = programs[gamma]
        t0 = time.time()
        if (pn, ngen) not in goldens:
            goldens[pn, ngen] = C.golden_run(model, ps[pn], ngen)
        tmp = img.with_name(img.name + ".partial")
        if tmp.exists():
            shutil.rmtree(tmp)
        isa = C.make_images(tmp, model, lay, prog, entry, ps[pn], ngen, gamma, d, False, goldens[pn, ngen])
        isa["v41x_images"] = IMG.write(tmp, lay, X.PARAMS["hhw"], X.PARAMS["mg"])
        (tmp / "isa.json").write_text(json.dumps(isa))
        ok = bool(isa["equal_golden_tokens"] and isa["committed_logits_bit_exact_with_golden"])
        print(pn, d, gamma, ngen, "isa", isa["equal_golden_tokens"], isa["committed_logits_bit_exact_with_golden"],
              isa["accepted"], f"{time.time() - t0:.0f}s", flush=True)
        if not ok:
            raise SystemExit(f"ISA model disagrees with the golden: {tmp} kept for inspection")
        tmp.rename(img)
        files = sorted(p for p in img.iterdir() if p.is_file())
        manifest.append({"zero_row_me_ops_excluded": ZERO_ROW_ME_OPS.pop("last"), "image": img.name, "prompt": pn, "drafter": d, "gamma": gamma, "ngen": ngen,
                         "arith": V.ARITH, "accepted": isa["accepted"], "tokens": isa["tokens"],
                         "equal_golden_tokens": isa["equal_golden_tokens"],
                         "committed_logits_bit_exact_with_golden": isa["committed_logits_bit_exact_with_golden"],
                         "sha256": {p.name: digest(p) for p in files}})
    sources = [Path(__file__).resolve(), *campaign.TOOLS]
    rec = {"schema": "opentallas.dsrom-dspark-images.v1", "units": list(campaign.UNITS), "arith": V.ARITH,
           "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in sources}, "images": manifest}
    path = a.out / f"manifest-{int(time.time())}.json"
    path.write_text(json.dumps(rec, indent=1) + "\n")
    print("manifest", path)


if __name__ == "__main__":
    raise SystemExit(main())
