"""Refit the two middle phases on identical games using margin and outcome labels."""

import ast
import csv
import json
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE = (HERE / "baseline.cpp").read_text()
WIDTHS = (8, 10, 12, 14, 14, 12, 10, 8)
BOARD = sum(1 << (16 * r + (14 - w) // 2 + c) for r, w in enumerate(WIDTHS) for c in range(w))
FLAT = BOARD & (65535 | (65535 << 112))
ANCHORS = 0
SLOPE = 0
for s in range(128):
    bit = 1 << s
    if BOARD & bit:
        axes = sum(bool(BOARD & (bit >> d)) and bool(BOARD & (bit << d)) for d in (1, 15, 16, 17))
        if axes == 0:
            ANCHORS |= bit
        elif axes == 1 and not FLAT & bit:
            SLOPE |= bit
EDGE = FLAT | SLOPE | ANCHORS
PATTERNS = [tuple(map(int, g.split(","))) for g in re.findall(r"patternIndex<([\d, ]+)>\(p\)", SOURCE)]
assert len(PATTERNS) == 12
STATE = {}
for own in range(16):
    for enemy in range(own):
        if own & enemy == 0:
            idx = len(STATE) // 2
            STATE[own, enemy], STATE[enemy, own] = (idx, 1), (idx, -1)


def adjacent(bits):
    result = 0
    for d in (1, 15, 16, 17):
        result |= (bits << d) | (bits >> d)
    return result


def stable(bits):
    total = 0
    for start in (3, 115):
        row = (bits >> start) & 255
        left = row & ~(row + 1)
        right = 0
        for index in range(7, -1, -1):
            if not row & (1 << index):
                break
            right |= 1 << index
        total += ((left | right) & 126).bit_count()
    return total


def features(own, enemy, mobility, anchor_moves):
    def diff(mask):
        return (mask & own).bit_count() - (mask & enemy).bit_count()
    vacant = BOARD & ~(own | enemy)
    exposed = adjacent(ANCHORS & vacant)
    vector = np.zeros(131, dtype=np.int16)
    vector[:11] = (mobility, diff(adjacent(vacant)), anchor_moves, diff(exposed & EDGE),
                   diff(exposed & ~EDGE), stable(own) - stable(enemy), diff(FLAT & ANCHORS),
                   diff(ANCHORS & ~FLAT), diff(FLAT & ~ANCHORS), diff(SLOPE), diff(BOARD))
    for i, pattern in enumerate(PATTERNS):
        a = sum(((own >> s) & 1) << j for j, s in enumerate(pattern))
        b = sum(((enemy >> s) & 1) << j for j, s in enumerate(pattern))
        if a or b:
            k, sign = STATE[a, b]
            vector[11 + (i // 4) * 40 + k] += sign
    return vector


def table(name):
    initializer = re.search(r"\b" + name + r"\[.*?= (\{.*?\});", SOURCE, re.S)[1]
    values = ast.literal_eval(initializer.replace("{", "[").replace("}", "]"))
    return initializer, np.array(values, dtype=int)


def initializer(values):
    return json.dumps(values.tolist()).replace("[", "{").replace("]", "}").replace("}, ", "},\n    ")


def main():
    pattern_text, patterns = table("learnedPatterns")
    weight_text, weights = table("phaseWeights")
    prior = np.column_stack((weights, patterns.reshape(4, 120)))
    vectors, labels = [], []
    with (HERE / "records/training.csv").open() as file:
        for row in csv.reader(file):
            game, empty, margin, lo, hi, elo, ehi, mobility, anchors, score = map(int, row)
            phase = empty // 21
            x = features(lo | (hi << 64), elo | (ehi << 64), mobility, anchors)
            if x @ prior[phase] != score:
                raise ValueError(f"feature mismatch in game {game}")
            vectors.append(x)
            labels.append((game, phase, margin))
    x = np.array(vectors, dtype=float)
    games, phases, margins = np.array(labels).T
    print(f"{len(margins)} positions in {len(set(games))} sampled games")
    for target in ("margin", "outcome"):
        fitted = prior.copy()
        for phase in (1, 2):
            train = (games % 5 != 0) & (phases == phase)
            valid = (games % 5 == 0) & (phases == phase)
            design = x[train]
            y = 288 * np.tanh(margins[train] / 24)
            if target == "outcome":
                # Match the RMS of the margin target so score magnitudes remain comparable.
                outcomes = np.sign(margins[train])
                y = outcomes * np.sqrt((y @ y) / (outcomes @ outcomes))
            delta = np.linalg.solve(design.T @ design + 32 * np.eye(131),
                                    design.T @ (y - design @ prior[phase]))
            fitted[phase] = np.rint(prior[phase] + 0.4 * delta)
            fitted[phase, 11:] = np.clip(fitted[phase, 11:], -127, 127)
            for name, model in (("baseline", prior), (target, fitted)):
                accuracy = np.mean(np.sign(x[valid] @ model[phase]) == np.sign(margins[valid]))
                print(f"{name} phase {phase} held-out outcome accuracy {accuracy:.4f} (n={valid.sum()})")
        cpp = SOURCE.replace(pattern_text, initializer(fitted[:, 11:].reshape(4, 3, 40)))
        cpp = cpp.replace(weight_text, initializer(fitted[:, :11]))
        path = HERE / f"midgame-{target}.cpp"
        path.write_text(f"// Middle phases refitted by fit_midgame.py using {target} labels.\n" + cpp)


if __name__ == "__main__":
    main()
