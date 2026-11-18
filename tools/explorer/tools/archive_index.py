#!/usr/bin/env python3
"""Index of the signed-layout archives on the archive host (rtx-pro), for the explorer.

    python3 -I archive_index.py [--export /home/ubuntu/signed-export-1114] [--closed /home/ubuntu/closed_archive] > archive_index.json

Lists, without reading any design data: signed-export-1114/<die>/<name>/ (files, sizes, signoff.json) and the rows of
closed_archive/INDEX.json (element, job, final DB).  The explorer service (another host) loads the JSON and shows, for
every design, where its signed database lives now; it never opens the databases themselves.
"""
import argparse, json, os, socket, sys, time


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--export', default='/home/ubuntu/signed-export-1114'); ap.add_argument('--closed', default='/home/ubuntu/closed_archive')
    ap.add_argument('--host', default='rtx-pro')
    ap.add_argument('--agidock', default='ubuntu@155.103.253.53'); ap.add_argument('--agiroot', default='/archive/opentallas-signed-1114'); ap.add_argument('--key', default='~/.ssh/agidock_ot')
    a = ap.parse_args()
    out = dict(schema='opentallas.explorer.archive_index.v1', generated=time.time(), host=a.host, hostname=socket.gethostname(), roots=dict(export=a.export, closed=a.closed), export=[], closed=[])
    if os.path.isdir(a.export):
        for die in sorted(os.listdir(a.export)):
            dd = os.path.join(a.export, die)
            if not os.path.isdir(dd): continue
            for name in sorted(os.listdir(dd)):
                p = os.path.join(dd, name)
                if not os.path.isdir(p): continue
                files = {}
                for root, _, fs in os.walk(p):
                    for f in fs:
                        try: files[os.path.relpath(os.path.join(root, f), p)] = os.path.getsize(os.path.join(root, f))
                        except OSError: pass
                    if len(files) > 400: break
                odb = next((f for f in files if f.endswith('6_final.odb') or f.endswith('6_final.odb.zst')), None)
                rec = dict(die=die, name=name, path=p, odb=odb, signoff='signoff.json' in files or any(f.endswith('/signoff.json') for f in files),
                           bytes=sum(files.values()), files=sorted(files)[:40], mtime=os.path.getmtime(p))
                sj = os.path.join(p, 'signoff.json')
                if os.path.isfile(sj) and os.path.getsize(sj) < 4e6:
                    try:
                        s = json.load(open(sj)); rec['design'] = s.get('design') or s.get('name') or s.get('top'); rec['verdict'] = s.get('verdict')
                    except Exception: pass
                out['export'].append(rec)
    ix = os.path.join(a.closed, 'INDEX.json')
    if os.path.isfile(ix):
        try:
            d = json.load(open(ix))
            for r in d.get('rows') or []:
                fin = r.get('final') or {}
                base = os.path.join(a.closed, r.get('dir') or ''); odb = fin.get('final_odb')
                # REMOTE_ONLY jobs keep only links here: the heavy files are on the remote archive (AGIdock)
                present = bool(odb) and os.path.exists(os.path.join(base, odb))
                out['closed'].append(dict(name=r.get('element') or r.get('block'), job=r.get('job'), status=r.get('status'), path=base, odb=odb, present=present,
                                          remote_only=bool(odb) and not present and os.path.exists(os.path.join(base, 'REMOTE_ONLY.json')), from_host=r.get('host')))
            out['closed_generated'] = d.get('generated_at')
        except Exception as e:
            out['closed_error'] = str(e)
    # INGEST-FIX 11-17: _view-packs/objects holds 2.3M files; listing it made the JSON 180 MB and the 60 s scp to the hub failed (listing stale 6 h): pruned.
    # AGIdock /archive/opentallas-signed-1114: the archive of record for the count (owner 2026-11-14).  Listing + INDEX.tsv only.
    if a.agidock:
        import subprocess
        ssh = ['ssh', '-n', '-i', os.path.expanduser(a.key), '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ControlPath=none', a.agidock]
        try:
            cmd = "cd " + a.agiroot + " && find . -maxdepth 4 -path ./_view-packs/objects -prune -o -type f -printf '%P|%s\\n'; echo ---INDEX---; cat INDEX.tsv 2>/dev/null; true"
            r = subprocess.run(ssh + [cmd], capture_output=True, text=True, timeout=300)
            if r.returncode: raise RuntimeError(r.stderr.strip()[-200:])
            listing, _, index = r.stdout.partition('---INDEX---\n'); ent = {}
            for ln in listing.splitlines():
                f, _, sz = ln.rpartition('|'); parts = f.split('/')
                if len(parts) >= 3: ent.setdefault((parts[0], parts[1]), {})['/'.join(parts[2:])] = int(sz or 0)
            out['agidock'] = [dict(die=d, name=n, path='%s/%s/%s' % (a.agiroot, d, n), files=fs) for (d, n), fs in sorted(ent.items())]
            out['agidock_index_tsv'] = index if index.strip() else None; out['agidock_root'] = a.agiroot; out['agidock_listed'] = time.time()
        except Exception as e:
            out['agidock_error'] = '%s: %s' % (type(e).__name__, e)
    json.dump(out, sys.stdout, separators=(',', ':'))


if __name__ == '__main__':
    main()
