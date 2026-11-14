# SIGNED-RECOVER handoff (11-14 ~09:35 PST)
INDEX: AGI /archive/opentallas-signed-1114/INDEX.tsv (mirror rtx ~/signed-export-1114/INDEX.tsv); 328 rows = 316 explorer-signed + 12 audit-only names. Status: 249 ARCHIVED-BOTH (DB+signoff/manifest+view pack, sha256 equal rtx vs AGI), 69 ARCHIVED-BOTH-NO-VIEWPACK (DB+meta ok; explorer has no layout cut for them, so no pack exists to export; list in scratchpad sr/noviewpack.txt), 3 SHA-DIFFERS-FROM-RECORD (dsdv_gunit_l1f_ba0/ba1, hd_ctl_n: archived file differs from the explorer record's DB; other attempt), 10 NO-DB.
Key finding: audit's LOST rows were found: explorer signed-store records (epyc8 explorer-2-work/signed-store/records) carry size+sha256 and the DBs sit in AGI opentallas-signed-1106; hardlinked into 1114 (no data copy). 36 explorer-signed elements without records exported from live fleet hosts; 6 CA-only from rtx closed_archive; 12 zero-byte .zst dirs refilled from closed_archive.
View packs: AGI+rtx _view-packs/{elements,objects} (1,138,778 files, 4.0 GB, file counts equal).
Still no DB (rebuild): s81_head ot_s81hd_elemA_cv, ot_s81hd_elemB_cv; hbm q_spb1, q_spt2, vsN1 (only NOT SIGNED attempts on fleet); qwen_compute coll_ftm (sign-off is route-only: DB is 5_2_route.odb on epyc2 .../coll_ftm/eco_20261108_052329_1409894/i1, no 6_final.odb); audit-only pseudo names signoff, signoff_eco_*, signoff_s8pin2b (export-dir naming artifacts, their DBs are now under correct names).
Protection: signed-dbs.txt on intel2/intel1/epyc2/7/8/9/10 filtered 321 -> 37 entries (284 verified-in-both removed); backup signed-dbs.txt.bak-signedrecover; clean4-keep-sync.sh restored from .bak-signeddb. The 37 remaining belong to the NO-DB/SHA-differs rows; delete the file when those are resolved.
Not done: resubmission of the 6 lost sign-offs (specs/plan sha not recovered), explorer cuts for the 69 no-view-pack rows.

## ARCHIVE HOW-TO (one signed record -> rtx-pro + AGIdock + INDEX row)
Route used: from rtx-pro (localhost, user ubuntu) over ssh to AGIdock archive-store, user ubuntu, address 155.103.253.53, identity file ~/.ssh/agidock_ot (no ssh alias exists for it; `ssh agidock` does NOT resolve). Fleet hosts have no route to it, so everything is staged on rtx-pro first. Archive root on AGIdock: /archive/opentallas-signed-1114. rtx-pro mirror: /home/ubuntu/signed-export-1114. Same relative layout in both: <die>/<element>/{6_final.odb,6_final.def,6_final.spef,6_final.v,6_final.sdc,signoff.json}; view pack in _view-packs/{elements,objects}; index at INDEX.tsv. Never rsync --delete; never touch other /archive dirs.

    AG="ubuntu@155.103.253.53"; SSH="ssh -i $HOME/.ssh/agidock_ot -o IdentitiesOnly=yes -o ControlPath=none -o BatchMode=yes"
    DIE=qwen_compute; EL=my_element; R=/home/ubuntu/signed-export-1114; K=$DIE/$EL
    # 1. DB + siblings + signoff.json from the fleet host to rtx-pro (run on rtx-pro)
    HOST=epyc2; DBDIR=/srv/.../results/asap7/<design>/base; SIG=/srv/.../signoff/signoff.json
    mkdir -p $R/$K
    rsync -a -e "ssh -o ControlPath=none" --include='6_final.odb' --include='6_final.def' --include='6_final.spef' --include='6_final.v' --include='6_final.sdc' --exclude='*' $HOST:$DBDIR/ $R/$K/
    rsync -a -e "ssh -o ControlPath=none" $HOST:$SIG $R/$K/signoff.json
    # 2. push to AGIdock (same relative path)
    rsync -a -R -e "$SSH" $R/./$K/ $AG:/archive/opentallas-signed-1114/
    # 3. view pack: job json + index.json + every object the job lists, from the explorer store on epyc8
    #    NODE = explorer node (e.g. qwen_compute.c.my_element), JOB = job file name under store/elements/NODE/
    ST=/srv/opentallas-scratch2/claude/explorer-2-work/store
    ssh -n -o ControlPath=none epyc8 "cd $ST && python3 -I -c \"import json,sys;j=json.load(open('elements/$NODE/$JOB'));f=['elements/$NODE/$JOB','elements/$NODE/index.json']
    def w(o):
        for v in o.values():
            (w(v) if isinstance(v,dict) else f.append('objects/%s/%s.br'%(v[:2],v)))
    w(j['objects']);print('\n'.join(f))\"" > /tmp/pack_$EL.txt
    ssh -o ControlPath=none epyc8 "cd $ST && tar cf - --files-from=- --no-recursion" < /tmp/pack_$EL.txt | tar xf - -C $R/_view-packs
    tar cf - -C $R/_view-packs --files-from=/tmp/pack_$EL.txt --no-recursion | $SSH $AG 'tar xf - --skip-old-files -C /archive/opentallas-signed-1114/_view-packs'
    # 4. verify size+sha256 on both sides, then append the INDEX row on both
    (cd $R && sha256sum $K/6_final.odb $K/signoff.json); $SSH $AG "cd /archive/opentallas-signed-1114 && sha256sum $K/6_final.odb $K/signoff.json"
    SHA=$(sha256sum $R/$K/6_final.odb | cut -d' ' -f1); SZ=$(stat -c %s $R/$K/6_final.odb)
    ROW="$DIE\t$EL\t<type|core>\t<record id or empty>\t/archive/opentallas-signed-1114/$K/6_final.odb\t$R/$K/6_final.odb\t$SZ\t$SHA\t_view-packs/elements/$NODE/$JOB\t/archive/opentallas-signed-1114/$K/signoff.json\tARCHIVED-BOTH\tlane"
    printf "$ROW\n" >> $R/INDEX.tsv; printf "$ROW\n" | $SSH $AG 'cat >> /archive/opentallas-signed-1114/INDEX.tsv'
Columns of INDEX.tsv: die, element, kind, record, db (AGI path), rtx_db, size, sha256, pack, meta, status, src. Use a single writer at a time for INDEX.tsv (append, never rewrite). Notes: a DB already sitting in /archive/opentallas-signed-1106 can be hardlinked server-side instead of copied: `$SSH $AG 'mkdir -p /archive/opentallas-signed-1114/K && ln -f /archive/opentallas-signed-1106/<host>/<path>/6_final.odb /archive/opentallas-signed-1114/K/'` (same filesystem, instant). Parallel ssh above ~8 sessions to AGIdock gets connection resets; keep <=3 for tar streams. AGIdock disk is ~100 MB/s, large DBs are I/O bound.
