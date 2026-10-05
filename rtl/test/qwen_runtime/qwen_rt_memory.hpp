// Fast $readmemh-compatible loader for the runtime-composed benches: each line
// is one memory word of `words_per_line` 32-bit words, least-significant word
// last; `@hex` sets the word address; `//` comments and blank lines skipped.
// A short line is zero-extended on the left, as $readmemh does.
#pragma once
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <string>
#include <vector>
struct QwenHex {
    static std::vector<uint32_t> load(const std::string& path, size_t wpl) {
        FILE* f = fopen(path.c_str(), "rb");
        if (!f) throw std::runtime_error("open " + path);
        std::vector<uint32_t> out;
        std::vector<char> line;
        size_t row = 0;
        int c;
        auto flush = [&](std::vector<char>& l) {
            size_t a = 0, b = l.size();
            while (a < b && (l[a] == ' ' || l[a] == '\t' || l[a] == '\r')) a++;
            for (size_t i = a; i + 1 < b; i++) if (l[i] == '/' && l[i + 1] == '/') { b = i; break; }
            while (b > a && (l[b - 1] == ' ' || l[b - 1] == '\t' || l[b - 1] == '\r')) b--;
            if (a == b) return;
            if (l[a] == '@') { row = std::stoull(std::string(l.begin() + a + 1, l.begin() + b), nullptr, 16); return; }
            if (b - a > wpl * 8) throw std::runtime_error("wide hex row in " + path);
            if (out.size() < (row + 1) * wpl) out.resize((row + 1) * wpl, 0);
            uint32_t* w = &out[row * wpl];
            size_t n = b - a;
            for (size_t k = 0; k < n; k++) {
                char ch = l[b - 1 - k];
                uint32_t v = (ch >= '0' && ch <= '9') ? ch - '0' : (ch >= 'a' && ch <= 'f') ? ch - 'a' + 10
                           : (ch >= 'A' && ch <= 'F') ? ch - 'A' + 10 : 0xffffffff;
                if (v > 15) throw std::runtime_error("bad hex digit in " + path);
                w[k / 8] |= v << (4 * (k % 8));
            }
            row++;
        };
        while ((c = fgetc_unlocked(f)) != EOF) {
            if (c == '\n') { flush(line); line.clear(); }
            else line.push_back(char(c));
        }
        flush(line);
        fclose(f);
        return out;
    }
};
