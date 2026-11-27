"""Fail-closed FIRM placement of actual mapped landing/collector cells."""
from pathlib import Path
from collections import defaultdict
from math import isfinite
import re



def _tcl_quote(s):
    """CLAND-PUTS-QUOTE 11-12 (QC sle_su_c s27 place rc 2: global_place.tcl 'invalid command name
    "72.38399999999999,"'): a face-window note carries python lists [x0, y0, ...]; inside a Tcl "..." string
    [ ] is command substitution, so escape [ ] $ \\ and the quote."""
    return re.sub(r'([\[\]$"\\])', r'\\\1', str(s))

def safe(s):return re.sub(r'\W','_',s)


def _native_stage_pattern(prefix, mode):
    return '^' + prefix + '$' if mode == 'cell' else f'(^|[/.]){prefix}[/.]'


# The plan emits exact names and large unions of literal suffixes.
# Use dictionary lookups only for these forms; all other valid selectors
# run the same Tcl regexp as placement.
_NATIVE_NAME_LITERAL = r"(?:[A-Za-z0-9_/:-]|\\[.\\\[\]$])+"
_NATIVE_ENUMERATION = re.compile(
    r"(" + _NATIVE_NAME_LITERAL + r")\(\?:(" + _NATIVE_NAME_LITERAL +
    r"(?:\|" + _NATIVE_NAME_LITERAL + r")*)\)(?:(" + _NATIVE_NAME_LITERAL + r"))?"
)


def _native_exact_names(prefix):
    enumeration = _NATIVE_ENUMERATION.fullmatch(prefix)
    if enumeration:
        stem, choices, tail = enumeration.groups()
        patterns = (stem + choice + (tail or '') for choice in choices.split('|'))
    elif re.fullmatch(_NATIVE_NAME_LITERAL, prefix):
        patterns = (prefix,)
    else:
        return ''
    return ' '.join('{' + re.sub(r'\\(.)', r'\1', name) + '}' for name in patterns)


_NATIVE_REGEXP_TOKEN = re.compile(r"\\.|\[[A-Za-z0-9_/.-]+\]|[()[\]|]")


def _native_cell_stem(prefix):
    """Find a required literal stem for the common grouped cell regexes."""
    start = re.match(_NATIVE_NAME_LITERAL, prefix)
    if not start or prefix[start.end():start.end() + 1] not in ('(', '['):
        return ''
    depth = 0
    for match in _NATIVE_REGEXP_TOKEN.finditer(prefix, start.end()):
        token = match[0]
        if token == '(':
            depth += 1
        elif token == ')':
            depth -= 1
        elif token in ('[', ']') or (token == '|' and depth == 0):
            return ''
    return '^' + start[0] if depth == 0 else ''


def native_stage_selector_check_tcl(t):
    """Check ordered native-selector ownership on the retained post-synth DB."""
    cfg = t.get('clock', {}).get('landing_contract', {}).get('native_stage_groups')
    if cfg is None:
        return ''
    _native_stage_groups(t, [])
    rows = []
    for row in cfg['groups']:
        prefix = row['prefix']
        mode = row.get('match', 'prefix')
        pattern = _native_stage_pattern(prefix, mode)
        names = _native_exact_names(prefix) if mode == 'cell' else ''
        stem = _native_cell_stem(prefix) if not names and mode == 'cell' else ''
        rows.append('  {{%s} {%s} %d {%s} {%s}}' % (row['tag'], pattern, 'density' in row, names, stem))
    return 'cland_native_selector_check {\n' + '\n'.join(rows) + '\n}\n'


def _native_stage_groups(t, groups):
    # Existing HEAD vd stages must occupy the windows the plan already prices.
    cfg = t.get('clock', {}).get('landing_contract', {}).get('native_stage_groups')
    if cfg is None:
        return groups, ''
    # v1: one content.  v2 (FABLE-FIX-HEAD-LEP0N-R5 11-21, gen-mode type with several contents joined by type nets):
    # contents [{content, module, params}], every group prefix starts with one of them.
    if isinstance(cfg, dict) and set(cfg) == {'schema', 'content', 'module', 'params', 'groups'} and cfg['schema'] == 'opentallas.native_stage_groups.v1':
        heads = [dict(content=cfg['content'], module=cfg['module'], params=cfg['params'])]
    elif isinstance(cfg, dict) and set(cfg) == {'schema', 'contents', 'groups'} and cfg['schema'] == 'opentallas.native_stage_groups.v2':
        heads = cfg['contents']
        if not isinstance(heads, list) or not heads or any(not isinstance(h, dict) or set(h) != {'content', 'module', 'params'} for h in heads) \
                or len({h['content'] for h in heads}) != len(heads):
            raise ValueError('native_stage_groups contents fields')
    else:
        raise ValueError('native_stage_groups schema/fields')
    for head in heads:
        matches = [x for x in t.get('contents', []) if x.get('inst') == head['content']]
        if len(matches) != 1 or matches[0].get('module') != head['module'] or matches[0].get('params', {}) != head['params']:
            raise ValueError('native_stage_groups content/module/params mismatch')
    owners = tuple(re.escape(h['content']) for h in heads)
    rows = cfg['groups']
    if not isinstance(rows, list) or not rows:
        raise ValueError('native_stage_groups needs nonempty groups')
    width, height = t['outline_um']; seen = {x[0] for x in groups}; added = []; leaf = {}; density = {}; ff_only = []
    for row in rows:
        if not isinstance(row, dict) or not {'prefix', 'rect_um', 'tag'} <= set(row) or set(row) - {'prefix', 'rect_um', 'tag', 'match', 'density'}:
            raise ValueError('native_stage_groups group fields')
        mode = row.get('match', 'prefix')
        if mode not in ('prefix', 'cell'):
            raise ValueError('native_stage_groups match must be prefix or cell')
        prefix, rect, tag = row['prefix'], row['rect_um'], row['tag']
        if not isinstance(prefix, str) or not prefix.startswith(owners) or any(x in prefix for x in '{}\n\r\t\0') or prefix in seen:
            raise ValueError('native_stage_groups invalid/duplicate prefix')
        try:
            re.compile(prefix)
        except re.error as exc:
            raise ValueError('native_stage_groups invalid regex') from exc
        if not isinstance(tag, str) or not re.fullmatch(r'stage:[A-Za-z0-9_.:-]+', tag):
            raise ValueError('native_stage_groups invalid tag')
        if 'density' in row:
            d = row['density']
            if mode != 'cell' or type(d) not in (int, float) or not isfinite(d) or not (0.4 <= d <= 0.6):
                raise ValueError('native_stage_groups density requires cell match and 0.4..0.6')
            if tag in density and density[tag] != d:
                raise ValueError('native_stage_groups conflicting tag density')
            density[tag] = d; ff_only.append(prefix)
        if not isinstance(rect, list) or len(rect) != 4 or any(type(x) not in (int, float) or not isfinite(x) for x in rect):
            raise ValueError('native_stage_groups finite rectangle required')
        if not (0 <= rect[0] < rect[2] <= width and 0 <= rect[1] < rect[3] <= height):
            raise ValueError('native_stage_groups rectangle outside outline')
        seen.add(prefix); added.append((prefix, rect, tag))
        if mode == 'cell':
            leaf[prefix] = _native_stage_pattern(prefix, mode)
    # Use the exact matcher that the later placement loop uses.
    entries = ' '.join('{' + p + '}' for p, _, _ in added)
    check = '\n'.join(['foreach cland_native_prefix {%s} {' % entries,
        ' set cland_native_found 0',
        ' foreach cland_native_i [$ff_blk getInsts] {',
        '  if {[regexp [format {(^|[/.])%s[/.]} $cland_native_prefix] [$cland_native_i getName]]} {set cland_native_found 1; break}',
        ' }',
        ' if {!$cland_native_found} {',
        '  error "OT_CLAND missing native stage group $cland_native_prefix"',
        ' }', '}', 'unset -nocomplain cland_native_prefix cland_native_found cland_native_i', ''])
    if leaf:
        init = 'set ::cland_native_leaf_regex [dict create]\n'
        init += ''.join('dict set ::cland_native_leaf_regex {' + p + '} {' + pat + '}\n' for p, pat in leaf.items())
        init += 'set ::cland_native_ff_only [dict create]\n'
        init += ''.join('dict set ::cland_native_ff_only {' + p + '} 1\n' for p in ff_only)
        init += 'set ::cland_native_tag_density [dict create]\n'
        init += ''.join('dict set ::cland_native_tag_density {' + tag + '} ' + str(d) + '\n' for tag, d in density.items())
        init += '''unset -nocomplain cland_native_named_cells
set cland_native_leaf_members {}
proc cland_native_leaf_insts {prefix} {
 global ff_blk cland_native_named_cells cland_native_leaf_members
 if {[dict exists $cland_native_leaf_members $prefix]} {
  return [dict get $cland_native_leaf_members $prefix]
 }
 # Native stages only move instances. Capture DB order and names once for this hook invocation.
 if {![info exists cland_native_named_cells]} {
  set cland_native_named_cells {}
  foreach i [$ff_blk getInsts] {
   lappend cland_native_named_cells [list $i [$i getName]]
  }
 }
 set pattern [dict get $::cland_native_leaf_regex $prefix]
 set ff_only [dict exists $::cland_native_ff_only $prefix]
 set hit {}
 foreach entry [lsearch -all -inline -regexp -index 1 $cland_native_named_cells $pattern] {
  set i [lindex $entry 0]
  if {$ff_only && ![string match DFF* [[$i getMaster] getName]]} continue
  lappend hit $i
 }
 dict set cland_native_leaf_members $prefix $hit
 return $hit
}
proc cland_native_sp {tag} {
 if {[dict exists $::cland_native_tag_density $tag]} {return [expr {0.4 / [dict get $::cland_native_tag_density $tag]}]}
 return 1.0
}
'''
        check = check.replace(
            ' set cland_native_found 0',
            ' if {[dict exists $::cland_native_leaf_regex $cland_native_prefix]} {\n'
            '  if {![llength [cland_native_leaf_insts $cland_native_prefix]]} {\n'
            '   error "OT_CLAND missing native stage group $cland_native_prefix"\n'
            '  }\n  continue\n }\n set cland_native_found 0')
        check = init + check
    return groups + added, check


