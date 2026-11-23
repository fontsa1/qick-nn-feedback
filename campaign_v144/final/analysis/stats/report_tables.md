### NN_live - LDA (fir770), 99,400 rows

| Rows | Set | first | second | first - second (points) | 95% CI bootstrap | 95% CI normal | b vs c | exact p | margin (95%) | margin (90%, TOST) |
|---|---|---|---|---|---|---|---|---|---|---|
| all | board A | 95.547 | 95.656 | -0.109 | [-0.169, -0.049] | [-0.169, -0.048] | 422 vs 530 | 0.00052 | 0.169 | 0.160 |
| all | board B | 95.616 | 95.653 | -0.037 | [-0.098, +0.023] | [-0.097, +0.023] | 446 vs 483 | 0.24 | 0.098 | 0.088 |
| all | run-1 mosaic | 95.600 | 95.652 | -0.051 | [-0.111, +0.008] | [-0.110, +0.008] | 423 vs 474 | 0.09 | 0.111 | 0.101 |
| all | both boards pooled (row-clustered) | | | -0.073 | [-0.121, -0.025] | [-0.121, -0.025] | 868 vs 1013 (198,800 shots) | sign-flip 0.0026 (naive summed McNemar 0.00089) | 0.121 | 0.113 |

### NN_live - LDA (fir576), 99,400 rows

| Rows | Set | first | second | first - second (points) | 95% CI bootstrap | 95% CI normal | b vs c | exact p | margin (95%) | margin (90%, TOST) |
|---|---|---|---|---|---|---|---|---|---|---|
| all | board A | 95.547 | 95.524 | +0.023 | [-0.023, +0.070] | [-0.024, +0.070] | 294 vs 271 | 0.35 | 0.070 | 0.062 |
| all | board B | 95.616 | 95.565 | +0.050 | [+0.005, +0.096] | [+0.005, +0.095] | 287 vs 237 | 0.03 | 0.096 | 0.088 |
| all | run-1 mosaic | 95.600 | 95.570 | +0.030 | [-0.014, +0.075] | [-0.014, +0.075] | 271 vs 241 | 0.20 | 0.075 | 0.067 |
| all | both boards pooled (row-clustered) | | | +0.037 | [+0.002, +0.071] | [+0.002, +0.072] | 581 vs 508 (198,800 shots) | sign-flip 0.04 (naive summed McNemar 0.03) | 0.071 | 0.066 |

### NN_live - LDA (box576), 99,400 rows

| Rows | Set | first | second | first - second (points) | 95% CI bootstrap | 95% CI normal | b vs c | exact p | margin (95%) | margin (90%, TOST) |
|---|---|---|---|---|---|---|---|---|---|---|
| all | board A | 95.547 | 95.465 | +0.082 | [+0.030, +0.134] | [+0.031, +0.134] | 383 vs 301 | 0.0019 | 0.134 | 0.125 |
| all | board B | 95.616 | 95.475 | +0.141 | [+0.089, +0.192] | [+0.090, +0.192] | 409 vs 269 | 8.5e-08 | 0.192 | 0.184 |
| all | run-1 mosaic | 95.600 | 95.472 | +0.129 | [+0.077, +0.180] | [+0.078, +0.180] | 399 vs 271 | 8.6e-07 | 0.180 | 0.172 |
| all | both boards pooled (row-clustered) | | | +0.112 | [+0.072, +0.151] | [+0.072, +0.151] | 792 vs 570 (198,800 shots) | sign-flip 5e-06 (naive summed McNemar 2e-09) | 0.151 | 0.144 |

### NN_live - LDA (fir770), fresh 80,000 vs development 19,400

