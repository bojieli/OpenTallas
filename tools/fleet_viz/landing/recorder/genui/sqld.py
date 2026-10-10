"""Persistent read-only SQLite query server for the BI sandbox (one warm connection per worker thread).
   sqld.py DB PORT   -- clients send a query terminated by NUL to 127.0.0.1:PORT and read the formatted result."""
import sqlite3, socketserver, sys, threading, time
DB, PORT = sys.argv[1], int(sys.argv[2]); local = threading.local()
def conn():
    if not hasattr(local, 'c'):
        c = sqlite3.connect(f'file:{DB}?mode=ro', uri=True, check_same_thread=False)
        for p in ('mmap_size=2000000000', 'cache_size=-1000000', 'temp_store=MEMORY', 'threads=4'): c.execute('PRAGMA ' + p)
        local.c = c
    return local.c
def run(q):
    c = conn(); q = q.strip()
    try:
        if q == '.tables':
            return ''.join(f'{n} {c.execute(f"select count(*) from {n}").fetchone()[0]} rows\n' for (n,) in c.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name"))
        if q.startswith('.schema'):
            a = q.split()[1:]
            return ''.join(s + ';\n' for (s,) in c.execute("select sql from sqlite_master where sql is not null and name not like 'sqlite_%'" + (" and tbl_name=?" if a else ""), a))
        if q.startswith('.indexes'):
            return ''.join(s + ';\n' for (s,) in c.execute("select sql from sqlite_master where type='index' and sql is not null"))
        t0 = time.time(); cur = c.execute(q); rows = cur.fetchmany(201); cols = [d[0] for d in cur.description or []]
        out = ['\t'.join(cols)] + ['\t'.join('' if v is None else (f'{v:.2f}' if isinstance(v, float) else str(v)) for v in r) for r in rows[:200]]
        return '\n'.join(out) + f'\n({len(rows[:200])}{"+" if len(rows) > 200 else ""} rows, {time.time() - t0:.3f} s)\n'
    except sqlite3.Error as e:
        return f'SQL error: {e}\n'
class H(socketserver.StreamRequestHandler):
    def handle(self):
        buf = b''
        while not buf.endswith(b'\0'):
            ch = self.request.recv(65536)
            if not ch: break
            buf += ch
        self.wfile.write(run(buf.rstrip(b'\0').decode()).encode())
class S(socketserver.ThreadingTCPServer): allow_reuse_address = True; daemon_threads = True
S(('127.0.0.1', PORT), H).serve_forever()
