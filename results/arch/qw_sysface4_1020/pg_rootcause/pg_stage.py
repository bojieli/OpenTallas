import odb,sys,collections,re
for path in sys.argv[1:]:
    db=odb.dbDatabase.create(); odb.read_db(db,path); b=db.getChip().getBlock()
    tot=unb=0; inst_unb=collections.Counter(); dnt=0; names=[]
    for i in b.getInsts():
        u=False
        for mt in i.getMaster().getMTerms():
            if str(mt.getSigType()) not in ('POWER','GROUND'): continue
            tot+=1
            t=i.findITerm(mt.getName())
            if t is None or t.getNet() is None:
                unb+=1; u=True
        if u:
            inst_unb[re.sub(r'\d+','N',i.getName().split('/')[0].split('.')[0])]+=1
            if i.isDoNotTouch(): dnt+=1
            if len(names)<8: names.append((i.getName(),i.getMaster().getName(),str(i.getPlacementStatus())))
    gcs=[(g.getInstPattern(),g.getPinPattern(),g.getNet().getName()) for g in b.getGlobalConnects()]
    print(path.split('/')[-1],'pg_mterms',tot,'unbound',unb,'dnt_unbound_insts',dnt,inst_unb.most_common(8),'gc_rules',gcs,names,flush=True)
