#!/usr/bin/env python3
"""Install the Verilator build -j cap (VL_JCAP_1022) on a fleet host.  Run as root ON the host, ot-vl-jcap alongside:
    sudo python3 install_vl_jcap.py [path/to/ot-vl-jcap]
Installs /usr/local/bin/ot-vl-jcap, the make shim /usr/local/lib/ot-heavy/vljcap/make -> it, and a 5-line block in
/usr/local/bin/ot-heavy (before its docker-shim PATH line) that evals `ot-vl-jcap --env MEM -- CMD` at launch.
Idempotent; every file is replaced atomically (new inode), so running ot-heavy waiters and jobs keep their old copy;
backup in /var/tmp/ot-heavy/vl-jcap-backup-<stamp>.  Never stops jobs.  Rollback: copy the backup ot-heavy back.
"""
import os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

MARK = "VL_JCAP_1022"
HEAVY = "/usr/local/bin/ot-heavy"
JCAP = "/usr/local/bin/ot-vl-jcap"
SHIM_DIR = "/usr/local/lib/ot-heavy/vljcap"
ANCHOR = "    [ -x /usr/local/lib/ot-heavy/bin/docker ] && export PATH="
BLOCK = (
    "    # " + MARK + " (fleet 2026-10-22: ep5 / filled by OOM dumps): Verilator C++ builds peak ~30 GB per cc1plus, so\n"
    "    # every Verilator make in this job runs at most floor(MEM / per-cc1plus GB) jobs (ot-vl-jcap). OT_VL_JCAP=0 opts out.\n"
    "    if [ \"${OT_VL_JCAP:-1}\" != 0 ] && [ -x /usr/local/bin/ot-vl-jcap ]; then\n"
    "      _jc=$(timeout 20 /usr/local/bin/ot-vl-jcap --env \"$MEM\" -- \"$@\") && eval \"$_jc\"; unset _jc\n"
    "    fi\n")


def patch_heavy(s):
    if MARK in s:
        return s
    if s.count(ANCHOR) != 1:
        raise ValueError("unknown ot-heavy layout (docker PATH anchor)")
    return s.replace(ANCHOR, BLOCK + ANCHOR)


def atomic_write(dst, data, mode=0o755):
    d = os.path.dirname(dst)
    fd, tmp = tempfile.mkstemp(dir=d, prefix="." + os.path.basename(dst) + ".")
    with os.fdopen(fd, "w") as f:
        f.write(data)
    os.chmod(tmp, mode)
    os.replace(tmp, dst)


def main():
    if os.geteuid() != 0:
        raise SystemExit("root required")
    src = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("ot-vl-jcap"))
    heavy = Path(HEAVY).read_text()
    new_heavy = patch_heavy(heavy)
    tmp = tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False)
    tmp.write(new_heavy); tmp.close()
    if subprocess.run(["bash", "-n", tmp.name]).returncode:
        raise SystemExit("patched ot-heavy fails bash -n; nothing installed")
    os.unlink(tmp.name)
    r = subprocess.run([sys.executable, str(src), "--selftest"], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("ot-vl-jcap selftest failed; nothing installed\n" + r.stdout)
    bk = Path("/var/tmp/ot-heavy/vl-jcap-backup-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    bk.mkdir(parents=True)
    shutil.copy2(HEAVY, bk / "ot-heavy")
    if os.path.exists(JCAP):
        shutil.copy2(JCAP, bk / "ot-vl-jcap")
    atomic_write(JCAP, src.read_text())
    os.makedirs(SHIM_DIR, exist_ok=True)
    link = os.path.join(SHIM_DIR, "make")
    if os.path.realpath(link) != JCAP:
        tl = link + ".new"
        if os.path.lexists(tl):
            os.unlink(tl)
        os.symlink(JCAP, tl)
        os.replace(tl, link)
    if new_heavy != heavy:
        atomic_write(HEAVY, new_heavy, os.stat(HEAVY).st_mode & 0o7777)
    print(f"VL_JCAP_OK {os.uname().nodename} heavy={'patched' if new_heavy != heavy else 'already'} backup={bk} "
          f"selftest={r.stdout.strip()}")


if __name__ == "__main__":
    main()
