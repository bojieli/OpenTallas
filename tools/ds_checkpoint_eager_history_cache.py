"""Price eager History/LockedArray reads from enrolled metadata, never payload.

This is an input to physical admission, not an admission verdict. Source RAM,
allocator pages, output cache, kernel and peer reserves remain separate. The
old constructor and checkpoint guards are unchanged.
"""
import math


def eager_history_cache(manifest, inventory, *, page_bytes):
    """Inventory rows use the fstat stamp which LockedArray.check enforces.

    Full file pages are charged because LockedArray.__init__ preads to EOF.
    Same-inode aliases count once only with identical size/hash/full stamp.
    Distinct inodes with identical contents still count separately. No existing
    residency, cache eviction, KSM or cross-process page reuse is credited.
    """
    if type(page_bytes) is not int or page_bytes <= 0 or page_bytes & (page_bytes - 1):
        raise ValueError('explicit positive power-of-two host page size required')
    records = manifest['history_images']
    if not records:
        raise ValueError('actual eager history records required')
    unique = {}
    paths = set()
    payload_total = 0
    for record in records:
        path = record['path']
        if path in paths:
            raise ValueError('duplicate history source path')
        paths.add(path)
        if record['dtype'] != 'F32' or record['kind'] not in (1, 2):
            raise ValueError('exact source history dtype/kind required')
        shape = record['shape']
        if len(shape) != 2 or any(type(n) is not int or n <= 0 for n in shape):
            raise ValueError('finite positive source history shape required')
        if shape[1] != {1: 512, 2: 128}[record['kind']]:
            raise ValueError('source history row layout mismatch')
        row = inventory.get(path)
        if not isinstance(row, dict):
            raise ValueError('eager history missing from actual input enrollment: ' + path)
        required = ('bytes', 'dev', 'ino', 'mtime_ns', 'ctime_ns')
        if any(type(row.get(k)) is not int or row[k] < 0 for k in required):
            raise ValueError('complete immutable fstat stamp required')
        payload = math.prod(shape) * 4
        if row['bytes'] <= payload:
            raise ValueError('NPY file extent must include header and full source payload')
        if row.get('sha256') != record['file_sha256'] or len(row['sha256']) != 64:
            raise ValueError('exact history file identity required')
        identity = (row['dev'], row['ino'])
        stamp = tuple(row[k] for k in required) + (row['sha256'],)
        if identity in unique and unique[identity] != stamp:
            raise ValueError('same inode has inconsistent immutable identity')
        unique[identity] = stamp
        payload_total += payload
    pages = sum((stamp[0] + page_bytes - 1) // page_bytes for stamp in unique.values())
    return dict(history_records=len(records), unique_file_inodes=len(unique),
                source_payload_bytes=payload_total,
                full_eager_filecache_page_upper_bytes=pages * page_bytes,
                page_bytes=page_bytes,
                # pread assigns the next chunk before releasing the old one.
                pread_simultaneous_chunk_payload_upper_bytes=2 * 1048576,
                existing_cache_credit_bytes=0, physical_admission=False,
                excludes=['allocator and bytes headers', 'other immutable inputs',
                          'output/journal/checkpoint filecache', 'kernel/page tables',
                          'peer growth', 'cumulative guest PFN reuse proof'])
