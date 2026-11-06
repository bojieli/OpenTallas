"""Strict ownership of a registered output's optional local state feedback."""

def check(F, root, port, drivers, loads, roots_ports, is_ff, is_buf, is_std):
    """Return (failure, FF index). Extra Q loads may end ONLY at this FF's D.

    No port, macro, other state element, clock/reset/enable pin or dead/cyclic
    cone is accepted. The ordinary output chain remains private buffers only.
    """
    cur=root;chain={};seen=set()
    while True:
        if cur in seen:return 'cycle before output register',None
        seen.add(cur)
        if roots_ports.get(cur,[]) != ([port] if cur==root else []):
            return 'output chain aliases another port',None
        if len(drivers[cur])!=1:return 'output chain does not have exactly one driver',None
        ci,pin=drivers[cur][0];master,path,pp=F.cells[ci]
        if is_ff(master):
            outs=[(p,v) for p,(d,v) in pp.items() if d=='out' and v]
            if pin not in ('Q','QN') or len(outs)!=1 or len(outs[0][1])!=1:
                return 'output needs one scalar register state pin',None
            owner=ci;break
        ins=[(p,v) for p,(d,v) in pp.items() if d=='in' and v]
        outs=[v for p,(d,v) in pp.items() if d=='out' and v]
        if not is_buf(master) or len(ins)!=1 or len(ins[0][1])!=1 or len(outs)!=1 or len(outs[0])!=1:
            return 'output is not a private buffer chain from a register',None
        p,v=ins[0];up=F.find(v[0]);chain.setdefault(up,set()).add((ci,p));cur=up
    feedback=0
    def follow(ci,pin,active):
        nonlocal feedback
        master,path,pp=F.cells[ci]
        if is_ff(master):
            if ci==owner and pin=='D':feedback+=1;return None
            return 'feedback reaches another register or non-D state pin'
        if not is_std(master):return 'feedback reaches a macro'
        if ci in active:return 'combinational feedback cycle'
        outs=[F.find(b) for p,(d,v) in pp.items() if d=='out' for b in v]
        if not outs:return 'feedback cell has no output'
        for n in outs:
            if roots_ports.get(n):return 'feedback reaches a port'
            if not loads[n]:return 'feedback has a non-owner dead leaf'
            for cj,pj in loads[n]:
                why=follow(cj,pj,active|{ci})
                if why:return why
        return None
    for n in seen:
        for ci,pin in loads[n]:
            if (ci,pin) in chain.get(n,set()):continue
            why=follow(ci,pin,set())
            if why:return why,None
    return None,owner
