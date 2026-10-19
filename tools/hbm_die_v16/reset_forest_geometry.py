"""Conservative reset relay placement. Geometry proof only; sign-off is downstream.

All coordinates are um. A home is a LOWER LEFT, matching die_case_v16.
The grid tests full relay rectangles at candidate centers against every
placed outline. Wires may overfly outlines, but every registered stage must
have a legal, distinct home and each routed span must fit the declared reach.
"""
import hashlib
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hbm_die_v15'))
from die_clock_tree import Grid, GRID
from view_case import lef_xy


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class GeometryError(ValueError):
    pass


class Geometry:
    def __init__(self, manifest, views, relay_views, reach):
        self.pl = manifest['placement']
        self.W, self.H = manifest['die_um']
        self.expected_hashes = manifest.get('consumed_view_sha256', {})
        self.views, self.relay_views = Path(views), Path(relay_views or views)
        self.reach = reach
        self.cache, self.hashes, self.reserved = {}, {}, {}
        self.relay = {k: self.lef('hbfd_rrl_' + k, self.relay_views) for k in ('hop', 'sync')}
        for kind, (w, h, pins) in self.relay.items():
            for p in ('rst_n_in', 'rst_n', 'clk'):
                if p not in pins:
                    raise GeometryError(f'hbfd_rrl_{kind}: missing LEF pin {p}')
        self.radius = max(max(w / 2 + h / 2, *(md((w / 2, h / 2), xy) for xy in pins.values()))
                          for w, h, pins in self.relay.values())
        self.budget = reach - 2 * self.radius - 2 * GRID
        if self.budget < 6 * GRID:
            raise GeometryError('reach too small for relay outlines and conservative grid budget')
        obstacles = []
        for n, v in self.pl.items():
            o = v.get('o', 'R0')
            if o not in ('R0', 'MX', 'MY', 'R180'):
                raise GeometryError(f'{n}: unsupported placement orientation {o}')
            obstacles.append((v['x'], v['y'], v['x'] + v['w'], v['y'] + v['h']))
        self.half_w = max(w / 2 for w, _, _ in self.relay.values())
        self.half_h = max(h / 2 for _, h, _ in self.relay.values())
        self.grid = Grid(self.W, self.H, [])
        for rect in obstacles:
            self.block_rect(*rect)
        for j in range(self.grid.ny):
            for i in range(self.grid.nx):
                x, y = self.grid.xy((i, j))
                if x < self.half_w or y < self.half_h or x + self.half_w > self.W or y + self.half_h > self.H:
                    self.grid.blk[j * self.grid.nx + i] = 1

    def block_rect(self, x0, y0, x1, y1):
        # Mark centers whose complete largest-relay rectangle intersects the
        # obstacle. Whole-cell rasterization would erase legal 20 um channels.
        lo_x, hi_x = x0 - self.half_w, x1 + self.half_w
        lo_y, hi_y = y0 - self.half_h, y1 + self.half_h
        i0 = max(0, int(math.floor(lo_x / GRID - .5)) + 1)
        i1 = min(self.grid.nx, int(math.ceil(hi_x / GRID - .5)))
        j0 = max(0, int(math.floor(lo_y / GRID - .5)) + 1)
        j1 = min(self.grid.ny, int(math.ceil(hi_y / GRID - .5)))
        if i1 <= i0 or j1 <= j0:
            return
        for j in range(j0, j1):
            self.grid.blk[j * self.grid.nx + i0:j * self.grid.nx + i1] = b'\x01' * (i1 - i0)

    def lef(self, master, directory):
        path = directory / (master + '.lef')
        key = str(path)
        if key not in self.cache:
            if not path.is_file():
                raise GeometryError(f'missing actual LEF: {path}')
            data = path.read_text()
            m = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', data)
            if not m:
                raise GeometryError(f'no SIZE in {path}')
            if re.search(r'\bORIGIN\s+(?!0(?:\.0*)?\s+0(?:\.0*)?\s*;)', data):
                raise GeometryError(f'nonzero LEF ORIGIN unsupported: {path}')
            w, h = map(float, m.groups())
            if min(w, h) <= 0:
                raise GeometryError(f'nonpositive LEF size: {path}')
            pins = lef_xy(path)
            self.cache[key] = (w, h, pins)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            expected = self.expected_hashes.get(path.name)
            if expected is not None and digest != expected:
                raise GeometryError(f'LEF bytes differ from placement manifest: {path}')
            self.hashes[str(path.resolve())] = digest
        return self.cache[key]

    def pin(self, name, port, bit=0, bits=1):
        if name not in self.pl:
            raise GeometryError(f'unplaced reset endpoint {name}.{port}')
        v = self.pl[name]
        master = v.get('m') or v.get('master')
        if not master:
            raise GeometryError(f'{name}: placement does not identify consumed LEF master')
        w, h, pins = self.lef(master, self.views)
        if abs(w - v['w']) > .001 or abs(h - v['h']) > .001:
            raise GeometryError(f'{name}: placed outline differs from actual LEF {master}')
        p = f'{port}[{bit}]' if bits > 1 else port
        if p not in pins:
            raise GeometryError(f'missing actual placed reset pin {name}.{p} ({master})')
        x, y = pins[p]
        if v.get('o', 'R0') in ('MY', 'R180'):
            x = w - x
        if v.get('o', 'R0') in ('MX', 'R180'):
            y = h - y
        xy = (v['x'] + x, v['y'] + y)
        if not (0 <= xy[0] <= self.W and 0 <= xy[1] <= self.H):
            raise GeometryError(f'reset pin outside die: {name}.{p}')
        for other, q in self.pl.items():
            if other != name and q['x'] + .5 < xy[0] < q['x'] + q['w'] - .5 and q['y'] + .5 < xy[1] < q['y'] + q['h'] - .5:
                raise GeometryError(f'buried reset pin {name}.{p} under {other}')
        return xy

    def centre(self, tile):
        w, h, _ = self.relay[tile['kind']]
        return tile['home'][0] + w / 2, tile['home'][1] + h / 2

    def tile_pin(self, tile, p):
        x, y = self.relay[tile['kind']][2][p]
        return tile['home'][0] + x, tile['home'][1] + y

    def candidates(self, point, max_distance):
        ci, cj = self.grid.cell(*point)
        max_steps = int(math.ceil((max_distance + GRID) / GRID))
        for r in range(max_steps + 1):
            choices = []
            for di in range(-r, r + 1):
                for dj in set((r - abs(di), -(r - abs(di)))):
                    c = ci + di, cj + dj
                    if 0 <= c[0] < self.grid.nx and 0 <= c[1] < self.grid.ny and self.grid.free(c):
                        d = md(point, self.grid.xy(c))
                        if d <= max_distance:
                            choices.append((d, c))
            yield from (c for _, c in sorted(choices))

    def reserve(self, kind, point, targets=(), max_distance=None):
        w, h, pins = self.relay[kind]
        for cell in self.candidates(point, max_distance if max_distance is not None else self.reach):
            cx, cy = self.grid.xy(cell)
            tile = dict(kind=kind, home=(round(cx - w / 2, 6), round(cy - h / 2, 6)))
            if cx - w / 2 < 0 or cy - h / 2 < 0 or cx + w / 2 > self.W or cy + h / 2 > self.H:
                continue
            if any(md(self.tile_pin(tile, p), q) > self.reach for p, q in targets):
                continue
            # Reserve the actual rectangle, including exclusion for the next
            # tile's complete outline. No legalizer relocation is assumed.
            self.block_rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
            self.reserved[len(self.reserved)] = tile
            return tile
        raise GeometryError(f'no legal {kind} home near {point} satisfying reset reach')

    def chain(self, source, target):
        """Return reserved hop tiles excluding the already reserved target.

        Grid routing permits overflight with a STRICT bounded blocked run;
        unlike the clock router, there is no enlarged-run fallback. Greedy
        staging is conservative and refuses a path if it cannot place a stage.
        """
        end = self.tile_pin(target, 'rst_n_in')
        if md(source, end) <= self.reach:
            return []
        out = []
        point = source
        while md(point, end) > self.reach:
            a, b = self.grid.cell(*point), self.grid.cell(*end)
            try:
                # Leave room for the current relay reservation and endpoint
                # pin offsets; never use the clock router's 3x fallback.
                path = self.grid._route(a, b, self.budget - 4 * GRID)
            except SystemExit as e:
                raise GeometryError(f'no reset route within fixed reach: {point} -> {end}') from e
            points = [point] + [self.grid.xy(c) for c in path] + [end]
            run = [0.0]
            for p, q in zip(points, points[1:]):
                run.append(run[-1] + md(p, q))
            options = [i for i in range(1, len(points) - 1)
                       if run[i] <= self.budget and self.grid.free(path[i - 1])]
            if not options:
                raise GeometryError(f'no legal reset relay within routed reach from {point}')
            t = self.reserve('hop', points[options[-1]], max_distance=0)
            out.append(t)
            point = self.tile_pin(t, 'rst_n')
        all_pins = [source] + [self.tile_pin(t, 'rst_n') for t in out]
        inputs = [self.tile_pin(t, 'rst_n_in') for t in out] + [end]
        if any(md(p, q) > self.reach for p, q in zip(all_pins, inputs)):
            raise GeometryError('internal reset hop exceeds reach')
        return out