| Rows | Set | first | second | first - second (points) | 95% CI bootstrap | 95% CI normal | b vs c | exact p | margin (95%) | margin (90%, TOST) |
|---|---|---|---|---|---|---|---|---|---|---|
| fresh | board A | 95.585 | 95.722 | -0.138 | [-0.206, -0.069] | [-0.205, -0.070] | 328 vs 438 | 8e-05 | 0.206 | 0.195 |
| fresh | board B | 95.651 | 95.696 | -0.045 | [-0.111, +0.020] | [-0.111, +0.021] | 342 vs 378 | 0.19 | 0.111 | 0.101 |
| fresh | run-1 mosaic | 95.651 | 95.718 | -0.066 | [-0.131, -0.001] | [-0.132, -0.001] | 329 vs 382 | 0.05 | 0.131 | 0.120 |
| fresh | both boards pooled (row-clustered) | | | -0.091 | [-0.145, -0.039] | [-0.144, -0.038] | 670 vs 816 (160,000 shots) | sign-flip 0.00077 (naive summed McNemar 0.00017) | 0.145 | 0.136 |
| dev | board A | 95.391 | 95.381 | +0.010 | [-0.129, +0.144] | [-0.128, +0.148] | 94 vs 92 | 0.94 | 0.144 | 0.124 |
| dev | board B | 95.468 | 95.473 | -0.005 | [-0.150, +0.144] | [-0.151, +0.141] | 104 vs 105 | 1.00 | 0.150 | 0.129 |
| dev | run-1 mosaic | 95.391 | 95.381 | +0.010 | [-0.129, +0.144] | [-0.128, +0.148] | 94 vs 92 | 0.94 | 0.144 | 0.124 |
| dev | both boards pooled (row-clustered) | | | +0.003 | [-0.108, +0.116] | [-0.109, +0.114] | 198 vs 197 (38,800 shots) | sign-flip 1.00 (naive summed McNemar 1.00) | 0.116 | 0.098 |

### NN_live - LDA (fir576), fresh 80,000 vs development 19,400

| Rows | Set | first | second | first - second (points) | 95% CI bootstrap | 95% CI normal | b vs c | exact p | margin (95%) | margin (90%, TOST) |
|---|---|---|---|---|---|---|---|---|---|---|
| fresh | board A | 95.585 | 95.556 | +0.029 | [-0.024, +0.080] | [-0.024, +0.081] | 242 vs 219 | 0.31 | 0.080 | 0.072 |
| fresh | board B | 95.651 | 95.600 | +0.051 | [+0.001, +0.101] | [+0.002, +0.101] | 226 vs 185 | 0.05 | 0.101 | 0.092 |
| fresh | run-1 mosaic | 95.651 | 95.614 | +0.037 | [-0.013, +0.087] | [-0.012, +0.087] | 219 vs 189 | 0.15 | 0.087 | 0.079 |
| fresh | both boards pooled (row-clustered) | | | +0.040 | [+0.001, +0.079] | [+0.001, +0.079] | 468 vs 404 (160,000 shots) | sign-flip 0.05 (naive summed McNemar 0.03) | 0.079 | 0.073 |
| dev | board A | 95.391 | 95.391 | -0.000 | [-0.103, +0.103] | [-0.103, +0.103] | 52 vs 52 | 1.00 | 0.103 | 0.088 |
| dev | board B | 95.468 | 95.422 | +0.046 | [-0.062, +0.155] | [-0.061, +0.154] | 61 vs 52 | 0.45 | 0.155 | 0.139 |
| dev | run-1 mosaic | 95.391 | 95.391 | -0.000 | [-0.103, +0.103] | [-0.103, +0.103] | 52 vs 52 | 1.00 | 0.103 | 0.088 |
| dev | both boards pooled (row-clustered) | | | +0.023 | [-0.057, +0.106] | [-0.058, +0.104] | 113 vs 104 (38,800 shots) | sign-flip 0.62 (naive summed McNemar 0.59) | 0.106 | 0.090 |

### NN_live - LDA (box576), fresh 80,000 vs development 19,400

| Rows | Set | first | second | first - second (points) | 95% CI bootstrap | 95% CI normal | b vs c | exact p | margin (95%) | margin (90%, TOST) |
|---|---|---|---|---|---|---|---|---|---|---|
| fresh | board A | 95.585 | 95.487 | +0.098 | [+0.040, +0.155] | [+0.040, +0.155] | 315 vs 237 | 0.001 | 0.155 | 0.145 |
| fresh | board B | 95.651 | 95.504 | +0.147 | [+0.090, +0.205] | [+0.090, +0.205] | 331 vs 213 | 4.8e-07 | 0.205 | 0.196 |
| fresh | run-1 mosaic | 95.651 | 95.496 | +0.155 | [+0.097, +0.211] | [+0.098, +0.212] | 331 vs 207 | 1e-07 | 0.211 | 0.202 |
| fresh | both boards pooled (row-clustered) | | | +0.122 | [+0.079, +0.167] | [+0.078, +0.167] | 646 vs 450 (160,000 shots) | sign-flip 5e-06 (naive summed McNemar 3.5e-09) | 0.167 | 0.159 |
| dev | board A | 95.391 | 95.371 | +0.020 | [-0.093, +0.134] | [-0.095, +0.136] | 68 vs 64 | 0.79 | 0.134 | 0.118 |
| dev | board B | 95.468 | 95.355 | +0.113 | [-0.005, +0.232] | [-0.004, +0.230] | 78 vs 56 | 0.07 | 0.232 | 0.211 |
| dev | run-1 mosaic | 95.391 | 95.371 | +0.020 | [-0.098, +0.139] | [-0.095, +0.136] | 68 vs 64 | 0.79 | 0.139 | 0.118 |
| dev | both boards pooled (row-clustered) | | | +0.067 | [-0.023, +0.154] | [-0.022, +0.156] | 146 vs 120 (38,800 shots) | sign-flip 0.16 (naive summed McNemar 0.13) | 0.154 | 0.141 |

