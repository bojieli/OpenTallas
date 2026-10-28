import openroad, odb
from openroad import Design, Tech
t=Tech(); d=Design(t); d.readDb("/base/6_final.odb")
blk=d.getBlock()
for nn in ["clk_tb0_tree","clknet_0_clk_regs","delaynet_1_clk"]:
    net=blk.findNet(nn); w=net.getWire()
    dec=odb.dbWireDecoder(); dec.begin(w)
    segs={}; prev=None; lay=None; tot=0
    while True:
        op=dec.next()
        if op==odb.dbWireDecoder.END_DECODE: break
        if op in (odb.dbWireDecoder.PATH, odb.dbWireDecoder.JUNCTION, odb.dbWireDecoder.SHORT, odb.dbWireDecoder.VWIRE):
            lay=dec.getLayer().getName(); prev=None
            if op==odb.dbWireDecoder.JUNCTION: prev=None
        if op in (odb.dbWireDecoder.POINT, odb.dbWireDecoder.POINT_EXT):
            p=dec.getPoint()[:2]
            if prev is not None:
                L=abs(p[0]-prev[0])+abs(p[1]-prev[1]); segs[lay]=segs.get(lay,0)+L/1000; tot+=L/1000
            prev=p
        if op==odb.dbWireDecoder.VIA or op==odb.dbWireDecoder.TECH_VIA:
            lay=None if dec.getVia() is None else lay
    print("WSEG",nn,round(tot,1),{k:round(v,1) for k,v in segs.items()})
