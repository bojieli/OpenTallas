"""Read archive/ELF metadata only; never compile, link or execute an object."""
import json
import struct
from pathlib import Path


def inspect(path):
    path = Path(path)
    objects = 0
    comments, shapes = set(), set()
    lto = 0
    with path.open('rb') as f:
        length = path.stat().st_size
        if f.read(8) != b'!<arch>\n':
            raise ValueError('regular ar archive required')
        offset = 8
        while offset < length:
            f.seek(offset)
            header = f.read(60)
            if len(header) != 60 or header[-2:] != b'`\n':
                raise ValueError('ar header')
            name = header[:16].decode().strip()
            size = int(header[48:58])
            start = offset + 60
            if size < 0 or start + size > length:
                raise ValueError('ar member bounds')
            if name not in ['/', '//', '/SYM64/']:
                f.seek(start)
                eh = f.read(min(size, 64))
                if len(eh) != 64 or eh[:6] != b'\x7fELF\x02\x01':
                    raise ValueError('ELF64 little-endian required')
                fields = struct.unpack('<16sHHIQQQIHHHHHH', eh)
                if (fields[1], fields[2]) != (1, 62):
                    raise ValueError('ET_REL EM_X86_64 required')
                shapes.add((fields[1], fields[2])); objects += 1
                shoff, shsz, shnum, stridx = fields[6], fields[11], fields[12], fields[13]
                if shsz != 64 or shnum == 0 or stridx >= shnum or shoff + shnum * 64 > size:
                    raise ValueError('ELF section directory bounds')
                f.seek(start + shoff)
                sections = [struct.unpack('<IIQQQQIIQQ', f.read(64)) for _ in range(shnum)]
                strings = sections[stridx]
                if strings[4] + strings[5] > size:
                    raise ValueError('section name table bounds')
                f.seek(start + strings[4]); names = f.read(strings[5])
                for section in sections:
                    if section[0] >= len(names):
                        raise ValueError('section name bounds')
                    sec = names[section[0]:].split(b'\0', 1)[0]
                    if sec.startswith(b'.gnu.lto'):
                        lto += 1
                    if sec == b'.comment':
                        if section[4] + section[5] > size:
                            raise ValueError('compiler comment bounds')
                        f.seek(start + section[4])
                        comments.update(x.decode() for x in f.read(section[5]).split(b'\0') if x)
            offset = start + size + size % 2
    if not objects or lto:
        raise ValueError('objects required; LTO needs separate plugin gate')
    return dict(path=str(path), objects=objects,
                ELF='ELF64 little-endian ET_REL EM_X86_64',
                compiler_comments=sorted(comments), LTO_sections=lto)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    print(json.dumps(inspect(parser.parse_args().archive), indent=2))
