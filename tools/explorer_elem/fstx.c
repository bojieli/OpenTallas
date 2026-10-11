/* fstx: minimal FST reader for the element activity replay (tools/explorer_elem/trace_bench.py).
 *
 *   fstx <file.fst> hier                      'S <timescale exponent>', then one line per variable:
 *                                             V <handle> <bits> <scope.path.name>
 *   fstx <file.fst> samp <clk handle> <list>  sample at every rising edge of <clk handle>; <list> holds lines
 *                                             "<handle> <t|v|b>" (t: per-cycle toggle count, v: per-cycle value)
 *
 * Cycle c is the interval [edge c, edge c+1); its value S_c is the signal value at the END of the time step of edge
 * c (registers clocked by that edge have updated).  Toggles(c) = popcount(S_c xor S_{c-1}); S_{-1} is the first
 * dumped value.  Output of samp: "E <n> <t_0> ... <t_n-1>" (edge times, FST time units), then per handle
 * "T <h> <x_0>,...,<x_n-1>" and/or "V <h> <s_0>,...,<s_n-1>" (s = value string, msb first, x/z kept).
 *
 * Built on the host from Verilator's bundled gtkwave fstapi (fstapi.c, fastlz.c, lz4.c) and zlib.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "fstapi.h"

static void die(const char *m) { fprintf(stderr, "fstx: %s\n", m); exit(2); }

static int do_hier(void *ctx) {
    printf("S %d\n", (int)fstReaderGetTimescale(ctx));
    char path[65536]; size_t plen[4096]; int depth = 0; path[0] = 0;
    struct fstHier *h;
    while ((h = fstReaderIterateHier(ctx))) {
        if (h->htyp == FST_HT_SCOPE) {
            size_t l = strlen(path);
            if (depth >= 4096) die("scope too deep");
            plen[depth++] = l;
            if (l + h->u.scope.name_length + 2 >= sizeof path) die("path too long");
            if (l) path[l++] = '.';
            memcpy(path + l, h->u.scope.name, h->u.scope.name_length); path[l + h->u.scope.name_length] = 0;
        } else if (h->htyp == FST_HT_UPSCOPE) {
            if (depth > 0) path[plen[--depth]] = 0;
        } else if (h->htyp == FST_HT_VAR) {
            const char *n = h->u.var.name; uint32_t nl = h->u.var.name_length;
            const char *sp = memchr(n, ' ', nl); if (sp) nl = (uint32_t)(sp - n);   /* "d [7:0]" -> "d" */
            printf("V %u %u %s%s%.*s\n", (unsigned)h->u.var.handle, (unsigned)h->u.var.length, path, *path ? "." : "", (int)nl, n);
        }
    }
    return 0;
}

typedef struct { uint32_t h; int len; char *cur; char *prev; int mode; uint16_t *tog; char **val; } Sig;
static Sig *sigs; static int nsig; static int *slot;   /* slot[handle] -> index into sigs, -1 none */
static fstHandle clk_h; static int clk_cur = 0, clk_at_step_start = 0;
static uint64_t step_t = 0; static int have_step = 0;
static uint64_t *edges; static int nedge = 0, cap_edge = 0;
static int dirty_first = 1;

static void grow(void) {
    if (nedge < cap_edge) return;
    cap_edge = cap_edge ? cap_edge * 2 : 1024;
    edges = realloc(edges, cap_edge * sizeof *edges);
    for (int i = 0; i < nsig; i++) {
        if (sigs[i].mode & 1) sigs[i].tog = realloc(sigs[i].tog, cap_edge * sizeof(uint16_t));
        if (sigs[i].mode & 2) sigs[i].val = realloc(sigs[i].val, cap_edge * sizeof(char *));
    }
}

static void close_step(void) {   /* end of the time step step_t: sample if the clock rose in it */
    if (!have_step) return;
    if (clk_cur == 1 && clk_at_step_start == 0) {
        grow();
        edges[nedge] = step_t;
        for (int i = 0; i < nsig; i++) {
            Sig *s = &sigs[i];
            if (s->mode & 1) {
                int t = 0;
                for (int k = 0; k < s->len; k++) t += (s->cur[k] != s->prev[k]);
                s->tog[nedge] = t > 65535 ? 65535 : t;
                memcpy(s->prev, s->cur, s->len);
            }
            if (s->mode & 2) s->val[nedge] = strndup(s->cur, s->len);
        }
        nedge++;
    }
    clk_at_step_start = clk_cur;
}

