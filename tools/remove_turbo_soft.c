// SPDX-License-Identifier: GPL-3.0-or-later
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "turbofec/rate_match.h"
#include "turbofec/turbo.h"

static int write_file(const char *path, const void *data, size_t size)
{
    FILE *handle = fopen(path, "wb");
    if (!handle) {
        fprintf(stderr, "cannot open %s: %s\n", path, strerror(errno));
        return -1;
    }
    if (fwrite(data, 1, size, handle) != size) {
        fprintf(stderr, "short write to %s\n", path);
        fclose(handle);
        return -1;
    }
    fclose(handle);
    return 0;
}

int main(int argc, char **argv)
{
    enum { E = 7200, D = 1412, K = 1408, OUT_BYTES = 176 };
    if (argc != 4) {
        fprintf(stderr, "usage: %s INPUT_INT8 OUTPUT_PREFIX ITERATIONS\n", argv[0]);
        return 2;
    }

    int iterations = atoi(argv[3]);
    if (iterations < 1 || iterations > 32) {
        fprintf(stderr, "iterations must be between 1 and 32\n");
        return 2;
    }

    int8_t input[E];
    FILE *handle = fopen(argv[1], "rb");
    if (!handle) {
        fprintf(stderr, "cannot open %s: %s\n", argv[1], strerror(errno));
        return 2;
    }
    size_t got = fread(input, 1, E, handle);
    int extra = fgetc(handle);
    fclose(handle);
    if (got != E || extra != EOF) {
        fprintf(stderr, "input must contain exactly %d signed int8 values\n", E);
        return 2;
    }

    int8_t d0[D] = {0};
    int8_t d1[D] = {0};
    int8_t d2[D] = {0};
    uint8_t decoded[OUT_BYTES] = {0};

    struct lte_rate_matcher *matcher = lte_rate_matcher_alloc();
    struct tdecoder *decoder = alloc_tdec();
    if (!matcher || !decoder) {
        fprintf(stderr, "decoder allocation failed\n");
        return 3;
    }

    struct lte_rate_matcher_io io = {
        .D = D,
        .E = E,
        .d = {d0, d1, d2},
        .e = input,
    };
    int status = lte_rate_match_rv(matcher, &io, 0);
    if (status == 0)
        status = lte_turbo_decode(decoder, K, iterations, decoded, d0, d1, d2);

    char path[4096];
    snprintf(path, sizeof(path), "%s_d0.bin", argv[2]);
    if (write_file(path, d0, sizeof(d0)) != 0) status = -1;
    snprintf(path, sizeof(path), "%s_d1.bin", argv[2]);
    if (write_file(path, d1, sizeof(d1)) != 0) status = -1;
    snprintf(path, sizeof(path), "%s_d2.bin", argv[2]);
    if (write_file(path, d2, sizeof(d2)) != 0) status = -1;
    snprintf(path, sizeof(path), "%s_transport_176.bin", argv[2]);
    if (write_file(path, decoded, sizeof(decoded)) != 0) status = -1;

    free_tdec(decoder);
    lte_rate_matcher_free(matcher);
    if (status != 0) {
        fprintf(stderr, "decode failed: %d\n", status);
        return 4;
    }
    return 0;
}
