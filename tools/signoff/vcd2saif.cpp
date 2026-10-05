// Streaming VCD -> SAIF converter for sign-off power (tools/signoff_analysis.py).
//
// Reads a VCD from a file or FIFO (so a multi-gigabyte dump of a gate-level
// decode never touches the disk) and writes a SAIF 2.0 backward file with, per
// traced bit, the time at 0 (T0), at 1 (T1), at X (TX) and the toggle count
// (TC) inside the window [begin, end) in VCD time units.  Only scopes under
// --scope (a dotted VCD scope path) are kept; the SAIF top instance is that
// scope's last component, nested INSTANCE blocks follow the VCD scopes below it.
//
// Usage: vcd2saif IN.vcd OUT.saif SCOPE[!] [BEGIN|auto [END]]   (auto: the first timestamp)
//
// A var that the VCD declares as a vector [msb:lsb] is written bit by bit as
// NAME[i]; a scalar as NAME.  Names are written SAIF-escaped (\ before any
// character outside [A-Za-z0-9_]).
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <unordered_map>
#include <map>
#include <memory>

struct Bit {
    unsigned long long t0 = 0, t1 = 0, tx = 0, tc = 0;
    char val = 'x';          // value committed at the end of the last timestamp
    char pend = 0;           // latest value seen in the current timestamp
    bool dirty = false;
    unsigned long long since = 0;
};

struct Var {
    std::string name;
    int msb = 0, lsb = 0;
    bool vector = false;
    size_t first = 0;   // index of bit lsb.. in bits[]
    int width = 1;
};

struct Scope {
    std::string name;
    std::map<std::string, std::unique_ptr<Scope>> kids;
    std::vector<size_t> vars;   // indices into vars
};

static std::vector<Bit> bits;
static std::vector<Var> vars;
static unsigned long long skipped_names = 0;
static std::unordered_map<std::string, std::vector<size_t>> by_code;   // code -> var indices
static unsigned long long now = 0, t_begin = 0, t_end = ~0ULL;
static bool active = true, suspended_seen = false;
static unsigned long long active_since = 0, active_time = 0;

static inline void account(Bit &b, unsigned long long upto) {
    unsigned long long lo = b.since < t_begin ? t_begin : b.since;
    unsigned long long hi = upto > t_end ? t_end : upto;
    if (hi > lo) {
        unsigned long long d = hi - lo;
        if (b.val == '0') b.t0 += d; else if (b.val == '1') b.t1 += d; else b.tx += d;
    }
    b.since = upto;
}

// An event-driven simulator (Icarus) can write several changes of one signal
// at one timestamp (zero-delay delta-cycle glitches, not physical).  Changes
// are therefore held per timestamp and only the value at its end is compared
// with the previous one: a toggle is a change between timestamps.
static std::vector<size_t> dirty;

static inline void set_bit(size_t i, char v) {
    if (v == 'X' || v == 'z' || v == 'Z') v = 'x';
    Bit &b = bits[i];
    b.pend = v;
    if (!b.dirty) { b.dirty = true; dirty.push_back(i); }
}

static void commit() {
    for (size_t i : dirty) {
        Bit &b = bits[i];
        b.dirty = false;
        char v = b.pend;
        if (v == b.val) continue;
        account(b, now);
        if (now >= t_begin && now < t_end && (b.val == '0' || b.val == '1') && (v == '0' || v == '1')) b.tc++;
        b.val = v;
    }
    dirty.clear();
}

static std::string esc(const std::string &s) {
    std::string o;
    for (char c : s) {
        if (!(isalnum((unsigned char)c) || c == '_')) o += '\\';
        o += c;
    }
    return o;
}