static void cb(void *user, uint64_t t, fstHandle h, const unsigned char *v) {
    (void)user; uint32_t len = v ? (uint32_t)strlen((const char *)v) : 0;
    if (!have_step || t != step_t) {
        close_step();
        if (have_step && dirty_first) dirty_first = 0;
        step_t = t; have_step = 1;
    }
    if (h == clk_h && v) clk_cur = (v[0] == '1');
    if ((int)h < 0) return;
    int i = slot[h]; if (i < 0 || !v) return;
    Sig *s = &sigs[i];
    if ((int)len != s->len) len = (uint32_t)strnlen((const char *)v, s->len);
    if ((int)len == s->len) memcpy(s->cur, v, len);
    else {   /* shorter string: left-pad (FST stores full width; be safe) */
        int pad = s->len - (int)len; memset(s->cur, '0', pad); memcpy(s->cur + pad, v, len);
    }
    if (dirty_first) memcpy(s->prev, s->cur, s->len);   /* S_-1 = the first dumped value */
}

int main(int argc, char **argv) {
    if (argc < 3) die("usage: fstx <fst> hier | samp <clk handle> <list>");
    void *ctx = fstReaderOpen(argv[1]);
    if (!ctx) die("cannot open fst");
    if (!strcmp(argv[2], "hier")) return do_hier(ctx);
    if (strcmp(argv[2], "samp") || argc < 5) die("bad mode");
    clk_h = (fstHandle)strtoul(argv[3], 0, 10);
    fstHandle maxh = fstReaderGetMaxHandle(ctx);
    slot = malloc((maxh + 2) * sizeof(int)); for (fstHandle k = 0; k <= maxh + 1; k++) slot[k] = -1;
    /* widths from the hierarchy */
    uint32_t *width = calloc(maxh + 2, sizeof(uint32_t));
    struct fstHier *hh;
    while ((hh = fstReaderIterateHier(ctx))) if (hh->htyp == FST_HT_VAR && hh->u.var.handle <= maxh) width[hh->u.var.handle] = hh->u.var.length;
    FILE *f = fopen(argv[4], "r"); if (!f) die("cannot open list");
    unsigned hv; char m; int capn = 0;
    while (fscanf(f, "%u %c", &hv, &m) == 2) {
        if (hv == 0 || hv > maxh || slot[hv] >= 0 || !width[hv]) continue;
        if (nsig == capn) { capn = capn ? capn * 2 : 256; sigs = realloc(sigs, capn * sizeof *sigs); }
        Sig *s = &sigs[nsig]; memset(s, 0, sizeof *s);
        s->h = hv; s->len = (int)width[hv]; s->mode = m == 't' ? 1 : m == 'v' ? 2 : 3;
        s->cur = malloc(s->len + 1); s->prev = malloc(s->len + 1);
        memset(s->cur, 'x', s->len); memset(s->prev, 'x', s->len); s->cur[s->len] = s->prev[s->len] = 0;
        slot[hv] = nsig++;
    }
    fclose(f);
    fstReaderClrFacProcessMaskAll(ctx);
    fstReaderSetFacProcessMask(ctx, clk_h);
    for (int i = 0; i < nsig; i++) fstReaderSetFacProcessMask(ctx, sigs[i].h);
    fstReaderSetUnlimitedTimeRange(ctx);
    fstReaderIterBlocks2(ctx, cb, 0, 0, 0);
    close_step();
    printf("E %d", nedge); for (int e = 0; e < nedge; e++) printf(" %llu", (unsigned long long)edges[e]); printf("\n");
    for (int i = 0; i < nsig; i++) {
        Sig *s = &sigs[i];
        if (s->mode & 1) { printf("T %u ", s->h); for (int e = 0; e < nedge; e++) printf(e ? ",%u" : "%u", s->tog[e]); printf("\n"); }
        if (s->mode & 2) { printf("V %u ", s->h); for (int e = 0; e < nedge; e++) printf(e ? ",%s" : "%s", s->val[e]); printf("\n"); }
    }
    fstReaderClose(ctx);
    return 0;
}