_PLAIN_GROUP_WORD = re.compile(r'[A-Za-z0-9_]+')


def _group_line(p, r, tag):
    r"""One cland_groups entry.  HEAD-LEP0N-OPUS 11-17: a non-plain prefix (a native_stage_groups regex such as
    u_core\.u\.g_plw\.g_s\\\[0\\\][/.].*) is written as a braced Tcl word.  Unbraced, the placement loop's lassign
    backslash-substituted it (\. -> ., \\ -> \, \[ -> [), so it no longer equalled its braced ::cland_native_leaf_regex
    key and fell to the generic regexp, which matches nothing: hd_lep0N NF15f GPL stopped at "OT_CLAND no mapped cells
    found under u_core.u.g_plw.g_s\[0\][/.].*" with the 11 stage flops present.  Plain names are emitted unchanged."""
    rect = '{' + ' '.join(f'{v:.5f}' for v in r) + '}'
    word = p if _PLAIN_GROUP_WORD.fullmatch(p) else '{' + p + '}'
    return '  {' + word + ' ' + rect + ' ' + tag + '}'


def _native_stage_placement_source(t, source):
    cfg = (t or {}).get('clock', {}).get('landing_contract', {}).get('native_stage_groups', {})
    if not any(row.get('match') == 'cell' for row in cfg.get('groups', [])):
        return source
    marker = 'proc cland_group_insts {prefix} {\n global ff_blk cland_instance_index\n'
    if source.count(marker) != 1:
        raise ValueError('native leaf matcher source marker missing')
    extra = ''' if {[dict exists $::cland_native_leaf_regex $prefix]} {
  return [cland_native_leaf_insts $prefix]
 }
'''
    source = source.replace(marker, marker + extra)
    if any('density' in row for row in cfg.get('groups', [])):
        source = source.replace('set sp 1.0', 'set sp [cland_native_sp $tag]')
    return source


def _group_rect_overrides(t, groups, stale=None):
    """Explicit physical collector/raw-copy sites; absent plans keep identical output.

    GEN-CLASS-1 11-12 (QC sle_ctl__cl372cea1c gen: 'unknown ... landing group override u_cland_collect_rst_n_t19'):
    group_rects_um is keyed on collector tree NODE names, and a reset-tree re-solve (taps moved with the partner
    windows) keeps the names but changes which nodes are on a source's path.  An override whose node is still in the
    collector tree but on no active path has no group to move (build_local emits no u_cland_collect_/u_cland_reset_
    for it): it is a stale no-op, so it is dropped and logged (stale: {prefix: reason}, from tcl()).  A prefix that is
    not a tree node at all, ambiguous or of an unsupported kind still fails closed."""
    c = t.get('clock', {}).get('landing_contract', {})
    if 'group_rects_um' not in c:
        return groups, ''
    overrides = c['group_rects_um']
    if not isinstance(overrides, dict):
        raise ValueError('landing group_rects_um must be an object')
    known = defaultdict(list)
    for prefix, rect, tag in groups:
        known[prefix].append(tag)
    width, height = t['outline_um']
    dropped = {}
    for prefix, rect in overrides.items():
        if not isinstance(prefix, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', prefix):
            raise ValueError(f'invalid landing group prefix {prefix!r}')
        tags = known.get(prefix, [])
        if not tags and prefix in (stale or {}):
            dropped[prefix] = stale[prefix]
            continue
        if len(tags) != 1 or not (tags[0].startswith('collector:') or tags[0] == 'raw-copy-optional'):
            raise ValueError(f'unknown, ambiguous or unsupported landing group override {prefix!r}')
        if not isinstance(rect, (list, tuple)) or len(rect) != 4 or any(
                type(v) not in (int, float) or not isfinite(v) for v in rect):
            raise ValueError(f'{prefix}: rectangle needs four finite numeric coordinates')
        x0, y0, x1, y1 = rect
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise ValueError(f'{prefix}: rectangle must be ordered and inside the type outline')
    notes = ''.join(f'puts "OT_CLAND stale group rectangle override {p}: {why}; dropped"\n'
                    for p, why in sorted(dropped.items()))
    overrides = {p: r for p, r in overrides.items() if p not in dropped}
    if not overrides:
        return groups, notes
    groups = [(p, overrides.get(p, r), tag) for p, r, tag in groups]
    # Optional raw copies can disappear during synthesis (a relay whose load a later
    # event re-pointed): placement already skips an absent optional group, so an
    # override on one only logs. An explicitly moved collector must exist in the
    # actual mapped design, rather than silently consuming no site.
    entries = ' '.join(f"{p} {0 if known[p][0] == 'raw-copy-optional' else 1}" for p in sorted(overrides))
    check = '''foreach {cland_override_prefix cland_override_required} {%s} {
 set cland_override_found 0
 foreach cland_override_i [$ff_blk getInsts] {
  if {[regexp [format {(^|[/.])%%s[/.]} $cland_override_prefix] [$cland_override_i getName]]} {set cland_override_found 1; break}
 }
 if {!$cland_override_found} {
  if {$cland_override_required} {error "OT_CLAND unused group rectangle override $cland_override_prefix"}
  puts "OT_CLAND optional group rectangle override $cland_override_prefix: no mapped instance, skipped"
 }
}
unset -nocomplain cland_override_prefix cland_override_required cland_override_found cland_override_i
''' % entries
    return groups, notes + check


def _bus_order(t,bus):
    """bit order of the band's bus on the type (buses[].order, or ft_slots in_order/out_order for <slot>_i/_o).
    FLOW-8 10-30 (DIE-HEAD-38 02:24 item 1): a slot with only 'order' (no in_order/out_order) uses it for both sides,
    the same fallback the schema pin layout uses (s_.get(stem + '_order', s_.get('order'))); before, the band read
    lsb_low and filled an lsb_high slot's ring reversed (+ff instead of +ffr: HEAD wshim_rx r2r 629 x343)."""
    for b in t.get('buses',[]):
        if b.get('name')==bus:return b.get('order','lsb_low')
    for s in t.get('ft_slots',[]):
        for suffix,key in (('_i','in_order'),('_o','out_order')):
            if s.get('name','')+suffix==bus:return s.get(key,s.get('order','lsb_low'))
    return 'lsb_low'


def band_rects(tn,name,band,t=None):
    """DIE-S81-47 11-01: the rect(s) of a landing band, nearest the bus pin first.  A band with rects_um (2..N disjoint
    rects; plan fix where no single legal rect exists, clock_landing_plan.fill_failed_bands) emits one cland_groups entry
    per rect with the same prefix and ring tag, and landing_placement.tcl packs the ring over them in that order.  Bands
    without rects_um return [rect_um] (unchanged output)."""
    if band.get('placement')=='FAIL' or not band.get('rect_um'):raise ValueError(f'{tn}.{name}: landing band absent')
    # Optional measured FF-only fill window. The outer reserved band remains
    # unchanged; a wide logic-sized band need not spread its FFs far past the
    # actual bus pins after its combinational logic is released to GPL.
    if 'ff_rect_um' in band:
        if band.get('ring_place') != 'ff' or 'rects_um' in band:
            raise ValueError(f'{tn}.{name}: ff_rect_um requires one FF-only band')
        outer, r = band['rect_um'], band['ff_rect_um']
        for rect in (outer, r):
            if not isinstance(rect, (list, tuple)) or len(rect) != 4 or any(
                    type(v) not in (int, float) or not isfinite(v) for v in rect):
                raise ValueError(f'{tn}.{name}: ff_rect_um needs four finite numeric coordinates')
        W,H=(t or {}).get('outline_um',[float('inf')]*2)
        if not (0 <= outer[0] <= r[0] < r[2] <= outer[2] <= W and
                0 <= outer[1] <= r[1] < r[3] <= outer[3] <= H):
            raise ValueError(f'{tn}.{name}: ff_rect_um must be inside the reserved band and type outline')
        return [list(r)]
    if 'rects_um' not in band:return [band['rect_um']]
    rs=band['rects_um']
    if not isinstance(rs,list) or len(rs)<2:raise ValueError(f'{tn}.{name}: rects_um needs 2 or more rects')
    if band.get('fill_axis') is not None:raise ValueError(f'{tn}.{name}: rects_um does not support fill_axis')
    W,H=(t or {}).get('outline_um',[float('inf')]*2)
    for r in rs:
        if not isinstance(r,(list,tuple)) or len(r)!=4 or any(type(v) not in (int,float) or not isfinite(v) for v in r):
            raise ValueError(f'{tn}.{name}: rects_um entry needs four finite numeric coordinates')
        if not (0<=r[0]<r[2]<=W and 0<=r[1]<r[3]<=H):raise ValueError(f'{tn}.{name}: rects_um entry {r} outside the type outline')
    for i,a in enumerate(rs):
        for b in rs[i+1:]:
            if min(a[2],b[2])>max(a[0],b[0])+1e-6 and min(a[3],b[3])>max(a[1],b[1])+1e-6:
                raise ValueError(f'{tn}.{name}: rects_um entries overlap')
    if list(rs[0])!=list(band['rect_um']):raise ValueError(f'{tn}.{name}: rect_um must be the first rects_um entry')
    return [list(r) for r in rs]


def _spread(band,order='lsb_low'):
    """DIE-HEAD-12 opt-in band_spread: ring tag suffix '@<spread>' (landing_placement.tcl widens each ring cell's reserved
    footprint by it, so the ring fills the whole band); no suffix when the band has no spread (default plans)."""
    sp=band.get('spread')
    # DIE-HEAD-13 opt-in band_ring="ff": '+ff' = place only the ring flops FIRM (bit-major), ring logic to GPL
    # DIE-HEAD-32 10-29: '+ffr' = the same, bit-major in DESCENDING bit order, for an lsb_high bus (bit 0 at the window's
    # high end): the band fills from its low corner, so the slot fill follows the pin order (hd_tile hk5m V1: ascending
    # fill put i[565]'s ring flops at the band top, 301.6 um from its pin at the bottom). lsb_low stays '+ff'.
    ff='' if band.get('ring_place')!='ff' else ('+ffr' if order=='lsb_high' else '+ff')
    axis=band.get('fill_axis')
    if axis not in (None,'x'):
        raise ValueError(f"landing fill_axis {axis!r}: want 'x' or absent")
    if axis=='x' and not ff:
        raise ValueError("landing fill_axis='x' requires ring_place='ff'")
    return ('' if not sp or sp<=1.0 else f'@{sp:.4f}')+('+x' if axis=='x' else '')+ff



def vertical_bands_with_x_fill(typ, pins):
    """Find explicitly horizontal soft FF bands with complete vertical pin banks."""
    from collections import defaultdict
    import clock_landings as CL

    bands = typ.get("clock", {}).get("landing_contract", {}).get("bands", {})
    if not bands:
        return []
    sizes = {
        bus["name"]: bus["width"] + bool(bus.get("epoch", bus.get("kind", "data") in ("data", "ctl")))
        for bus in typ.get("buses", ())
    }
    sizes.update({slot["name"] + "_i": slot["width"] + 1 for slot in typ.get("ft_slots", ())})
    by_bus = defaultdict(list)
    for row in pins:
        by_bus[row[0]].append(row)

    name = typ.get("module", "_landing_")
    shape = {"partition_types": {name: typ}}
    conflicts = []
    for bus, band in bands.items():
        if (
            band.get("fill_axis") != "x"
            or band.get("ring_place") != "ff"
            or band.get("hard_core")
            or band.get("native_role_banks")
            or "rects_um" in band
            or CL.hard_ring_params(shape, name, bus) is not None
        ):
            continue
        rows = by_bus[bus]
        bits = sizes.get(bus, 0)
        if bits < 2 or len(rows) != bits or {row[1] for row in rows} != set(range(bits)):
            continue
        faces = {row[5] for row in rows}
        if faces not in ({"E"}, {"W"}):
            continue
        xs = [row[3] for row in rows]
        ys = [row[4] for row in rows]
        if max(xs) - min(xs) < max(ys) - min(ys):
            conflicts.append((bus, next(iter(faces)), bits))
    return conflicts


def _native_role_banks(tn, name, band, typ):
    """Explicit opt-in native FF banks; no inferred clock roots or member counts."""
    cfg = band.get('native_role_banks')
    if cfg is None:
        return None
    if not isinstance(cfg, dict) or cfg.get('schema') != 'opentallas.landing_native_role_banks.v1':
        raise ValueError(f'{tn}.{name}: native_role_banks schema')
    if band.get('ring_place') != 'ff' or any(k in band for k in ('rects_um', 'ff_rect_um')):
        raise ValueError(f'{tn}.{name}: native role banks require one FF band without rectangle overrides')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
        raise ValueError('native role banks require an exact input bus name')
    required = {'schema', 'ff_pin_roles', 'banks', 'held_members', 'expected_total_members', 'expected_captures_per_port'}
    if set(cfg) != required or type(cfg['expected_captures_per_port']) is not int or cfg['expected_captures_per_port'] <= 0:
        raise ValueError('native role bank fields or first-capture slot count')
    roles = cfg.get('ff_pin_roles')
    if not isinstance(roles, dict) or not roles:
        raise ValueError('native role banks require qualified FF master pin roles')
    ident = lambda x: isinstance(x, str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', x)
    port = lambda x: isinstance(x, str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\[[0-9]+\])?', x)
    for master, role in roles.items():
        if not ident(master) or not isinstance(role, dict) or set(role) != {'clock', 'data', 'reset'}:
            raise ValueError('native role banks need exact master clock/data/reset pin roles')
        if not ident(role['clock']) or not isinstance(role['data'], list) or not role['data'] or not isinstance(role['reset'], list):
            raise ValueError('native role banks require one clock pin and explicit data/reset pin lists')
        pins = [role['clock']] + role['data'] + role['reset']
        if not all(ident(x) for x in pins) or len(pins) != len(set(pins)):
            raise ValueError('duplicate or invalid native FF pin role')
    banks = cfg.get('banks')
    held = cfg.get('held_members')
    if not isinstance(banks, list) or not banks or not isinstance(held, list):
        raise ValueError('native role banks need banks and explicit held_members')
    width, height = typ['outline_um']
    names, filters = set(), []
    for bank in banks:
        required = {'name', 'clock_port', 'first_capture', 'expected_members', 'expected_first_capture', 'rect_um', 'members'}
        if not isinstance(bank, dict) or set(bank) != required:
            raise ValueError('native role bank fields')
        if not ident(bank['name']) or bank['name'] in names or not port(bank['clock_port']):
            raise ValueError('duplicate bank name or invalid exact native clock port')
        names.add(bank['name'])
        filt = bank['first_capture']
        if filt not in ('any', 'present', 'absent'):
            raise ValueError('native first_capture filter must be any, present or absent')
        for clock, old in filters:
            if clock == bank['clock_port'] and (old == filt or 'any' in (old, filt)):
                raise ValueError('overlapping native role bank filters')
        filters.append((bank['clock_port'], filt))
        count, first = bank['expected_members'], bank['expected_first_capture']
        if type(count) is not int or count <= 0 or type(first) is not int or not 0 <= first <= count:
            raise ValueError('native role bank expected member/first-capture counts')
        if filt == 'present' and first != count or filt == 'absent' and first != 0:
            raise ValueError('native role bank first-capture count contradicts its filter')
        members = bank['members']
        if not isinstance(members, list) or len(members) != count:
            raise ValueError('native role bank pinned member count mismatch')
        for member in members:
            if not isinstance(member, dict) or set(member) != {'name', 'master'}:
                raise ValueError('native role bank pinned member fields')
            native_name = member['name']
            if not isinstance(native_name, str) or not native_name or any(c in native_name for c in '{}\n\r\t\0') or member['master'] not in roles:
                raise ValueError('invalid pinned native role member name/master')
        rect = bank['rect_um']
        if not isinstance(rect, (list, tuple)) or len(rect) != 4 or any(type(v) not in (int, float) or not isfinite(v) for v in rect):
            raise ValueError('native role bank rectangle requires four finite coordinates')
        if not (0 <= rect[0] < rect[2] <= width and 0 <= rect[1] < rect[3] <= height):
            raise ValueError('native role bank rectangle outside type outline')
    for i, bank in enumerate(banks):
        a = bank['rect_um']
        for other in banks[i + 1:]:
            b = other['rect_um']
            if min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1]):
                raise ValueError('native role bank rectangles overlap')
    seen = set()
    for bank in banks:
        for member in bank['members']:
            if member['name'] in seen:
                raise ValueError('duplicate pinned native role member')
            seen.add(member['name'])
    for member in held:
        if not isinstance(member, dict) or set(member) != {'name', 'master', 'clock_port'}:
            raise ValueError('held native role member fields')
        native_name = member['name']
        if not isinstance(native_name, str) or not native_name or any(c in native_name for c in '{}\n\r\t\0') or native_name in seen:
            raise ValueError('duplicate or invalid exact held native member')
        seen.add(native_name)
        if member['master'] not in roles or not port(member['clock_port']):
            raise ValueError('held native role member has unknown master/clock port')
    total = cfg.get('expected_total_members')
    if type(total) is not int or total != sum(b['expected_members'] for b in banks) + len(held):
        raise ValueError('native role bank total member count mismatch')
    return cfg