### boxcar NN_live - FIR-path network (emulated), all / fresh / dev

| Rows | Set | first | second | first - second (points) | 95% CI bootstrap | 95% CI normal | b vs c | exact p | margin (95%) | margin (90%, TOST) |
|---|---|---|---|---|---|---|---|---|---|---|
| all | board A | 95.547 | 95.463 | +0.085 | [+0.036, +0.133] | [+0.036, +0.133] | 343 vs 259 | 0.0007 | 0.133 | 0.126 |
| all | board B | 95.616 | 95.494 | +0.122 | [+0.074, +0.170] | [+0.073, +0.170] | 361 vs 240 | 9.1e-07 | 0.170 | 0.162 |
| all | run-1 mosaic | 95.600 | 95.474 | +0.127 | [+0.078, +0.174] | [+0.079, +0.174] | 353 vs 227 | 1.9e-07 | 0.174 | 0.167 |
| all | both boards pooled (row-clustered) | | | +0.103 | [+0.066, +0.140] | [+0.066, +0.140] | 704 vs 499 (198,800 shots) | sign-flip 5e-06 (naive summed McNemar 3.7e-09) | 0.140 | 0.134 |
| fresh | board A | 95.585 | 95.489 | +0.096 | [+0.042, +0.150] | [+0.042, +0.150] | 281 vs 204 | 0.00055 | 0.150 | 0.143 |
| fresh | board B | 95.651 | 95.514 | +0.138 | [+0.085, +0.191] | [+0.084, +0.191] | 290 vs 180 | 4.4e-07 | 0.191 | 0.182 |
| fresh | run-1 mosaic | 95.651 | 95.502 | +0.149 | [+0.095, +0.201] | [+0.096, +0.201] | 291 vs 172 | 3.5e-08 | 0.201 | 0.193 |
| fresh | both boards pooled (row-clustered) | | | +0.117 | [+0.076, +0.158] | [+0.076, +0.158] | 571 vs 384 (160,000 shots) | sign-flip 5e-06 (naive summed McNemar 1.6e-09) | 0.158 | 0.151 |
| dev | board A | 95.391 | 95.355 | +0.036 | [-0.072, +0.144] | [-0.073, +0.145] | 62 vs 55 | 0.58 | 0.144 | 0.129 |
| dev | board B | 95.468 | 95.412 | +0.057 | [-0.057, +0.170] | [-0.059, +0.172] | 71 vs 60 | 0.38 | 0.170 | 0.155 |
| dev | run-1 mosaic | 95.391 | 95.355 | +0.036 | [-0.072, +0.144] | [-0.073, +0.145] | 62 vs 55 | 0.58 | 0.144 | 0.129 |
| dev | both boards pooled (row-clustered) | | | +0.046 | [-0.039, +0.131] | [-0.039, +0.132] | 133 vs 115 (38,800 shots) | sign-flip 0.31 (naive summed McNemar 0.28) | 0.131 | 0.119 |

### NN_axi (EMULATED on the live session's FIR buffer) - NN_live