static void write_scope(FILE *f, const Scope &s, int depth) {
    std::string ind(depth * 2, ' ');
    fprintf(f, "%s(INSTANCE %s\n", ind.c_str(), esc(s.name).c_str());
    if (!s.vars.empty()) {
        fprintf(f, "%s  (NET\n", ind.c_str());
        for (size_t vi : s.vars) {
            const Var &v = vars[vi];
            for (int k = 0; k < v.width; k++) {
                const Bit &b = bits[v.first + k];
                std::string n = v.name;
                if (v.vector) {
                    int idx = v.lsb <= v.msb ? v.lsb + k : v.lsb - k;
                    n += "[" + std::to_string(idx) + "]";
                }
                // OpenSTA's SAIF reader rejects '/' and ':' even escaped; such
                // names are synthesis temporaries (a function's source path),
                // left for OpenSTA to propagate through.
                if (n.find('/') != std::string::npos || n.find(':') != std::string::npos) {
                    skipped_names++;
                    continue;
                }
                fprintf(f, "%s    (%s (T0 %llu) (T1 %llu) (TX %llu) (TC %llu))\n", ind.c_str(), esc(n).c_str(),
                        b.t0, b.t1, b.tx, b.tc);
            }
        }
        fprintf(f, "%s  )\n", ind.c_str());
    }
    for (auto &kv : s.kids) write_scope(f, *kv.second, depth + 1);
    fprintf(f, "%s)\n", ind.c_str());
}

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: vcd2saif IN.vcd OUT.saif SCOPE [BEGIN [END]]\n");
        return 2;
    }
    const char *in = argv[1], *out = argv[2];
    std::string want = argv[3];
    bool own_only = !want.empty() && want.back() == '!';   // SCOPE! = that scope's own vars only
    if (own_only) want.pop_back();
    bool auto_begin = argc > 4 && !strcmp(argv[4], "auto");
    if (argc > 4 && !auto_begin) t_begin = strtoull(argv[4], nullptr, 10);
    if (argc > 5) t_end = strtoull(argv[5], nullptr, 10);
    FILE *f = strcmp(in, "-") ? fopen(in, "r") : stdin;
    if (!f) { perror(in); return 1; }
    static char buf[1 << 16];
    std::vector<std::string> path;
    Scope root;
    root.name = want.substr(want.rfind('.') == std::string::npos ? 0 : want.rfind('.') + 1);
    std::string timescale = "1ns";
    bool in_defs = true, in_timescale = false;
    unsigned long long changes = 0;
    while (fgets(buf, sizeof buf, f)) {
        char *p = buf;
        while (*p == ' ' || *p == '\t') p++;
        if (in_defs) {
            if (in_timescale) {
                std::string t(p);
                while (!t.empty() && (t.back() == '\n' || t.back() == ' ')) t.pop_back();
                if (t.rfind("$end", 0) == 0) { in_timescale = false; continue; }
                if (!t.empty()) {
                    size_t e = t.find("$end");
                    timescale = t.substr(0, e);
                    while (!timescale.empty() && timescale.back() == ' ') timescale.pop_back();
                    if (e != std::string::npos) in_timescale = false;
                }
                continue;
            }
            if (!strncmp(p, "$timescale", 10)) {
                std::string t(p + 10);
                size_t e = t.find("$end");
                std::string v = t.substr(0, e);
                while (!v.empty() && (v.back() == ' ' || v.back() == '\n')) v.pop_back();
                while (!v.empty() && v.front() == ' ') v.erase(0, 1);
                if (!v.empty()) timescale = v;
                if (e == std::string::npos) in_timescale = true;
                continue;
            }
            if (!strncmp(p, "$scope", 6)) {
                char kind[64], name[4096];
                if (sscanf(p, "$scope %63s %4095s", kind, name) == 2) path.push_back(name);
                continue;
            }
            if (!strncmp(p, "$upscope", 8)) { if (!path.empty()) path.pop_back(); continue; }
            if (!strncmp(p, "$var", 4)) {
                char kind[64], code[256], name[4096], rng[256];
                int width = 0;
                int n = sscanf(p, "$var %63s %d %255s %4095s %255s", kind, &width, code, name, rng);
                if (n < 4) continue;
                std::string full;
                for (auto &s : path) full += (full.empty() ? "" : ".") + s;
                if (!(full == want || (!own_only && full.rfind(want + ".", 0) == 0))) continue;
                Var v;
                v.name = name[0] == '\\' ? name + 1 : name;   // Icarus keeps an escaped identifier's backslash
                v.width = width;
                if (n == 5 && rng[0] == '[') {
                    int a = 0, b = 0;
                    if (sscanf(rng, "[%d:%d]", &a, &b) == 2) { v.msb = a; v.lsb = b; v.vector = true; }
                    else if (sscanf(rng, "[%d]", &a) == 1) { v.msb = v.lsb = a; v.vector = true; }
                } else if (width > 1) { v.msb = width - 1; v.lsb = 0; v.vector = true; }
                // descend to the scope
                Scope *s = &root;
                std::string rest = full.size() > want.size() ? full.substr(want.size() + 1) : "";
                size_t pos = 0;
                while (!rest.empty() && pos <= rest.size()) {
                    size_t dot = rest.find('.', pos);
                    std::string c = rest.substr(pos, dot == std::string::npos ? std::string::npos : dot - pos);
                    auto &k = s->kids[c];
                    if (!k) { k.reset(new Scope); k->name = c; }
                    s = k.get();
                    if (dot == std::string::npos) break;
                    pos = dot + 1;
                }
                v.first = bits.size();
                bits.resize(bits.size() + width);
                vars.push_back(v);
                s->vars.push_back(vars.size() - 1);
                by_code[code].push_back(vars.size() - 1);
                continue;
            }
            if (!strncmp(p, "$enddefinitions", 15)) { in_defs = false; continue; }
            continue;
        }
        char c = *p;
        if (c == '#') {
            commit();
            now = strtoull(p + 1, nullptr, 10);
            if (auto_begin) {
                t_begin = now; active_since = now;
                for (auto &b : bits) b.since = now;
                auto_begin = false;
            }
            if (now >= t_end) break;
            continue;
        }
        if (c == '$') {
            // $dumpoff / $dumpon (Icarus windows): the time between them is not
            // observed -- no T0/T1/TX, and it is excluded from DURATION
            if (!strncmp(p, "$dumpoff", 8) && active) {
                commit();
                for (auto &b : bits) account(b, now);
                if (now > active_since) active_time += now - (active_since > t_begin ? active_since : t_begin);
                active = false;
                suspended_seen = true;
            } else if (!strncmp(p, "$dumpon", 7) && !active) {
                active = true;
                active_since = now;
                for (auto &b : bits) b.since = now;
            }
            continue;
        }
        if (c == '\n' || c == 0) continue;
        if (!active) continue;
        if (c == 'b' || c == 'B') {
            char *sp = strchr(p, ' ');
            if (!sp) continue;
            std::string val(p + 1, sp - p - 1);
            char *code = sp + 1;
            size_t L = strlen(code);
            while (L && (code[L - 1] == '\n' || code[L - 1] == '\r' || code[L - 1] == ' ')) code[--L] = 0;
            auto it = by_code.find(code);
            if (it == by_code.end()) continue;
            for (size_t vi : it->second) {
                Var &v = vars[vi];
                // val is MSB first, possibly shorter (left-extend with 0, or x/z)
                int W = v.width, n = (int)val.size();
                char pad = (n && (val[0] == 'x' || val[0] == 'z')) ? val[0] : '0';
                for (int k = 0; k < W; k++) {   // k = offset from lsb
                    int src = n - 1 - k;
                    char bv = src >= 0 ? val[src] : pad;
                    set_bit(v.first + k, bv);
                }
            }
            changes++;
            continue;
        }
        if (c == 'r' || c == 'R') continue;
        // scalar: 0code / 1code / xcode
        char *code = p + 1;
        size_t L = strlen(code);
        while (L && (code[L - 1] == '\n' || code[L - 1] == '\r' || code[L - 1] == ' ')) code[--L] = 0;
        auto it = by_code.find(code);
        if (it == by_code.end()) continue;
        for (size_t vi : it->second) set_bit(vars[vi].first, c);
        changes++;
    }
    if (f != stdin) fclose(f);
    commit();
    unsigned long long stop = t_end == ~0ULL ? now : t_end;
    if (stop > t_end) stop = t_end;
    if (active) {
        for (auto &b : bits) account(b, stop);
        unsigned long long from = active_since > t_begin ? active_since : t_begin;
        if (stop > from) active_time += stop - from;
    }
    unsigned long long dur = suspended_seen ? active_time : (stop > t_begin ? stop - t_begin : 0);
    FILE *o = fopen(out, "w");
    if (!o) { perror(out); return 1; }
    fprintf(o, "(SAIFILE\n(SAIFVERSION \"2.0\")\n(DIRECTION \"backward\")\n(DESIGN \"%s\")\n", root.name.c_str());
    fprintf(o, "(PROGRAM_NAME \"opentallas vcd2saif\")\n(DIVIDER / )\n(TIMESCALE %s)\n(DURATION %llu)\n",
            timescale.c_str(), dur);
    write_scope(o, root, 0);
    fprintf(o, ")\n");
    fclose(o);
    fprintf(stderr, "vcd2saif: %zu vars, %zu bits, %llu value changes, duration %llu (%s), %llu bits not written (name)\n",
            vars.size(), bits.size(),
            changes, dur, timescale.c_str(), skipped_names);
    return 0;
}
