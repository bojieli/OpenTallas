"""Remaining measured peak claims for live, explicitly identified external jobs."""
import json
from pathlib import Path


def remaining_bytes(record, proc_root=Path('/proc')):
    record = Path(record)
    if not record.exists():
        return 0
    # Malformed reservation inventory must reject admission, never free capacity.
    jobs = json.loads(record.read_text())
    remaining = 0
    for job in jobs:
        proc = proc_root / str(job['pid'])
        try:
            command = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
            if job['command_match'] not in command:
                continue
            rss_kib = next(int(line.split()[1]) for line in (proc / 'status').read_text().splitlines()
                           if line.startswith('VmRSS:'))
        except (OSError, StopIteration, ValueError):
            continue
        remaining += max(0, int(job['peak_ram_gb'] * 2**30) - rss_kib * 1024)
    return remaining
