"""Construct registered relay paths around real obstacles without monotonicity.

Each accepted hop has a collision-free orthogonal wire of at most the supplied
pin budget. This is necessary geometry, not routed/native timing qualification.
The search returns its actual stages and wire witnesses; it never relaxes reach.
"""
import heapq
import itertools
import math


def route(source, target, obstacles, outline, width, height, grid, reach,
          first_reach=None, gap=4.32, body_obstacles=None):
    first_reach = reach if first_reach is None else first_reach
    eps = 1e-6
    cell = max(grid, width, height)
    def spatial(rectangles):
        index={}
        for number, rect in enumerate(rectangles):
            for x in range(math.floor(rect[0]/cell),math.floor(rect[2]/cell)+1):
                for y in range(math.floor(rect[1]/cell),math.floor(rect[3]/cell)+1):
                    index.setdefault((x,y),set()).add(number)
        def query(rect):
            result=set()
            for x in range(math.floor(rect[0]/cell),math.floor(rect[2]/cell)+1):
                for y in range(math.floor(rect[1]/cell),math.floor(rect[3]/cell)+1):
                    result.update(index.get((x,y),()))
            return (rectangles[i]for i in result)
        return query
    nearby=spatial(obstacles)
    body_nearby=nearby if body_obstacles is None else spatial(body_obstacles)

    def intersects(a,b):
        return min(a[2],b[2])-max(a[0],b[0])>eps and min(a[3],b[3])-max(a[1],b[1])>eps

    def wire(a,b,extra=()):
        for corner in ((b[0],a[1]),(a[0],b[1])):
            points=(a,corner,b)
            clear=True
            for p,q in zip(points,points[1:]):
                # A zero-width segment crosses a rectangle only in its interior.
                box=(min(p[0],q[0])-eps,min(p[1],q[1])-eps,
                     max(p[0],q[0])+eps,max(p[1],q[1])+eps)
                for r in itertools.chain(nearby(box),extra):
                    if p[0]==q[0]:
                        blocked=r[0]+eps<p[0]<r[2]-eps and min(box[3],r[3])-max(box[1],r[1])>2*eps
                    else:
                        blocked=r[1]+eps<p[1]<r[3]-eps and min(box[2],r[2])-max(box[0],r[0])>2*eps
                    if blocked:
                        clear=False;break
                if not clear:break
            if clear:return points
        return None

    free_cache = {}
    def rect(node):
        x,y,_=node
        return (x*grid,y*grid,x*grid+width,y*grid+height)
    def free(node):
        key=node[:2]
        if key not in free_cache:
            r=rect(node);expanded=(r[0]-gap,r[1]-gap,r[2]+gap,r[3]+gap)
            free_cache[key]=(expanded[0]>=0 and expanded[1]>=0 and
                expanded[2]<=outline[0] and expanded[3]<=outline[1] and
                not any(intersects(expanded,b)for b in body_nearby(expanded)))
        return free_cache[key]
    def pins(node):
        r=rect(node);y=(r[1]+r[3])/2
        return ((r[0],y),(r[2],y)) if node[2]==0 else ((r[2],y),(r[0],y))
    dist=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
    radius=math.ceil((max(reach,first_reach)+width+height)/grid)
    offsets=[(x,y)for x in range(-radius,radius+1)for y in range(-radius,radius+1)
             if (abs(x)+abs(y))*grid<=max(reach,first_reach)+width+height]
    queue=[];serial=itertools.count();best={};parents={};wires={}
    def add(node,parent,stages,length,path):
        score=(stages,length)
        if score>=best.get(node,(math.inf,math.inf)):return
        best[node]=score;parents[node]=parent;wires[node]=path
        remaining=dist(pins(node)[1],target)
        heapq.heappush(queue,(stages+remaining/reach,remaining,next(serial),node,score))
    def choices(point,cap):
        bx,by=round(point[0]/grid),round(point[1]/grid)
        for dx,dy in offsets:
            for orientation in (0,1):
                node=(bx+dx,by+dy,orientation)
                if not free(node):continue
                pin,_=pins(node)
                length=dist(point,pin)
                if length<=cap+eps:yield node,pin,length
    for node,pin,length in choices(source,first_reach):
        path=wire(source,pin,(rect(node),))
        if path:add(node,None,1,length,path)
    expanded=0
    while queue:
        _,_,_,node,score=heapq.heappop(queue)
        if best[node]!=score:continue
        expanded+=1
        point=pins(node)[1]
        ancestors=[];cursor=node
        while cursor is not None:
            ancestors.append(rect(cursor));cursor=parents[cursor]
        tail=wire(point,target,ancestors)if dist(point,target)<=reach+eps else None
        if tail:
            chain=[];cursor=node
            while cursor is not None:
                r=rect(cursor)
                chain.append(dict(x=r[0],y=r[1],orient='R0'if cursor[2]==0 else'MY',
                    input=pins(cursor)[0],output=pins(cursor)[1],wire=list(wires[cursor])))
                cursor=parents[cursor]
            chain.reverse()
            return dict(stages=chain,tail_wire=list(tail),expanded=expanded,
                algorithm='obstacle-aware constructive search; no minimum-stage claim')
        for nxt,pin,length in choices(point,reach):
            r=rect(nxt);larger=(r[0]-gap,r[1]-gap,r[2]+gap,r[3]+gap)
            if any(intersects(larger,a)for a in ancestors):continue
            if (score[0]+1,score[1]+length)>=best.get(nxt,(math.inf,math.inf)):continue
            path=wire(point,pin,ancestors+[r])
            if path:add(nxt,node,score[0]+1,score[1]+length,path)
    return None
