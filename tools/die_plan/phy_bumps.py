"""Dedicated PHY supply bump sites, optionally anchored to an existing lattice."""
import math


def sites(domain):
    """Return local (net, x, y) sites; explicit origins are in die coordinates.

    Without origin_um/counts the historical rectangle-centred lattice is exact.
    An anchored lattice never recentres, drops sites, or changes its net parity.
    """
    cfg = domain['bumps']
    rect = cfg['rect_um']
    pitch = cfg['pitch_um']
    dx, dy, ex, ey = domain['rect_um']
    power, ground = domain['nets']
    anchored = 'origin_um' in cfg or 'counts' in cfg
    if anchored:
        origin, counts = cfg.get('origin_um'), cfg.get('counts')
        if (not isinstance(origin, list) or len(origin) != 2
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in origin)
                or not isinstance(counts, list) or len(counts) != 2
                or any(type(v) is not int or v < 1 for v in counts)
                or isinstance(pitch, bool) or not isinstance(pitch, (int, float))
                or not math.isfinite(pitch) or pitch <= 0):
            raise ValueError('anchored PHY bumps require finite origin_um, two positive integer counts and positive pitch_um')
        nx, ny = counts
        ox, oy = origin
        if any(abs(v*1000-round(v*1000)) > 1e-6 for v in (ox,oy,pitch)):
            raise ValueError('anchored PHY bump coordinates/pitch must survive native 0.001um emission exactly')
        lastx, lasty = ox + (nx-1)*pitch, oy + (ny-1)*pitch
        if not (rect[0] <= ox <= lastx <= rect[2] and rect[1] <= oy <= lasty <= rect[3]
                and dx <= ox <= lastx <= ex and dy <= oy <= lasty <= ey):
            raise ValueError('anchored PHY bump sites exceed the declared bump rectangle or supply domain')
        for i in range(nx):
            for j in range(ny):
                x, y = ox+i*pitch, oy+j*pitch
                if any(a <= x <= c and b <= y <= d for a,b,c,d in cfg.get('exclude_um', [])):
                    raise ValueError('anchored PHY bump site intersects an explicit exclusion')
        sx, sy = ox-dx, oy-dy
    else:
        nx, ny = int((rect[2]-rect[0])//pitch), int((rect[3]-rect[1])//pitch)
        if min(nx,ny) < 1:
            raise ValueError('declared PHY bump rectangle has no complete row')
        sx = (rect[0]+rect[2]-(nx-1)*pitch)/2-dx
        sy = (rect[1]+rect[3]-(ny-1)*pitch)/2-dy
    return [(power if (i+j)%2 == 0 else ground, round(sx+i*pitch,3), round(sy+j*pitch,3))
            for i in range(nx) for j in range(ny)]
