#!/usr/bin/env python3
"""Visual + geometric regression of the layout viewer against KLayout (an independent DEF/LEF reader and renderer).

  PYTHONPATH=<klayout>=0.29 python module> python3 lv_visual.py --def 6_final.def --lef-dir DIR --pack <element>.lvp \
      --url http://127.0.0.1:8765 --element <id> --box x0 y0 x1 y1 (um) [--layers M2,M3,...] --out DIR

1. geometry: the pack's full decoded shape set (lv_verify.js --dump) against KLayout's reading of the same element's
   6_final.def + LEFs, per layer, as merged regions over the whole die: XOR area (nm^2) and its share of the layer area.
   KLayout's Mx comprises routing, special routing, DEF pins (Mx.PIN) and the LEF macro geometry of the placed cells.
2. pixels: KLayout's LayoutView renders each layer of --box solid white on black; the viewer renders the same window
   with the layer solo in its regression mode (?lvsolid=1: solid white, no outline / stipple).  Both binarised; reported:
   IoU and the share of pixels that differ by more than one pixel of edge (antialiasing / rasterisation rule).
Writes <out>/visual.json and the image pairs.
"""
import argparse, asyncio, json, os, subprocess, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def kl_options(lefdir):
    """LEF/DEF reader options: everything the DB holds lands on the plain layer (routing, special routing, DEF pins,
    LEF pins and LEF OBS of the placed cells), the same composition as the viewer's layers"""
    import klayout.db as db
    opt = db.LoadLayoutOptions(); c = opt.lefdef_config
    c.lef_files = sorted([str(p.resolve()) for p in Path(lefdir).glob('*.lef')], key=lambda f: 0 if 'tech' in f else 1)
    c.produce_obstructions = True; c.obstructions_suffix = ''; c.obstructions_datatype = 0
    c.produce_lef_pins = True; c.lef_pins_suffix = ''; c.lef_pins_datatype = 0
    c.produce_pins = True; c.pins_suffix = ''; c.pins_datatype = 0
    c.produce_blockages = True; c.blockages_suffix = ''; c.blockages_datatype = 0
    c.macro_resolution_mode = 1   # always build placed cells from their LEF MACRO geometry (pins + OBS)
    opt.lefdef_config = c
    return opt


def kl_layout(defp, lefdir):
    import klayout.db as db
    ly = db.Layout(); ly.read(defp, kl_options(lefdir))
    return ly


def kl_region(ly, name, box=None):
    import klayout.db as db
    r = db.Region()
    for i in ly.layer_indexes():
        inf = ly.get_info(i)
        if inf.name in (name, name + '.PIN'):
            r.insert(db.RecursiveShapeIterator(ly, ly.top_cell(), i, db.Box(*box)) if box else db.RecursiveShapeIterator(ly, ly.top_cell(), i))
    r.flatten()
    return r.merged()


def header_layers(pack):
    import brotli, struct
    if str(pack).endswith('.json'):
        man = json.loads(Path(pack).read_text()); h = man['objects']['header']
        b = (Path(pack).resolve().parent.parent.parent / 'objects' / h[:2] / (h + '.br')).read_bytes()
    else:
        with open(pack, 'rb') as f:
            io, il = struct.unpack('<QQ', f.read(24)[8:]); f.seek(io); idx = json.loads(brotli.decompress(f.read(il)))
            f.seek(idx['header'][0]); b = f.read(idx['header'][1])
    return [l['name'] for l in json.loads(brotli.decompress(b))['layers']]


def geometry(ly, pack, layers, out, box=None):
    import klayout.db as db
    dump = out / 'decoded.bin'
    subprocess.run(['node', str(HERE / 'lv_verify.js'), pack, '--dump', str(dump)], check=False, capture_output=True)
    hdr = header_layers(pack)
    a = np.fromfile(dump, dtype='<i4').reshape(-1, 5)
    res = {}
    for name in layers:
        li = hdr.index(name)
        m = a[a[:, 0] == li]
        if box is not None:   # window: shapes touching it, both sides clipped to it
            m = m[(m[:, 1] < box[2]) & (m[:, 3] > box[0]) & (m[:, 2] < box[3]) & (m[:, 4] > box[1])]
        ours = db.Region()
        for r in m: ours.insert(db.Box(int(r[1]), int(r[2]), int(r[3]), int(r[4])))
        ours.merge()
        kl = kl_region(ly, name, box)
        if box is not None:
            w = db.Region(db.Box(*box)); ours = ours & w; kl = kl & w
        x = ours ^ kl
        res[name] = dict(ours_area_um2=ours.area() / 1e6, klayout_area_um2=kl.area() / 1e6, xor_area_nm2=x.area(),
                         xor_share=(x.area() / max(1, kl.area())), ours_polys=ours.count(), klayout_polys=kl.count())
    return res


def kl_images(defp, lefdir, box, layers, px, out):
    import klayout.lay as lay, klayout.db as db
    v = lay.LayoutView()
    v.load_layout(defp, kl_options(lefdir), True)
    v.max_hier()
    v.set_config('background-color', '#000000'); v.set_config('grid-visible', 'false'); v.set_config('text-visible', 'false')
    v.set_config('cell-box-visible', 'false'); v.set_config('stipple-offset', 'false')
    files = {}
    for name in layers:
        it = v.begin_layers()
        while not it.at_end():
            lp = it.current().dup()
            base = lp.source_name if hasattr(lp, 'source_name') else ''
            nm = lp.name or ''
            src = lp.source.split('@')[0].strip()
            lname = src.split(' ')[0] if src else nm
            lp.visible = lname in (name, name + '.PIN')
            lp.fill_color = 0xffffff; lp.frame_color = 0xffffff; lp.dither_pattern = 0; lp.width = 0; lp.transparent = False
            v.set_layer_properties(it, lp)
            it.next()
        v.zoom_box(db.DBox(*box))
        f = out / ('klayout_%s.png' % name)
        v.save_image(str(f), px, px)
        files[name] = f
    return files


