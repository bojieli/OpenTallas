"""Allocate distinct physical sites for the HBM die clock repeater network.

The route-grid tree specifies electrical topology, not legal cell sites: delay
padding can put hundreds of cells at one coordinate. Reserve sites jointly
across all domains before emitting placement. Timing must be remeasured after
this operation; the original analytical insertion is only a topology estimate.
"""
import heapq

from die_clock_tree import Grid, GRID

# Pinned asap7sc7p5t_28_R_1x_220121a.lef: both cells are CORE,
# asap7sc7p5t site, height .27; widths are 30 and 18 .054-um sites.
SIZES = {'BUFx24_ASAP7_75t_R': (1.620, 0.270),
         'BUFx12f_ASAP7_75t_R': (0.972, 0.270)}
XPITCH, YPITCH = 1.620, 0.270


def orientation(y):
    """Pinned initialize_floorplan rows start R0 at y=0, alternate MX/R0."""
    row = round(y / YPITCH)
    if abs(y - row * YPITCH) > 1e-6:
        raise ValueError(f'Clock cell is not on the .270-um row lattice: {y}')
    return 'R0' if row % 2 == 0 else 'MX'



def allocate(trees, width, height, obstacles):
    """Mutate only buffer coordinates; preserve all cells, names and nets.

    A whole 1.62 x .27 site is reserved even for the narrower pad. The conservative
    10-um obstacle grid leaves the complete cell rectangle outside hard blocks.
    The nearest available site is chosen by physical Manhattan displacement.
    Fail rather than silently place a cell in a block or outside the die.
    """
    grid = Grid(width, height, obstacles)
    occupied = set()
    nx, ny = int(width / XPITCH), int(height / YPITCH)
    for domain, tree in sorted(trees.items()):
        placed, displacements = [], []
        for name, cell, oldx, oldy in tree['buffers']:
            if cell not in SIZES:
                raise ValueError(f'Unmeasured clock cell dimensions: {cell}')
            start = (min(nx - 1, max(0, round(oldx / XPITCH))),
                     min(ny - 1, max(0, round(oldy / YPITCH))))
            queue, visited = [(0.0, *start)], {start}
            while queue:
                _, ix, iy = heapq.heappop(queue)
                x, y = ix * XPITCH, iy * YPITCH
                # Reserve the complete maximum-width site across every domain.
                ci0, cj0 = int(x / GRID), int(y / GRID)
                ci1 = int((x + XPITCH - 1e-9) / GRID)
                cj1 = int((y + YPITCH - 1e-9) / GRID)
                legal = ((ix, iy) not in occupied and x + XPITCH <= width
                         and y + YPITCH <= height and
                         all(0 <= ci < grid.nx and 0 <= cj < grid.ny and grid.free((ci, cj))
                             for ci in range(ci0, ci1 + 1) for cj in range(cj0, cj1 + 1)))
                if legal:
                    occupied.add((ix, iy))
                    placed.append((name, cell, round(x, 3), round(y, 3)))
                    displacements.append(abs(x - oldx) + abs(y - oldy))
                    break
                for ni, nj in ((ix - 1, iy), (ix + 1, iy), (ix, iy - 1), (ix, iy + 1)):
                    if 0 <= ni < nx and 0 <= nj < ny and (ni, nj) not in visited:
                        visited.add((ni, nj))
                        heapq.heappush(queue, (abs(ni * XPITCH - oldx) + abs(nj * YPITCH - oldy), ni, nj))
            else:
                raise ValueError(f'No legal die clock site for {domain}:{name}')
        tree['buffers'] = placed
        tree['model']['site_allocation'] = dict(
            cells=len(placed), max_displacement_um=round(max(displacements, default=0), 3),
            mean_displacement_um=round(sum(displacements) / max(1, len(placed)), 3),
            reserved_site_um=[XPITCH, YPITCH], overlap=0,
            basis='asap7sc7p5t_28_R_1x_220121a.lef; complete cell outside conservative hard-block grid',
            timing='Topology insertion estimate predates site allocation; actual propagated STA required')
