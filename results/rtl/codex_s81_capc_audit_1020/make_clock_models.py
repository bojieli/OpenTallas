"""Make bounded diagnostic COPIES of a native ODB; never edits the gate ODB.

Reattach the RT leaf to one of its existing upstream taps; bypass 1..3
existing LD pads. The next source gate must independently rebuild/qualify it.
"""
import odb,sys,json,hashlib
from pathlib import Path
src=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=True);manifest=[]
variants = [(3,4),(3,5)] if len(sys.argv)>3 and sys.argv[3]=='finish_ld' else [(0,0)]+[(u,p) for u in [1,2,3] for p in [1,2,3]]
for up,pads in variants:
    db=odb.dbDatabase.create();odb.read_db(db,str(src));b=db.getChip().getBlock();changes=[]
    ld_tap=f'clkbuf_sp_L1_p{5-pads}_net' if pads<5 else 'clkbuf_sp_N36_net'
    for leaf,tap in ([('clkbuf_sp_L4',f'clkbuf_sp_N{35+up}_net'),('clkbuf_sp_L1',ld_tap)] if up else []):
        i=b.findInst(leaf);p=i.findITerm('A');old=p.getNet().getName();n=b.findNet(tap)
        assert n and old!=tap
        oldnet=p.getNet()
        # All three are protected clock objects in the original. Temporarily
        # unprotect ONLY this diagnostic copy, reattach, then restore protection.
        i.setDoNotTouch(False);oldnet.setDoNotTouch(False);n.setDoNotTouch(False)
        p.disconnect();p.connect(n)
        i.setDoNotTouch(True);oldnet.setDoNotTouch(True);n.setDoNotTouch(True)
        changes.append({'pin':leaf+'/A','old_net':old,'new_net':tap,'protected_after_reconnect':True})
    dst=out/f'rt{up}_ld{pads}.odb';odb.write_db(db,str(dst));manifest.append({'odb':dst.name,'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'changes':changes})
(out/'manifest.json').write_text(json.dumps({'kind':'diagnostic copy, no gate qualification','original_odb_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'variants':manifest},indent=2)+'\n')