async def viewer_images(url, element, box, layers, px, out):
    from playwright.async_api import async_playwright
    files = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=gl-egl', '--ignore-gpu-blocklist'])
        ctx = await b.new_context(viewport={'width': 1700, 'height': 2400})
        pg = await ctx.new_page()
        cx, cy = (box[0] + box[2]) / 2 * 1000, (box[1] + box[3]) / 2 * 1000
        for name in layers:
            await pg.goto('%s/explorer/element/?e=%s&lvsolid=1#tab=geo' % (url, element))
            await pg.wait_for_function('() => window.LayoutViewer && LayoutViewer.state().header && LayoutViewer.state().deck', timeout=300000)
            r = await pg.evaluate('''([name, cx, cy, span, px]) => { const V = LayoutViewer.state();
              V.L.forEach(l => l.vis = (l.name === name)); V.kindVis[13] = false;
              const vs = Object.assign({}, V.vs, {target: [cx, cy, 0], zoom: Math.log2(px / span)}); V.vs = vs; V.deck.setProps({initialViewState: vs});
              LayoutViewer._restyle(); LayoutViewer._update(); const c = V.root.querySelector('[data-canvas]').getBoundingClientRect(); return [c.left, c.top, c.width, c.height]; }''',
                                  [name, cx, cy, (box[2] - box[0]) * 1000, px])
            await pg.wait_for_function('() => { const V = LayoutViewer.state(); return V.mode === "geometry" && V.pending.size === 0 && V.tiles.size > 0 }', timeout=300000)
            await pg.wait_for_timeout(1500)
            f = out / ('viewer_%s.png' % name)
            await pg.screenshot(path=str(f), clip=dict(x=r[0] + r[2] / 2 - px / 2, y=r[1] + r[3] / 2 - px / 2, width=px, height=px))
            files[name] = f
        await b.close()
    return files


def mask(f):
    from PIL import Image
    a = np.asarray(Image.open(f).convert('L'), dtype=np.uint8)
    return a > 127


def compare(ka, va, search=6):
    """IoU after the best integer registration shift within +-search px (the two renderers place the window to within a
    pixel or two: KLayout fits the box to its canvas, the viewer centres its camera); the shift is reported"""
    from scipy import ndimage
    best = (-1, 0, 0)
    m = search
    kc = ka[m:-m, m:-m]
    for dy in range(-m, m + 1):
        for dx in range(-m, m + 1):
            vc = va[m + dy:va.shape[0] - m + dy, m + dx:va.shape[1] - m + dx]
            iou = (kc & vc).sum() / max(1, (kc | vc).sum())
            if iou > best[0]: best = (iou, dx, dy)
    _, dx, dy = best
    ka = kc; va = va[m + dy:va.shape[0] - m + dy, m + dx:va.shape[1] - m + dx]
    inter = (ka & va).sum(); uni = (ka | va).sum()
    x = ka ^ va
    near = ndimage.binary_dilation(ka, iterations=1) & ~ndimage.binary_erosion(ka, iterations=1)
    far = x & ~near
    return dict(iou=float(inter / max(1, uni)), shift_px=[dx, dy], xor_px=int(x.sum()), beyond_1px_edge=int(far.sum()),
                beyond_1px_share=float(far.sum() / max(1, ka.sum())), klayout_px=int(ka.sum()), viewer_px=int(va.sum()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--def', dest='defp', required=True); ap.add_argument('--lef-dir', required=True); ap.add_argument('--pack', required=True)
    ap.add_argument('--url', default='http://127.0.0.1:8765'); ap.add_argument('--element', required=True)
    ap.add_argument('--box', nargs=4, type=float, required=True); ap.add_argument('--layers', default='M1,M2,M3,M4,M5,M6,M7,V1,V2,V3,V4,V5,V6')
    ap.add_argument('--px', type=int, default=600); ap.add_argument('--out', required=True); ap.add_argument('--skip-geometry', action='store_true')
    ap.add_argument('--geo-box', nargs=4, type=float, help='um window for the geometry XOR (default: whole die)'); ap.add_argument('--skip-pixels', action='store_true')
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    layers = a.layers.split(',')
    res = dict(schema='opentallas.layout_viewer.visual.v1', element=a.element, box_um=a.box, px=a.px)
    if not a.skip_geometry:
        ly = kl_layout(a.defp, a.lef_dir)
        res['geometry'] = geometry(ly, a.pack, layers, out, [int(v * 1000) for v in a.geo_box] if a.geo_box else None)
        res['geo_box_um'] = a.geo_box
        (out / 'visual.json').write_text(json.dumps(res, indent=1))
    if not a.skip_pixels:
        kf = kl_images(a.defp, a.lef_dir, a.box, layers, a.px, out)
        vf = asyncio.run(viewer_images(a.url, a.element, a.box, layers, a.px, out))
        res['pixels'] = {n: compare(mask(kf[n]), mask(vf[n])) for n in layers}
    (out / 'visual.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