| Rows | Set | first | second | first - second (points) | 95% CI bootstrap | 95% CI normal | b vs c | exact p | margin (95%) | margin (90%, TOST) |
|---|---|---|---|---|---|---|---|---|---|---|
| all | board A | 95.655 | 95.547 | +0.108 | [+0.050, +0.164] | [+0.050, +0.165] | 476 vs 369 | 0.00026 | 0.164 | 0.156 |
| all | board B | 95.672 | 95.616 | +0.056 | [-0.000, +0.113] | [+0.000, +0.113] | 435 vs 379 | 0.05 | 0.113 | 0.104 |
| all | run-1 mosaic | 95.665 | 95.600 | +0.064 | [+0.007, +0.122] | [+0.008, +0.121] | 444 vs 380 | 0.03 | 0.122 | 0.113 |
| all | both boards pooled (row-clustered) | | | +0.082 | [+0.037, +0.127] | [+0.037, +0.127] | 911 vs 748 (198,800 shots) | sign-flip 0.00035 (naive summed McNemar 6.9e-05) | 0.127 | 0.120 |
| fresh | board A | 95.704 | 95.585 | +0.119 | [+0.056, +0.182] | [+0.055, +0.182] | 383 vs 288 | 0.00028 | 0.182 | 0.172 |
| fresh | board B | 95.718 | 95.651 | +0.066 | [+0.005, +0.129] | [+0.004, +0.128] | 347 vs 294 | 0.04 | 0.129 | 0.119 |
| fresh | run-1 mosaic | 95.716 | 95.651 | +0.065 | [+0.004, +0.128] | [+0.003, +0.127] | 351 vs 299 | 0.05 | 0.128 | 0.119 |
| fresh | both boards pooled (row-clustered) | | | +0.092 | [+0.044, +0.142] | [+0.043, +0.142] | 730 vs 582 (160,000 shots) | sign-flip 0.00027 (naive summed McNemar 4.9e-05) | 0.142 | 0.134 |
| dev | board A | 95.453 | 95.391 | +0.062 | [-0.072, +0.196] | [-0.071, +0.195] | 93 vs 81 | 0.40 | 0.196 | 0.175 |
| dev | board B | 95.484 | 95.468 | +0.015 | [-0.119, +0.149] | [-0.118, +0.148] | 88 vs 85 | 0.88 | 0.149 | 0.124 |
| dev | run-1 mosaic | 95.453 | 95.391 | +0.062 | [-0.067, +0.196] | [-0.071, +0.195] | 93 vs 81 | 0.40 | 0.196 | 0.175 |
| dev | both boards pooled (row-clustered) | | | +0.039 | [-0.065, +0.142] | [-0.066, +0.143] | 181 vs 166 (38,800 shots) | sign-flip 0.50 (naive summed McNemar 0.45) | 0.142 | 0.126 |

### NN_axi (emulated) - LDA fir770

| Rows | Set | first | second | first - second (points) | 95% CI bootstrap | 95% CI normal | b vs c | exact p | margin (95%) | margin (90%, TOST) |
|---|---|---|---|---|---|---|---|---|---|---|
| all | board A | 95.655 | 95.656 | -0.001 | [-0.054, +0.051] | [-0.054, +0.052] | 357 vs 358 | 1.00 | 0.054 | 0.045 |
| all | board B | 95.672 | 95.653 | +0.019 | [-0.032, +0.070] | [-0.032, +0.070] | 342 vs 323 | 0.49 | 0.070 | 0.062 |
| all | run-1 mosaic | 95.665 | 95.652 | +0.013 | [-0.037, +0.064] | [-0.038, +0.064] | 341 vs 328 | 0.64 | 0.064 | 0.055 |
| all | both boards pooled (row-clustered) | | | +0.009 | [-0.031, +0.050] | [-0.031, +0.050] | 699 vs 681 (198,800 shots) | sign-flip 0.68 (naive summed McNemar 0.65) | 0.050 | 0.044 |
| fresh | board A | 95.704 | 95.722 | -0.019 | [-0.076, +0.039] | [-0.076, +0.039] | 266 vs 281 | 0.55 | 0.076 | 0.067 |
| fresh | board B | 95.718 | 95.696 | +0.021 | [-0.035, +0.077] | [-0.035, +0.077] | 272 vs 255 | 0.49 | 0.077 | 0.068 |
| fresh | run-1 mosaic | 95.716 | 95.718 | -0.001 | [-0.056, +0.054] | [-0.056, +0.054] | 250 vs 251 | 1.00 | 0.056 | 0.048 |
| fresh | both boards pooled (row-clustered) | | | +0.001 | [-0.044, +0.046] | [-0.043, +0.046] | 538 vs 536 (160,000 shots) | sign-flip 0.98 (naive summed McNemar 0.98) | 0.046 | 0.039 |
| dev | board A | 95.453 | 95.381 | +0.072 | [-0.057, +0.206] | [-0.059, +0.203] | 91 vs 77 | 0.32 | 0.206 | 0.180 |
| dev | board B | 95.484 | 95.473 | +0.010 | [-0.108, +0.129] | [-0.108, +0.129] | 70 vs 68 | 0.93 | 0.129 | 0.108 |
| dev | run-1 mosaic | 95.453 | 95.381 | +0.072 | [-0.057, +0.206] | [-0.059, +0.203] | 91 vs 77 | 0.32 | 0.206 | 0.181 |
| dev | both boards pooled (row-clustered) | | | +0.041 | [-0.054, +0.139] | [-0.056, +0.138] | 161 vs 145 (38,800 shots) | sign-flip 0.44 (naive summed McNemar 0.39) | 0.139 | 0.124 |

