"""Actual OpenDB master geometry transformed by its instance origin/orientation."""
def transformed_rect(inst, shape):
    signs={"R0":(1,1),"MX":(1,-1),"MY":(-1,1),"R180":(-1,-1)}
    orient=str(inst.getOrient())
    if orient not in signs:raise ValueError("unsupported orientation: "+orient)
    sx,sy=signs[orient];ox,oy=inst.getOrigin()
    xs=sorted((ox+sx*shape.xMin(),ox+sx*shape.xMax()))
    ys=sorted((oy+sy*shape.yMin(),oy+sy*shape.yMax()))
    return [xs[0],ys[0],xs[1],ys[1]]