def _native_role_config(tn, typ):
    """Emit nothing unless a band explicitly opts in. Tcl braces preserve native names literally."""
    rows = []
    seen = set()
    atom = lambda v: '{' + str(v) + '}'
    for name, band in typ.get('clock', {}).get('landing_contract', {}).get('bands', {}).items():
        cfg = _native_role_banks(tn, name, band, typ)
        if cfg is None:
            continue
        prefix = band.get('instance', 'u_cland_' + name)
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', prefix) or prefix in seen:
            raise ValueError('native role banks require a unique exact group prefix')
        seen.add(prefix)
        roles = []
        for master, r in cfg['ff_pin_roles'].items():
            roles += [atom(master), atom('clock ' + atom(r['clock']) + ' data ' + atom(' '.join(r['data'])) + ' reset ' + atom(' '.join(r['reset'])))]
        banks = []
        for b in cfg['banks']:
            members = ' '.join(atom(m['name']) + ' ' + atom(m['master']) for m in b['members'])
            banks.append(atom(' '.join([atom(b['name']), atom(b['clock_port']), atom(b['first_capture']), str(b['expected_members']), str(b['expected_first_capture']), atom(' '.join(f'{v:.5f}' for v in b['rect_um'])), atom(members)])))
        held = [atom(' '.join(atom(m[k]) for k in ('name', 'master', 'clock_port'))) for m in cfg['held_members']]
        body = 'bus ' + atom(name) + ' total ' + str(cfg['expected_total_members']) + ' captures_per_port ' + str(cfg['expected_captures_per_port']) + ' roles ' + atom(' '.join(roles)) + ' banks ' + atom(' '.join(banks)) + ' held ' + atom(' '.join(held))
        rows.append('dict set ::cland_native_role_banks ' + atom(prefix) + ' ' + atom(body))
    return ('set ::cland_native_role_banks {}\n' + '\n'.join(rows) + '\n') if rows else ''


