"""BIND-UNDRIVEN-IN 11-24 (COORD, report-only per r703): input ports left open by instances INSIDE leaf bodies.

The die elaboration blackboxes every leaf master, so an instance inside a leaf (S81 seqhost__t1 u_l2.u_vs, whose
bk_uid[7:0] the parent never connects) is invisible to the bind; only kit synth saw it.  This is a text scan of the
selected RTL source, no elaboration: each leaf master's body is preprocessed with the manifest defines, its module
instances are found with die_port_bind's own instance scan, and every input port of a child that the instance does
not name, or names with an empty `.p()`, is recorded.  The scan recurses into children (each module once).

Presence only: widths, generate conditions on the instance and parameter-gated use are not evaluated, so a hit may
be a proven-dead input; positional or `.*` connections are counted as unjudged.  Never an error."""
import re
from pathlib import Path

import die_port_bind as D


_INSTANCE_HEAD = re.compile(r'\s*([A-Za-z_]\w*|\\\S+)\s*(?:\[[^\]]*\]\s*)*\(')


def _instances(body):
    """[(master, inst, connection text or None)] for 'M [#(...)] I [range] (...)' at statement boundaries."""
    masked = D._unlabel(D._lexical_mask(body, strings=True))
    out = []
    for m in re.finditer(r'(?:^|;|\bbegin\b|\bend\b|\bendgenerate\b|\belse\b|\)|:)\s*([A-Za-z_]\w*)\s*', masked, re.M):
        name = m.group(1)
        if name in D._SV_KW:
            continue
        i = m.end()
        if masked.startswith('#', i):
            j = masked.find('(', i)
            if j < 0 or masked[i + 1:j].strip():
                continue
            try:
                i = D._closing_paren_masked(masked, j) + 1
            except ValueError:
                continue
        # Match at an offset without copying the rest of a large module for every candidate.
        im = _INSTANCE_HEAD.match(masked, i)
        if not im or im.group(1) in D._SV_KW:
            continue
        k = im.end() - 1
        try:
            e = D._closing_paren_masked(masked, k)
        except ValueError:
            out.append((name, im.group(1), None))
            continue
        out.append((name, im.group(1), masked[k + 1:e]))   # masked offsets: _unlabel shortens labels
    return out


class Scanner:
    def __init__(self, pick, defines=()):
        """pick(module) -> source file path or None (the bind's selected definition)."""
        self.pick = pick
        self.defines = {}
        for d in defines or ():
            k, _, v = str(d).partition("=")
            self.defines[k] = v
        self._files, self._mods, self._hits = {}, {}, {}
        self.unjudged = []

    def module(self, name):
        if name not in self._mods:
            f = self.pick(name)
            m = None
            if f:
                if f not in self._files:
                    try:
                        t = D.preprocess(D.strip_comments(Path(f).read_text(errors="replace")), dict(self.defines))
                        self._files[f] = {x.name: x for x in D.parse_modules(t, f)}
                    except (OSError, ValueError, IndexError):
                        self._files[f] = {}
                m = self._files[f].get(name)
            self._mods[name] = m
        return self._mods[name]

    def hits(self, name, _stack=()):
        """[(relative instance path, child master, port)] for the body of `name` and everything below it."""
        if name in self._hits:
            return self._hits[name]
        if name in _stack:
            return []
        m = self.module(name)
        res = []
        self._hits[name] = res
        if m is None:
            return res
        for child, inst, conns in _instances(m.body):
            cm = self.module(child)
            if cm is None:
                continue        # no RTL body of record (hard macro, primitive): its pins are the macro's view
            if conns is None or '.*' in conns or (conns.strip() and not conns.lstrip().startswith('.')):
                self.unjudged.append(f"{name}.{inst} ({child})")
                continue
            named = dict(D._named_conns(conns))
            for pn, (d, _) in cm.ports.items():
                if d == "input" and not named.get(pn):
                    res.append((inst, child, pn))
            for p, c, pn in self.hits(child, _stack + (name,)):
                res.append((f"{inst}.{p}", c, pn))
        return res