### Fidelity by row subset (NN_live chip; NN_axi emulated)

| Rows | Set | NN_live | 95% CI | NN_axi emulated | 95% CI |
|---|---|---|---|---|---|
| all | A | 95.547 | [95.42, 95.67] | 95.655 | [95.53, 95.78] |
| all | B | 95.616 | [95.49, 95.74] | 95.672 | [95.55, 95.80] |
| all | mosaic | 95.600 | [95.47, 95.73] | 95.665 | [95.54, 95.79] |
| all | pooled_AB | 95.581 | [95.49, 95.67] | 95.663 | [95.57, 95.75] |
| fresh | A | 95.585 | [95.44, 95.73] | 95.704 | [95.56, 95.84] |
| fresh | B | 95.651 | [95.51, 95.79] | 95.718 | [95.58, 95.86] |
| fresh | mosaic | 95.651 | [95.51, 95.79] | 95.716 | [95.58, 95.86] |
| fresh | pooled_AB | 95.618 | [95.52, 95.72] | 95.711 | [95.61, 95.81] |
| dev | A | 95.391 | [95.10, 95.69] | 95.453 | [95.16, 95.74] |
| dev | B | 95.468 | [95.18, 95.76] | 95.484 | [95.19, 95.77] |
| dev | mosaic | 95.391 | [95.10, 95.69] | 95.453 | [95.16, 95.74] |
| dev | pooled_AB | 95.430 | [95.22, 95.64] | 95.468 | [95.26, 95.67] |

### board B - board A, same rows

| Classifier | Rows | B - A | 95% CI normal | 95% CI bootstrap | B-only vs A-only | exact p |
|---|---|---|---|---|---|---|
| NN_live | all | +0.068 | [+0.000, +0.136] | [+0.001, +0.135] | 628 vs 560 | 0.05 |
| NN_live | dev | +0.077 | [-0.087, +0.242] | [-0.088, +0.237] | 140 vs 125 | 0.39 |
| NN_live | fresh | +0.066 | [-0.008, +0.141] | [-0.009, +0.141] | 488 vs 435 | 0.09 |
| NN_axi emulated on live FIR | all | +0.017 | [-0.044, +0.078] | [-0.044, +0.078] | 487 vs 470 | 0.61 |
| NN_axi emulated on live FIR | dev | +0.031 | [-0.120, +0.182] | [-0.119, +0.186] | 115 vs 109 | 0.74 |
| NN_axi emulated on live FIR | fresh | +0.014 | [-0.053, +0.080] | [-0.052, +0.080] | 372 vs 361 | 0.71 |
| NN_axi on chip | dev | -0.098 | [-0.253, +0.057] | [-0.253, +0.057] | 108 vs 127 | 0.24 |

Boards' NN_live decisions agree on 98.80% of the 99,400 traces.

### on-chip NN_axi (its own session) vs NN_axi emulated on the NN_live session's FIR buffer, rows 0-19,999 minus map rows

| Board | decisions agree | on-chip NN_axi | emulated (live FIR) | chip - emulated | 95% CI | b vs c | exact p |
|---|---|---|---|---|---|---|---|
| A | 98.95% | 95.545 | 95.453 | +0.093 | [-0.052, +0.237] | 111 vs 93 | 0.23 |
| B | 98.78% | 95.447 | 95.484 | -0.036 | [-0.191, +0.118] | 115 vs 122 | 0.70 |

Boxcar emulator equals the chip's NN_live decision on {'A': 100000, 'B': 100000} of 100,000 shots per board.