def _local_chunk_config(typ, die_clock=None):
    """Only explicitly selected writer chunks or FREG ordering change placement.  DIE-QC-97: die_clock (the plan clock
    block) applies the die ring fanout bound (clock.landing_ring_fanout_max) exactly as the ring generator does.
    CLAND-SLEW-1 (GEN-CLASS-1 11-12): every soft band whose ring carries read-select copies (DSREP > 1: the generator's
    reach rule clock_landings.ring_reach_select_copies, landing_ring_dsrep, or the wreg dsrep) gets a read-group row
    (read = 64 / DSREP), so each kept copy g_srep.sr[r].u_sel/di is keyed at its own group instead of the START bit;
    write 0 when the writer chunk is the legacy 64 (no change to the write side).  Bands without copies: no row."""
    import clock_landings as CL
    clock = (typ or {}).get('clock', {})
    cfg = clock.get('landing_ring_wreg') or {}
    if cfg and die_clock:
        cfg = CL.ring_fanout_wreg_cfg(die_clock, cfg)
    wc = cfg.get('write_chunk', 64)
    numeric = cfg.get('freg_numeric_order', False) is True
    tail = ' tail 1' if cfg.get('write_tail') else ''
    bands = clock.get('landing_contract', {}).get('bands', {})
    dcfg = clock.get('landing_ring_dsrep') or {}
    hard_plan = dict(partition_types={'_': typ or {}})

    def ring_w(bus, band):
        for k in ('ring_width', 'width'):
            if isinstance(band.get(k), int) and not isinstance(band.get(k), bool):
                return band[k]
        for b in (typ or {}).get('buses', []):
            if b.get('name') == bus and isinstance(b.get('width'), int):
                return b['width']
        return 0

    rows = []
    for bus in cfg.get('buses', []):
        band = bands.get(bus, {})
        prefix = band.get('instance', 'u_cland_' + bus)
        ds = cfg.get('dsrep', 1)
        if CL.hard_ring_params(hard_plan, '_', bus) is None and not band.get('hard_core'):
            ds = max(ds, CL.ring_reach_select_copies(ring_w(bus, band), cfg.get('read_chunk', 0)))
        rc = cfg.get('read_chunk') or 64 // ds
        if wc != 64:
            rows.append('dict set ::cland_local_chunks {' + prefix + '} {write ' + str(wc) + ' read ' + str(rc) + tail + '}')
        elif ds > 1 and not cfg.get('read_chunk'):
            rows.append('dict set ::cland_local_chunks {' + prefix + '} {write 0 read ' + str(rc) + '}')
        if numeric:
            rows.append('dict set ::cland_numeric_freg_banks {' + prefix + '.g_freg.u_face} 1')
    for bus, band in sorted(bands.items()):
        if bus in cfg.get('buses', []) or band.get('hard_core') or CL.hard_ring_params(hard_plan, '_', bus) is not None:
            continue
        ds = dcfg.get('dsrep', 1) if bus in (dcfg.get('buses') or []) else 1
        ds = max(ds, CL.ring_reach_select_copies(ring_w(bus, band)))
        # CLAND-RING-LOCALITY: the same shared reach rule as the ring RTL and the strap K (clock_landings.ring_wreg_reach):
        # the registered write enables of a wide soft strap ring are keyed at their own writer chunk (a plain or
        # non-strap ring has no such cells, so there the row only restates the read groups)
        rw = CL.ring_wreg_reach(hard_plan, '_', bus, clock.get('landing_ring_wreg'))
        if rw and die_clock:
            rw = CL.ring_fanout_wreg_cfg(die_clock, rw)
        wr = rw.get('write_chunk', 64) if rw else 64
        if ds > 1:
            prefix = band.get('instance', 'u_cland_' + bus)
            rows.append('dict set ::cland_local_chunks {' + prefix + '} {write ' + str(0 if wr == 64 else wr) + ' read ' + str(64 // ds) + '}')
    # A separate face bank must keep pin bit order even on a reach-derived WREG.
    for bus, band in sorted(bands.items()):
        if not band.get('freg_rect_um'):
            continue
        wreg = CL.ring_write_reg(hard_plan, '_', bus)
        if wreg and wreg.get('freg') and not (numeric and bus in cfg.get('buses', [])):
            prefix = band.get('instance', 'u_cland_' + bus)
            rows.append('dict set ::cland_numeric_freg_banks {' + prefix + '.g_freg.u_face} 1')
    if not rows and wc == 64 and not numeric:
        return ''
    return 'set ::cland_local_chunks {}\nset ::cland_numeric_freg_banks {}\n' + '\n'.join(rows) + '\n'

def _placement_source(active):
    source = Path(__file__).with_name('landing_placement.tcl').read_text()
    if not active:
        source = re.sub(r'^# BEGIN NATIVE_ROLE_BANKS\n.*?^# END NATIVE_ROLE_BANKS\n', '', source, flags=re.M | re.S)
    return source


def _band_groups(tn, name, band, typ):
    cfg = _native_role_banks(tn, name, band, typ or {})
    rects = [b['rect_um'] for b in cfg['banks']] if cfg else band_rects(tn, name, band, typ)
    # The emitted pad geometry can give a band a different bit direction
    # from the logical FT declaration. Keep the override local to placement.
    order = band.get('pinslot_order', _bus_order(typ or {}, name))
    if order not in ('lsb_low', 'lsb_high'):
        raise ValueError(f'{tn}.{name}: invalid pinslot_order {order!r}')
    tag = 'ring:' + name + _spread(band, order)
    prefix = band.get('instance', 'u_cland_' + name)
    groups = []
    face = band.get('freg_rect_um')
    if face is not None:
        # Optional first capture at the physical pin face. FREG otherwise shares
        # the storage band; adding the register alone does not shorten pin reach.
        import clock_landings as CL
        wreg = CL.ring_write_reg({'partition_types': {tn: typ or {}}}, tn, name)
        legacy = (typ or {}).get('clock', {}).get('landing_input_freg') or []
        if not (wreg and wreg.get('freg')) and name not in legacy:
            raise ValueError(f'{tn}.{name}: freg_rect_um requires this bus FREG')
        if cfg or len(rects) != 1:
            raise ValueError(f'{tn}.{name}: separate FREG bank requires one ordinary storage band')
        w, h = typ['outline_um']
        if (not isinstance(face, (list, tuple)) or len(face) != 4
                or any(type(v) not in (int, float) or not isfinite(v) for v in face)
                or not (0 <= face[0] < face[2] <= w and 0 <= face[1] < face[3] <= h)):
            raise ValueError(f'{tn}.{name}: invalid freg_rect_um')
        main = rects[0]
        if min(face[2], main[2]) > max(face[0], main[0]) and min(face[3], main[3]) > max(face[1], main[1]):
            raise ValueError(f'{tn}.{name}: FREG and storage banks overlap')
        groups.append((prefix + '.g_freg.u_face', list(face),
                       'ring:' + name + '@freg' + _spread(band, order)))
    groups.extend((prefix, rect, tag) for rect in rects)
    return groups

def _hard_core_rects(t):
    return [(h['origin_um'][0], h['origin_um'][1], h['origin_um'][0] + h['outline_um'][0],
             h['origin_um'][1] + h['outline_um'][1]) for h in (t or {}).get('hard_cores') or []]


def _row_free_fraction(cores, rect, halo=2.17):
    """Share of a window with rows: floorplan cuts rows about 2.05-2.17 um beside every macro (measured, coll_s)."""
    x0, y0, x1, y1 = rect
    hit = [(a - halo, b - halo, c + halo, d + halo) for a, b, c, d in cores
           if x0 < c + halo and x1 > a - halo and y0 < d + halo and y1 > b - halo]
    if not hit:
        return 1.0
    n = 16
    points = [(x0 + (i + .5) * (x1 - x0) / n, y0 + (j + .5) * (y1 - y0) / n) for i in range(n) for j in range(n)]
    return sum(not any(a <= x <= c and b <= y <= d for a, b, c, d in hit) for x, y in points) / len(points)


def _clear_of_hard_cores(t, rect, margin=4.32):
    """A landing window with almost no row under it moves to the nearest free window.

    The START event draws relay and local-reset sites on straight lines that cross child
    cores and SRAMs, and the band check then fails with upper bound 0. Stage count and RTL
    are unchanged; a window with row capacity is returned as is (identical output)."""
    cores = _hard_core_rects(t)
    x0, y0, x1, y1 = rect
    if _row_free_fraction(cores, rect) >= 0.25:
        return rect
    w, h = x1 - x0, y1 - y0
    width, height = t['outline_um']
    xs = {x0} | {v for a, _, c, _ in cores for v in (a - margin - w, c + margin)}
    ys = {y0} | {v for _, b, _, d in cores for v in (b - margin - h, d + margin)}
    edge = 4.32
    xs = [x for x in xs if edge <= x and x + w <= width - edge]
    ys = [y for y in ys if edge <= y and y + h <= height - edge]
    for _, x, y in sorted((abs(x - x0) + abs(y - y0), x, y) for x in xs for y in ys):
        if not any(x < c + margin and x + w > a - margin and y < d + margin and y + h > b - margin
                   for a, b, c, d in cores):
            return [round(x, 5), round(y, 5), round(x + w, 5), round(y + h, 5)]
    raise ValueError(f'no window clear of hard cores for START site {rect}')


def _centre(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def _chain_clear_of_hard_cores(t, origin_xy, stages, margin=4.32):
    """Windows for one START relay chain: stages inside a core may leave by any side, picked
    by Viterbi for the smallest longest hop (then total length). Stages not inside a core keep
    their window, so a chain with none inside is unchanged."""
    cores = _hard_core_rects(t)
    width, height = (t or {}).get('outline_um', (0, 0))
    edge = 4.32

    def free(q):
        return (edge <= q[0] and q[2] <= width - edge and edge <= q[1] and q[3] <= height - edge
                and not any(q[0] < c + margin and q[2] > a - margin and q[1] < d + margin and q[3] > b - margin
                            for a, b, c, d in cores))

    options = []
    for st in stages:
        x, y = st['xy_um']
        bw, bh = st.get('box_um') or (4.32, 4.32)     # BAND-CAP 11-17: opt-in box for a stage holding many relay flops
        r = [x - bw / 2, y - bh / 2, x + bw / 2, y + bh / 2]
        near = _clear_of_hard_cores(t, r, margin)
        opts = [near]
        for a, b, c, d in cores:
            if near is not r and r[0] < c + margin and r[2] > a - margin and r[1] < d + margin and r[3] > b - margin:
                opts += [q for q in ([a - margin - bw, r[1], a - margin, r[3]],
                                     [c + margin, r[1], c + margin + bw, r[3]],
                                     [r[0], b - margin - bh, r[2], b - margin],
                                     [r[0], d + margin, r[2], d + margin + bh]) if free(q)]
        options.append(opts)
    hop = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])
    states = [((0.0, 0.0), origin_xy, [])] if origin_xy is not None else None
    for opts in options:
        next_states = []
        for q in opts:
            c = _centre(q)
            if states is None:
                next_states.append(((0.0, 0.0), c, [q]))
                continue
            cost, _, path = min((((max(m, hop(p, c)), tot + hop(p, c)), p, pth) for (m, tot), p, pth in states),
                                key=lambda v: v[0])
            next_states.append((cost, c, path + [q]))
        states = next_states
    return [] if not stages else min(states, key=lambda v: v[0])[2]


def _reader_start_groups(t):
    """Actual kept relay instances at declared sites, through existing FIRM packing."""
    cfg = (t or {}).get('clock', {}).get('landing_reader_start')
    if cfg is None:
        return []
    groups = []
    if 'origin_rect_um' in cfg:
        origin = 'u_cland_rstart_rx' if (t or {}).get('landing_relay_start_copy') else 'u_cland_origin'
        groups.append((origin, _clear_of_hard_cores(t, cfg['origin_rect_um']), 'reader-start-origin'))
    origin_xy = _centre(_clear_of_hard_cores(t, cfg['origin_rect_um'])) if 'origin_rect_um' in cfg else None
    owners = None
    if cfg.get('share_trunk'):      # R-REACH-1: a shared trunk stage is one instance, placed once (its owner's group)
        import clock_landings as _CL
        owners = _CL.reader_start_owners(cfg)
    for bus, branch in sorted(cfg['branches'].items()):
        for i, rect in enumerate(_chain_clear_of_hard_cores(t, origin_xy, branch['stages'])):
            if owners is not None and owners[bus][i] != bus:
                continue
            groups.append((f'u_cland_reader_start_{safe(bus)}_{i}', rect, 'reader-start:'+bus))
    return groups


def _start_origin_xy(t):
    """Centre of the START origin home (the source of every writer START chain: u_cland_origin start_d drives stage 0):
    landing_writer_start / landing_reader_start origin_rect_um (cleared like the origin group) or landing_origin_rect_um.
    None when the plan pins no origin home."""
    ck = (t or {}).get('clock', {})
    for k in ('landing_writer_start', 'landing_reader_start'):
        rect = (ck.get(k) or {}).get('origin_rect_um')
        if rect is not None:
            return _centre(_clear_of_hard_cores(t, rect))
    rect = ck.get('landing_origin_rect_um')
    return _centre(rect) if rect is not None else None


# CLAND-FACEWIN-1 11-11 (QC cbn_q01__cldd6ea846 kw43 hcut1111 3_3 "OT_CLAND no legal nonoverlapping row/site in
# reserved band for u_bound.u_cland_fstart_rsf_o ... (writer-face:rsf_o)"): the final writer-face relay window is the
# fstart pin +-4.32 um, drawn blind.  rsf_o's pin (237.09, 2.66) sat on the 64 FIRM FT bit sites of a00 stage 7
# (x 233.28..241.3, y 0..9.2) and on the local-reset window lrst_start_3, so the window had no free row/site.
# _face_window_clear moves a window that overlaps FT bit sites / FT regs or a hard core (+4.32 um) to the nearest free
# segment of the same face (along the face, or up to the reach deeper), clear of those and of the other START /
# local-reset / status windows; a window with no FIRM blocker is returned unchanged (identical output).  With no free window within FACE_WINDOW_REACH_UM
# the window stays and the reason is recorded (FACE_WINDOW_NOTES -> "puts OT_CLAND face-window ..." in the tcl).
FACE_WINDOW_REACH_UM = 60.0
FACE_WINDOW_NOTES = []


def _ft_site_rects(t):
    """FIRM FT bit-site / FT register boxes of a type (one box per FT stage), as clock_landing_plan._band_obstacles"""
    out = []
    for slot in (t or {}).get('ft_slots') or []:
        cw, ch = slot.get('bit_site_cell_um', [1.404, .27])
        for stage in slot.get('bit_sites_um') or []:
            if stage:
                out.append((min(p[0] for p in stage) - cw / 2, min(p[1] for p in stage) - ch / 2,
                            max(p[0] for p in stage) + cw, max(p[1] for p in stage) + ch))
        if not slot.get('bit_sites_um'):
            out += [(x - 2.16, y - 2.16, x + 2.16, y + 2.16) for x, y in slot.get('regs_um') or []]
    return out


def _overlaps(r, o, m=0.0):
    return r[0] < o[2] + m - 1e-6 and r[2] > o[0] - m + 1e-6 and r[1] < o[3] + m - 1e-6 and r[3] > o[1] - m + 1e-6


def face_window_blockers(t, rect, others=()):
    """names of what blocks a writer-face window: ft (FT bit sites/regs), core (hard core +4.32 um), window (others)"""
    why = []
    if any(_overlaps(rect, o) for o in _ft_site_rects(t)):
        why.append('ft')
    if any(_overlaps(rect, o, 4.32) for o in _hard_core_rects(t)):
        why.append('core')
    if any(_overlaps(rect, o) for o in others):
        why.append('window')
    return why


def _face_window_clear(t, name, rect, others=(), reach=None):
    reach = FACE_WINDOW_REACH_UM if reach is None else reach
    # FIRM blockers only: an FT bit site or a hard core.  The START / local-reset windows are ~4.32-um grow windows placed
    # after this one (each fstart pin has its own local reset beside it), so they only bar the destination of a move.
    if not set(face_window_blockers(t, rect)) & {'ft', 'core'}:
        return rect
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    width, height = t['outline_um']
    obs = [('ft', o, 0.0) for o in _ft_site_rects(t)] + [('core', o, 4.32) for o in _hard_core_rects(t)] + \
          [('window', tuple(o), 0.0) for o in others]
    face = min((y0, 'S'), (height - y1, 'N'), (x0, 'W'), (width - x1, 'E'))[1]
    xs = {x0} | {v for _, o, m in obs for v in (o[0] - m - w, o[2] + m)}
    ys = {y0} | {v for _, o, m in obs for v in (o[1] - m - h, o[3] + m)}
    if face in 'SN':
        ys = {y0} | {y for y in ys if abs(y - y0) <= reach}
    else:
        xs = {x0} | {x for x in xs if abs(x - x0) <= reach}
    cands = sorted((abs(x - x0) + abs(y - y0), x, y) for x in xs for y in ys
                   if 0 <= x and x + w <= width and 0 <= y and y + h <= height)
    for d, x, y in cands:
        if d > reach:
            break
        r = [round(x, 5), round(y, 5), round(x + w, 5), round(y + h, 5)]
        if not any(_overlaps(r, o, m) for _, o, m in obs) and _row_free_fraction(_hard_core_rects(t), r) >= 0.25:
            FACE_WINDOW_NOTES.append(f'{name} moved {d:.2f} um along/off face {face}: {list(rect)} -> {r} '
                                     f'(was blocked by {"+".join(face_window_blockers(t, rect, others))})')
            return r
    FACE_WINDOW_NOTES.append(f'{name} kept {list(rect)}: no free {face}-face window within {reach:g} um '
                             f'(blocked by {"+".join(face_window_blockers(t, rect, others))})')
    return rect


def _writer_start_groups(t):
    """W1 writer START relays at declared sites (DIE-HEAD-38), same FIRM packing; [] when absent.
    CLAND-WSTART-1 (11-11, QC cbn_q11 NK pilot TT -1065.5 / base -667: u_cland_origin start_d -> writer_start_y_o23_0
    1163 um, one cycle): the chain is anchored at the START origin home like the reader chain.  Without the anchor the
    hard-core relocation minimised only the hops BETWEEN stages and moved y_o23 stages 0-2 (planned 305-um hops from
    the origin) onto the north core edge, 30 um apart, leaving the whole distance on the origin -> stage-0 hop.
    A chain with no stage inside a hard core is unchanged (one window per stage)."""
    cfg = (t or {}).get('clock', {}).get('landing_writer_start')
    if cfg is None:
        return []
    groups = []
    origin_xy = _start_origin_xy(t)
    others = [tuple(r) for _, r, _ in _status_reset_groups(t)]
    owners = None
    if cfg.get('share_trunk'):      # R-REACH-1: a shared trunk stage is one instance, placed once (its owner's group)
        import clock_landings as _CL
        owners = _CL.reader_start_owners(cfg)
    direct = cfg.get('direct_fstart_buses', [])
    if not isinstance(direct, list) or any(not isinstance(bus, str) for bus in direct) or len(set(direct)) != len(direct):
        raise ValueError('landing_writer_start.direct_fstart_buses must list distinct bus names')
    if set(direct) & cfg['branches'].keys():
        raise ValueError('direct FSTART face must not have writer transport stages')
    for bus in sorted(cfg['branches'].keys() | set(direct)):
        stages = [] if bus in direct else cfg['branches'][bus]['stages']
        for i, rect in enumerate(_chain_clear_of_hard_cores(t, origin_xy, stages)):
            if owners is not None and owners[bus][i] != bus:
                continue
            groups.append((f'u_cland_writer_start_{safe(bus)}_{i}', rect, 'writer-start:'+bus))
        # The last face relay contains a synchronous-reset AND as well as Q.
        # Keeping only Q at the pin let GPL drag its AND to the distant origin
        # reset: HEAD spn_end bu_o travelled 1.6 mm down and back (-181.51 ps).
        # Treat the complete final relay exactly like each transport relay.
        pins = [p for p in (t or {}).get('clock', {}).get('landing_contract', {}).get('pins', [])
                if p.get('name') == 'cland_fstart_out_' + bus and p.get('dir') == 'out']
        if len(pins) != 1:
            if bus in direct:
                raise ValueError(f'direct FSTART {bus} requires one output pin')
            continue  # parameter-form/older plans without a final face site stay unchanged
        width, height = t['outline_um']
        x, y = pins[0]['xy_um']
        x = min(max(x, 4.32), width - 4.32)
        y = min(max(y, 4.32), height - 4.32)
        others += [tuple(r) for _, r, _ in groups]
        rect = _face_window_clear(t, f'u_cland_fstart_{safe(bus)}', [x-4.32, y-4.32, x+4.32, y+4.32], others)
        groups.append((f'u_cland_fstart_{safe(bus)}', rect, 'writer-face:'+bus))
    return groups


def _origin_home_groups(t):
    """KV-TYPES-3 11-07 (kv3_sys_SD_v1 TT -267.16: origin sf negedge -> s0 posedge, a half-cycle edge, placed 1168 um
    apart because GPL pulled the origin flops toward three different pins). Optional clock.landing_origin_rect_um puts
    the whole START origin (sf/s0/s1/s2/pd) FIRM in one rectangle next to its tstart pin, so the half-cycle capture is
    local and only full-cycle START legs travel. No added cycles, no RTL change. Absent key = unchanged output."""
    ck = (t or {}).get('clock', {})
    rect = ck.get('landing_origin_rect_um')
    if rect is None:
        return []
    for k in ('landing_reader_start', 'landing_writer_start'):
        if 'origin_rect_um' in (ck.get(k) or {}):
            raise ValueError(f'landing_origin_rect_um conflicts with {k}.origin_rect_um (one origin home only)')
    if (not isinstance(rect, (list, tuple)) or len(rect) != 4
            or any(type(v) not in (int, float) or not isfinite(v) for v in rect)):
        raise ValueError('landing_origin_rect_um needs four finite numbers')
    w, h = t['outline_um']
    if not (0 <= rect[0] < rect[2] <= w and 0 <= rect[1] < rect[3] <= h):
        raise ValueError('landing_origin_rect_um must be ordered and inside the type outline')
    origin = 'u_cland_rstart_rx' if t.get('landing_relay_start_copy') else 'u_cland_origin'
    return [(origin, list(rect), 'origin-home')]


def _status_reset_groups(t):
    """DIE-HEAD-38 R1/R2 opt-in sites (absent = no group): status input relays, status stage anchors and
    same-cycle local reset copies, through the existing FIRM packing at +-2.16 um."""
    ck=(t or {}).get('clock',{});groups=[]
    near=lambda xy:_clear_of_hard_cores(t,[xy[0]-2.16,xy[1]-2.16,xy[0]+2.16,xy[1]+2.16])
    for tgt,rings in sorted((ck.get('landing_status_input_stages') or {}).items()):
        for ring,stages in sorted(rings.items()):
            for k,s in enumerate(stages):
                groups.append((f'u_cland_sin_{safe(tgt)}_{safe(ring)}_{k}',near(s['xy_um']),'status-stage:'+tgt))
    for inst,xy in sorted((ck.get('landing_status_anchors') or {}).items()):
        groups.append((inst,near(xy),'status-anchor'))
    for r in ck.get('landing_local_resets') or []:
        groups.append((f"u_cland_lrst_{safe(r['name'])}",near(r['xy_um']),'local-reset'))
    for branch in ck.get("landing_raw_branches") or []:
        name = safe(branch["name"])
        for i, site in enumerate(branch.get("hard_boot_prefix_um", [])):
            groups.append((f"u_cland_hard_raw_{name}_{i}", near(site), "literal-local-reset"))
        for i, stage in enumerate(branch["stages"]):
            groups.append((f"u_cland_raw_{safe(branch['name'])}_{i}",near(stage["xy_um"]),"literal-local-reset"))
    return groups


def _source_node(s):
    """collector tree node of a local source: its 'node' when the row names one (the node landing_collector.build_local,
    collector_reach and collector_reattach all use: the emitted RTL), else rst_n_t<tap>.  GENBUG D2: B6gsh leaf t8 t12 t17 t33
    t52 t59 t68 t72 and kv_leaf t3 carry a node (rst_n_t20 / t18) beside a different tap (46 / 47); the old tap-first rule here
    expected u_cland_collect_rst_n_t46 while the bound RTL holds rst_n_t20, so the plan scan and the placement hook disagreed
    with the emitter.  A hard-tree source (tap None, e.g. the KV modeled-PHY wrappers whose collector tree is only cland_h*
    relays) names its relay in 'node' as before."""
    if s.get('node'):
        return s['node']
    return f"rst_n_t{s['tap']}"


class LandingSourceUnmodeled(RuntimeError):
    """LANDING-SOURCE-UNMODELED: a landing local source whose node is no relay of the collector tree this kit holds"""


def _source_relay(tn, tree, s, c):
    """GENDRY-STOPITER-1124 (KV-OWN-HUB-R2, COORD: kv3_hub_Eo / kv3_hub_Wo PRE GENDRY died on a bare StopIteration here, A5t3 too): the
    relay of tree that drives local source s.  Without the bind's clock-landing sidecar (gen --clock-landing = as-built
    clock_landing_table, what the wave passes) no collector_event is installed and the contract's collector_tree is the native
    captured reset solve (u_rrl_*), which has no collector source nodes.  That is a modelling gap of the run, named here."""
    want = _source_node(s)
    for r in (tree or {}).get('relays') or []:
        if r.get('q') == want:
            return r
    how = "sidecar collector_event" if c.get('collector_event') else "contract collector_tree (no collector_event installed: no --clock-landing sidecar for this type?)"
    raise LandingSourceUnmodeled(
        f"LANDING-SOURCE-UNMODELED type {tn}: local source {s.get('name')} node {want} is no relay of the {how} "
        f"({len((tree or {}).get('relays') or [])} relays); pass the bind's clock-landing sidecar (as-built clock_landing_table) "
        f"as gen --clock-landing, as the kit wave does")


def collector_event(c):
    """The collector identity of a landing contract: the sidecar event the collector RTL was emitted from
    (contract collector_event, set by gen_phys.install_collector_event), else the contract's own published fields.
    contract collector_tree may hold the native captured reset solve (u_rrl_*): that tree owns the reset relays, not
    the collectors, and its node names and edges differ (KW-FIX-27 three-reset-tree class)."""
    ev=c.get('collector_event')
    if ev:return ev
    return dict(tree=c.get('collector_tree'),collector_root_node=c.get('collector_root_node'),
                local_sources=c.get('collector_local_sources',[]),children=c.get('collector_children',[]))


def _soft_status_site(tn, type_row, source, published, band):
    """Recover an impossible stale sidecar seat from its exact current physical alias.

    The sidecar still owns the collector node and the reset-source identity.
    Only the physical ready/fault seat can follow a matched current band alias.
    """
    xy = source['xy_um']
    w, h = type_row['outline_um']

    def on_outline(point):
        x, y = point
        return isfinite(x) and isfinite(y) and 0 <= x <= w and 0 <= y <= h

    if on_outline(xy):
        return xy
    name = source['name']
    matches = [
        row for row in published
        if row['name'] == name and row.get('band') == band
        and all(row.get(role) == source.get(role) == f'landing_{role}_{name}'
                for role in ('ready', 'fault'))
        and row.get('xy_um') is not None and row['xy_um'] == row.get('pin_xy_um')
        and on_outline(row['xy_um'])
    ]
    if len(matches) == 1:
        return matches[0]['xy_um']

    # The native status hook can reach inward from a slightly inset face
    # reference. A point outside even its 17.28 um entry window is stale.
    x, y = xy
    reach = 17.28
    if isfinite(x) and isfinite(y) and -reach < x < w + reach and -reach < y < h + reach:
        return xy
    raise ValueError(
        f'CLAND-STATUS-SITE {tn}.{name}: ready/fault point {xy} outside the '
        f'{w:g}x{h:g} outline with no matching current landing-band alias'
    )


def collector_nodes(ev):
    """Active tree nodes of a collector event: root plus every node on a source's path to it, the set
    landing_collector.build_local emits an u_cland_collect_<node> for.  -> (active nodes, {node: xy})"""
    tree,root=ev['tree'],ev['collector_root_node']
    adj=defaultdict(list);xy={'rst_root_n':tree['root']}
    for r in tree['relays']:adj[r['q']].append(r['d']);adj[r['d']].append(r['q']);xy[r['q']]=r['xy']
    parent={root:None};todo=[root]
    while todo:
        n=todo.pop()
        for q in adj[n]:
            if q not in parent:parent[q]=n;todo.append(q)
    active=set()
    for n in [_source_node(s) for s in ev.get('local_sources',[])]+[s['node'] for s in ev.get('children',[])]:
        while n is not None:active.add(n);n=parent[n]
    return active,xy


def collector_instances(ev):
    """the u_cland_collect_* instance names of a collector event"""
    instances = {'u_cland_collect_'+safe(n) for n in collector_nodes(ev)[0]}
    if ev.get("collector_egress_um") is not None:
        from landing_collector import egress_instances
        instances.update(egress_instances(ev["collector_egress_um"], ev.get("collector_root_node")))
    return instances


COLLECTOR_GROW_MAX = 32   # landing_placement.tcl cland_put_grow: window x1..x32 about the same centre


def _rows_reachable(t, rect, halo=2.17):
    """True when some area of rect, inside the type outline, lies outside every hard core and its row-cut halo
    (exact: the rect is cut on every core edge, each cell tested at its centre)."""
    W, H = (t or {}).get('outline_um', (float('inf'), float('inf')))
    x0, y0, x1, y1 = max(rect[0], 0.0), max(rect[1], 0.0), min(rect[2], W), min(rect[3], H)
    if x0 >= x1 or y0 >= y1:
        return False
    cores = [(a - halo, b - halo, c + halo, d + halo) for a, b, c, d in _hard_core_rects(t)]
    xs = sorted({x0, x1} | {v for a, _, c, _ in cores for v in (a, c) if x0 < v < x1})
    ys = sorted({y0, y1} | {v for _, b, _, d in cores for v in (b, d) if y0 < v < y1})
    for xa, xb in zip(xs, xs[1:]):
        for ya, yb in zip(ys, ys[1:]):
            cx, cy = (xa + xb) / 2, (ya + yb) / 2
            if not any(a < cx < c and b < cy < d for a, b, c, d in cores):
                return True
    return False


def _collector_window(tn, t, node, xy):
    """DIE-S81-85 11-09 (S81 ot_s81sl_leaf__t10 attempt 5, 3_3 'OT_CLAND no legal nonoverlapping row/site in reserved
    band for u_bound.u_cland_collect_rst_rl_148/_4_ (collector:rst_rl_148)'): a collector / reset raw-copy window is its
    tree relay xy +-2.16 um, and the collector tree was solved without the type's hard cores, so rst_rl_148
    (194.32, 859.32) is 73.8 um inside u_lf.u_vsw (224.64 um square): the window has no row, and the runtime grow law
    (cland_put_grow, x2..x32 = +-69.12 um) never leaves the macro, so global place stops after ~2 min of hooks.
    A window whose LARGEST grown window still reaches rows (outside every hard core + halo, inside the outline) is
    returned as is: identical output, the runtime law places it as before.  A window whose grow cannot reach any row
    moves, by the START / local-reset law (_clear_of_hard_cores), to the nearest 4.32 um window clear of every hard
    core; when none fits the outline the plan cannot hold the collector and gen fails here, not 3_3."""
    x, y = xy
    rect = [x - 2.16, y - 2.16, x + 2.16, y + 2.16]
    g = 2.16 * COLLECTOR_GROW_MAX
    if _rows_reachable(t, [x - g, y - g, x + g, y + g]):
        return rect
    try:
        return _clear_of_hard_cores(t, rect)
    except ValueError:
        raise ValueError(f'{tn}: landing collector {node} window {rect}: no row within +-{g:.2f} um (inside a hard '
                         'core) and no 4.32 um window clear of every hard core fits the type outline: the collector '
                         'band cannot be placed') from None


def _moved_type(t, macro_moves):
    """The type with its hard cores at their kit sites: gen_phys.macro_move_table (OT_MACRO_MOVES) entries {inst, to}
    replace the plan origin of that core.  No moves: the type itself."""
    if not macro_moves:
        return t
    to = {m['inst']: m['to'] for m in macro_moves.values()}
    return dict(t, hard_cores=[dict(h, origin_um=list(to[h.get('inst')])) if h.get('inst') in to else h
                               for h in t.get('hard_cores') or []])


def _dsel_cone_tcl(c, t=None):
    """HEAD-TOOLS-RINGDSEL (ALLFIX-HEAD C5): opt-in band key dsel_cone=true (needs ring_place='ff') -> 'set cland_dsel_cone
    {prefix ..}' so landing_placement.tcl keys and places each chunked-ring u_dsel AND-OR cone cell FIRM right behind its y
    flop; '' (output unchanged) when no band carries the key."""
    names = []
    data_launch = []
    packed_widths = []
    scoped_words = []
    local_chunks = ((t or {}).get("clock") or {}).get("landing_ring_wreg") or {}
    for name, band in sorted((c or {}).get('bands', {}).items()):
        v = band.get('dsel_cone')
        launch = band.get('dsel_data_launch')
        word_scope = band.get('dsel_data_scope')
        if word_scope is not None:
            width = band.get('width')
            bits = word_scope.get('word_bits') if isinstance(word_scope, dict) else None
            slots = word_scope.get('slots') if isinstance(word_scope, dict) else None
            pockets = word_scope.get('word_rects_um') if isinstance(word_scope, dict) else None
            ring = band.get('rect_um')
            if (launch is not True or type(width) is not int or not isinstance(bits, list) or not bits
                    or any(type(i) is not int or not 0 <= i <= width for i in bits)
                    or bits != sorted(set(bits)) or type(slots) is not int or slots < 1
                    or set(word_scope) != {'word_bits', 'slots', 'word_rects_um'}
                    or not isinstance(pockets, dict) or set(pockets) != {str(i) for i in bits}
                    or not isinstance(ring, list) or len(ring) != 4
                    or any(k in band for k in ('rects_um', 'ff_rect_um', 'fill_axis', 'native_role_banks', 'hard_core'))):
                raise ValueError(f"landing band {name}: invalid DSEL word scope")
            for rect in pockets.values():
                if (not isinstance(rect, list) or len(rect) != 4
                        or any(type(q) not in (int, float) or not isfinite(q) for q in rect)
                        or not (ring[0] <= rect[0] < rect[2] <= ring[2] and ring[1] <= rect[1] < rect[3] <= ring[3])):
                    raise ValueError(f"landing band {name}: DSEL word pocket crosses the ring band")
        if launch is not None and (launch is not True or v is not True):
            raise ValueError(f"landing band {name}: dsel_data_launch must be true and requires dsel_cone=true")
        if v is None:
            continue
        if v is not True:
            raise ValueError(f"landing band {name}: dsel_cone must be true or absent")
        if band.get('ring_place') != 'ff':
            raise ValueError(f"landing band {name}: dsel_cone requires ring_place='ff'")
        instance = band.get('instance', 'u_cland_' + name)
        names.append(instance)
        if word_scope is not None:
            words = ' '.join(str(bit) for bit in bits)
            rects = ' '.join(f'{bit} {{{" ".join(f"{q:.5f}" for q in pockets[str(bit)])}}}' for bit in bits)
            scoped_words.append(f'dict set ::cland_dsel_word_scope {{{instance}}} {{{{{words}}} {slots} {{{rects}}}}}')
        if launch:
            data_launch.append(instance)
            # Soft default-width rings use a single 64-bit chunk when the
            # planned padded width is 64, even when some y bits are optimized
            # away. Explicit custom read groups keep their native geometry.
            custom_read = name in (local_chunks.get("buses") or []) and local_chunks.get("read_chunk")
            if band.get("ring_width") == 64 and not band.get("hard_core") and not custom_read:
                packed_widths.append(f"{{{instance}}} 64")
    out = ('set cland_dsel_cone {' + ' '.join(names) + '}\n') if names else ''
    if data_launch:
        out += 'set cland_dsel_data_launch {' + ' '.join(data_launch) + '}\n'
    if packed_widths:
        out += 'set cland_dsel_data_launch_widths {' + ' '.join(packed_widths) + '}\n'
    if scoped_words:
        out += '\n'.join(scoped_words) + '\n'
        if ((c or {}).get('bands') or {}).get('xo_i0', {}).get('placement_xo_spread') is not None:
            out += 'set ::cland_export_dsel_anchors 1\n'
    return out



def _actual_pin_y_manifest(tn, name, cfg, t, bx):
    """Qualify the exact physical pins and bit-major native sequence of one east input."""
    hint = f'{tn}.{name}: pinslot_profile actual_pin_y'
    inputs = [bus for bus in t.get('buses', []) if bus.get('name') == name]
    if len(inputs) != 1 or inputs[0].get('dir') != 'in' or inputs[0].get('face') != 'E':
        raise ValueError(f'{hint} requires an exact east input bus')
    if not isinstance(cfg, dict) or set(cfg) != {'pins', 'members'}:
        raise ValueError(f'{hint} requires physical pins and ordered native members')
    pins, members = cfg['pins'], cfg['members']
    if not isinstance(pins, list) or not pins or not isinstance(members, list) or not members:
        raise ValueError(f'{hint} has an empty physical pin or native member list')
    width, height = t['outline_um']
    for pin in pins:
        if (not isinstance(pin, list) or len(pin) != 3 or pin[0] not in inputs[0].get('layers', [])
                or any(type(v) not in (int, float) or not isfinite(v) for v in pin[1:])
                or not bx <= pin[1] <= width or not 0 <= pin[2] <= height):
            raise ValueError(f'{hint} has an invalid physical pin reference')
    pattern = re.compile(rf'u_cland_{re.escape(name)}/[A-Za-z0-9_./\[\]$]+')
    names, bits = set(), set()
    for row in members:
        if (not isinstance(row, list) or len(row) != 2 or not isinstance(row[0], str)
                or not pattern.fullmatch(row[0]) or row[0] in names
                or type(row[1]) is not int or not 0 <= row[1] < len(pins)):
            raise ValueError(f'{hint} has an invalid or duplicate native member')
        names.add(row[0])
        bits.add(row[1])
    if bits != set(range(len(pins))):
        raise ValueError(f'{hint} has physical pins without a keyed member')
    return pins, members


def validate_pinslot_plan_pins(tn, t, planned_pins):
    """Refuse a retained bit-y manifest that differs from the current plan pin emitter."""
    bands = t.get('clock', {}).get('landing_contract', {}).get('bands', {})
    for name, band in bands.items():
        profile = band.get('pinslot_profile', {})
        if 'actual_pin_y' not in profile:
            continue
        pins, _ = _actual_pin_y_manifest(tn, name, profile['actual_pin_y'], t, band['rect_um'][2])
        pattern = re.compile(rf'{re.escape(name)}\[([0-9]+)\]')
        native = [pin for pin in planned_pins if pattern.fullmatch(pin['name'])]
        expected = {(f'{name}[{bit}]', layer, x, y) for bit, (layer, x, y) in enumerate(pins)}
        if len(native) != len(expected) or {(p['name'], p['layer'], p['x'], p['y']) for p in native} != expected:
            raise ValueError(f'{tn}.{name}: pinslot_profile actual_pin_y differs from current plan pin records')


def _capture_rank_seats_tcl(tn, c):
    """Emit an opt-in permutation of existing native data FF footprints."""
    lines = []
    masters = {"writer_capture": "DFFLQNx1_ASAP7_75t_R", "read_data": "DFFHQNx1_ASAP7_75t_R"}
    for bus, band in sorted(c.get("bands", {}).items()):
        moves = band.get("capture_rank_seats")
        if moves is None:
            continue
        prefix = "u_bound." + band.get("instance", "u_cland_" + bus) + "/"
        if band.get("ring_place") != "ff" or band.get("hard_core") or not moves:
            raise ValueError(f"{tn}.{bus}: native rank seats require a soft FF band and a nonempty permutation")
        by_name = {row["inst"]: row for row in moves}
        if len(by_name) != len(moves) or set(by_name) != {row["to_site_of"] for row in moves}:
            raise ValueError(f"{tn}.{bus}: native rank seats must permute the same set of instances")
        for row in moves:
            inst, dest = row["inst"], row["to_site_of"]
            x, y = row["from_um"]
            tx, ty = row["to_um"]
            valid = all(re.fullmatch(r"[A-Za-z0-9_.$/\[\]-]+", n) and n.startswith(prefix) for n in (inst, dest))
            if not valid or inst == dest or masters.get(row["role"]) != row["master"] or not all(
                    type(v) in (float, int) and isfinite(v) and v >= 0 for v in (x, y, tx, ty)):
                raise ValueError(f"{tn}.{bus}: invalid native rank FF {inst}")
            if [tx, ty] != by_name[dest]["from_um"]:
                raise ValueError(f"{tn}.{bus}: target footprint drift for {inst}")
            lines.append(f"  {{{{{inst}}} {row['master']} {{{x:.4f} {y:.4f}}} {{{dest}}}}}")
    return "set cland_capture_rank_seats {\n" + "\n".join(lines) + "\n}\n" if lines else ""


def _pinslot_profile_tcl(tn, c, t):
    """Optional east edge of the bit-major slot rows and literal writer FF locations."""
    out = []
    for name, band in (c or {}).get('bands', {}).items():
        if 'pinslot_profile' not in band:
            continue
        cfg = band['pinslot_profile']
        hint = f'{tn}.{name}: pinslot_profile'
        required = {'inset_um', 'guard_east_um', 'guard_seats_um'}
        if (not isinstance(cfg, dict) or not required <= set(cfg)
                or set(cfg) - required - {'reserve_guard_resize', 'actual_pin_y'}
                or type(cfg.get('reserve_guard_resize', False)) is not bool
                or band.get('ring_place') != 'ff'
                or any(k in band for k in ('rects_um', 'ff_rect_um', 'fill_axis', 'native_role_banks', 'hard_core', 'dsel_cone'))):
            raise ValueError(f'{hint} requires one existing soft FF y-slot band')
        ax, ay, bx, by = band_rects(tn, name, band, t)[0]
        profile = cfg['inset_um']
        edge = cfg['guard_east_um']
        num = lambda q: type(q) in (int, float) and isfinite(q)
        if (not isinstance(profile, list) or len(profile) != 3 or not all(map(num, profile))
                or not num(edge) or not bx < edge <= t['outline_um'][0]
                or not ay <= profile[0] < profile[1] <= by or not ax < profile[2] < bx):
            raise ValueError(f'{hint} has invalid y extent or x edge')
        guards = cfg['guard_seats_um']
        if not isinstance(guards, dict) or not guards:
            raise ValueError(f'{hint} needs exact writer FF guards')
        named = re.compile(r'u_ring\.g_wreg\.sl\[\d+\]\.ch\[\d+\]\.u_wen/q\$_DFF_P_')
        rows = []
        for member, xy in guards.items():
            if (not isinstance(member, str) or named.fullmatch(member) is None
                    or not isinstance(xy, list) or len(xy) != 2 or not all(map(num, xy))
                    or not bx <= xy[0] < edge or not ay <= xy[1] < by
                    or profile[0] <= xy[1] < profile[1]):
                raise ValueError(f'{hint} has invalid writer guard {member!r}')
            rows.append('{ {' + member + '}' + f' {xy[0]:.5f} {xy[1]:.5f}' + ' }')
        if len({tuple(xy) for xy in guards.values()}) != len(guards):
            raise ValueError(f'{hint} has duplicate writer guard seats')
        prefix = band.get('instance', 'u_cland_' + name)
        if not re.fullmatch(r'u_cland_[A-Za-z0-9_]+', prefix):
            raise ValueError(f'{hint} has unsupported native ring prefix')
        lo, hi, xmax = profile
        resize = ' 1' if cfg.get('reserve_guard_resize') else ''
        manifest = ''
        if 'actual_pin_y' in cfg:
            pins, members = _actual_pin_y_manifest(tn, name, cfg['actual_pin_y'], t, bx)
            pin_rows = ' '.join(f'{{{layer} {x:.5f} {y:.5f}}}' for layer, x, y in pins)
            member_rows = ' '.join('{{' + member + '} ' + str(bit) + '}' for member, bit in members)
            resize = f" {int(cfg.get('reserve_guard_resize', False))}"
            manifest = f' {{{{{pin_rows}}} {{{member_rows}}}}}'
        out.append(f'dict set ::cland_pinslot_profiles {{{prefix}}} '
                   f'{{{{{lo:.5f} {hi:.5f} {xmax:.5f}}} {edge:.5f} {{{" ".join(rows)}}}{resize}{manifest}}}')
    return '\n'.join(out) + '\n' if out else ''


def tcl(P,tn,macro_moves=None):
    """macro_moves (gen_phys.macro_move_table, kit macro sites when OT_MACRO_MOVES is set): the hard cores collector
    windows are cleared of (_collector_window); None / {} = plan origins."""
    c=P.types[tn].get('clock',{}).get('landing_contract',{})
    ev=collector_event(c)
    FACE_WINDOW_NOTES.clear()
    groups=_reader_start_groups(P.types[tn])+_writer_start_groups(P.types[tn])+_origin_home_groups(P.types[tn])+_status_reset_groups(P.types[tn]);status=[];tree=ev['tree'];root=ev['collector_root_node']
    cwin={};tmoved=_moved_type(P.types[tn],macro_moves)
    def near(xy,node=None):
        k=(node,tuple(xy))
        if k not in cwin:cwin[k]=_collector_window(tn,tmoved,node,xy)
        return cwin[k]
    if c.get('monitor')=='dataflow' or (root and tree is None):
        return _dataflow_tcl(tn,c,P.types[tn])
    soft_bands = {}
    for name,band in c.get('bands',{}).items():
        if band.get('hard_core'):continue   # QC-SLECTL-B: the ring is a hard child placed on this band (hard_cores[])
        # HARD-RING-BAND-1 (OPUS-FIX-KV-HUB-R6 11-22): a ring the plan realises as a signed hard child through hard_cores[]
        # param_wrap (clock_landings.hard_ring_params, the form the other ring consumers read) is a macro placed by
        # macro_place.tcl; emitting its soft ring band made global_place fail 'OT_CLAND no mapped ring flops found under
        # u_cland_<bus>' (kv3_hub_Eo / kv3_hub_Wo D28 hard ring rows carry no band hard_core flag).
        import clock_landings as CL
        if CL.hard_ring_params({"partition_types": {tn: P.types[tn]}}, tn, name) is not None:continue
        groups += _band_groups(tn, name, band, P.types[tn])
        soft_bands[name] = band
    for s in ev.get('local_sources',[]):
        name = s['name']
        xy = s['xy_um']
        if name in soft_bands:
            xy = _soft_status_site(tn, P.types[tn], s, c.get('collector_local_sources', []), soft_bands[name])
        x, y = xy
        for kind in ('ready', 'fault'):
            status.append((f'landing_{kind}_{name}', x, y))
        groups.append(('u_cland_rst_'+s['name'],near(_source_relay(tn,tree,s,c)['xy'],_source_node(s)),'raw-copy-optional'))
    stale={}
    if root:
        active,xy=collector_nodes(ev)
        if c.get("collector_egress_um") is not None:
            # STATUS-UP 11-25: every egress stage (stations + face register) at its own site; a station reset by a
            # local relay that is on no active path gets that relay's optional raw copy group at the relay site.
            from landing_collector import egress_chain
            for name, p, node in egress_chain(c["collector_egress_um"], root):
                groups.append((name, near(p, name[len("u_cland_collect_"):]), "collector:" + name[len("u_cland_collect_"):]))
                if node not in active and node != 'rst_root_n' and node in xy:
                    groups.append(('u_cland_reset_'+safe(node), near(xy[node], node), 'raw-copy-optional'))
        for n in sorted(set(xy)-active):
            for k in ('collect','reset'):
                stale[f'u_cland_{k}_'+safe(n)]=f'collector node {n} is in the tree but on no active path (tree re-solved)'
        for n in sorted(active):
            groups.append(('u_cland_collect_'+safe(n),near(xy[n],n),'collector:'+n))
            if n!='rst_root_n':groups.append(('u_cland_reset_'+safe(n),near(xy[n],n),'raw-copy-optional'))
        for s in ev.get('children',[]):
            if s['seam']:
                x,y=s['xy_um'];i=s['index']
                status.extend([(f'cland_dn_trained_{i}',x,y),(f'cland_dn_guard_{i}',x,y)])
    groups, override_check = _group_rect_overrides(P.types[tn], groups, stale)
    groups, native_check = _native_stage_groups(P.types[tn], groups)
    out=[f'puts "OT_CLAND face-window {_tcl_quote(n)}"' for n in FACE_WINDOW_NOTES]+['set cland_groups {']
    for p,r,tag in groups:
        # Optional raw copies only exist when the original START tap is gated.
        if tag=='raw-copy-optional':continue
        out.append(_group_line(p,r,tag))
    out+=['}','set cland_optional_groups {']
    for p,r,tag in groups:
        if tag=='raw-copy-optional':out.append(_group_line(p,r,tag))
    out+=['}','set cland_status {']
    out+=['  {'+n+f' {x:.5f} {y:.5f}'+'}' for n,x,y in status]
    out+=['}']
    role_config = _native_role_config(tn, P.types[tn])
    return '\n'.join(out)+'\n'+override_check+_dsel_cone_tcl(c,P.types[tn])+_pinslot_profile_tcl(tn,c,P.types[tn])+_capture_rank_seats_tcl(tn,c)+native_check+role_config+_local_chunk_config(P.types[tn], getattr(P, 'clock', None))+_native_stage_placement_source(P.types[tn], _placement_source(bool(role_config)))


def _dataflow_tcl(tn,c,t=None):
    """monitor="dataflow" (opt-in, FALLBACK-HEAD-2): ring storage bands plus the dedicated registered status
    output at each sender pin. No reset-tree collector exists, so nothing else is placed by this hook."""
    FACE_WINDOW_NOTES.clear()
    groups=_reader_start_groups(t)+_writer_start_groups(t)+_status_reset_groups(t);status=[]
    for name,band in sorted(c.get('bands',{}).items()):
        if band.get('hard_core'):raise ValueError(f"{tn}: band {name} is a hard child; dataflow monitor form unsupported")
        groups += _band_groups(tn, name, band, t)
    for pin in sorted(c.get('pins',[]),key=lambda q:q['name']):
        if pin['dir']=='out' and pin['name'].startswith(('cland_up_ready_','cland_up_fault_')):
            x,y=pin['xy_um'];status.append((pin['name'],x,y))
    groups, override_check = _group_rect_overrides(t or {}, groups)
    groups, native_check = _native_stage_groups(t or {}, groups)
    out=[f'puts "OT_CLAND face-window {_tcl_quote(n)}"' for n in FACE_WINDOW_NOTES]+['set cland_groups {']
    out+=[_group_line(p,r,tag) for p,r,tag in groups]
    out+=['}','set cland_optional_groups {','}','set cland_status {']
    out+=['  {'+n+f' {x:.5f} {y:.5f}'+'}' for n,x,y in status]
    out+=['}']
    role_config = _native_role_config(tn, t or {})
    return '\n'.join(out)+'\n'+override_check+_dsel_cone_tcl(c,t)+_pinslot_profile_tcl(tn,c,t or {})+_capture_rank_seats_tcl(tn,c)+native_check+role_config+_local_chunk_config(t or {})+_native_stage_placement_source(t or {}, _placement_source(bool(role_config)))
