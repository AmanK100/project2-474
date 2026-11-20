"""Compare both proof schedules on fresh positions eligible for the earlier switch."""

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tests"))
from audit_games import coordinates, verify
import match


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--winning", action="store_true",
                        help="use six additional roots proved winnable before running either player")
    args = parser.parse_args()
    rng = random.Random(800813 if args.winning else 113882)
    baseline = HERE / "bin/baseline"
    candidate = HERE / "bin/early-proof"
    for i in range(6 if args.winning else 18):
        empty = 20 + i % 3
        while True:
            position = match.opening(rng, 84 - empty)
            if position:
                board, side = position
                choices = match.legal_moves(board, side)
                if 2 <= len(choices) <= 8:
                    if args.winning:
                        first = next(iter(choices))
                        _, _, root = verify(HERE / "bin/verify", 1, board, side, first, first)
                        if root != 1:
                            continue
                    break
        # Reverse execution order on alternate fixtures.
        programs = (baseline, candidate) if i % 2 == 0 else (candidate, baseline)
        results = {p: match.ask_player(p, board, side, choices) for p in programs}
        base_move, base_time = results[baseline]
        new_move, new_time = results[candidate]
        base_value, new_value, best = verify(HERE / "bin/verify", 3, board, side, base_move, new_move)
        if args.winning:
            if best not in (1, -9):
                raise ValueError("independent searches disagree on a proved win")
            best = 1
        print(json.dumps({"id": i + 1, "empty": empty, "legal": len(choices),
                          "board": list(map(int, match.board_input(board, side).split())),
                          "base_move": coordinates(base_move), "new_move": coordinates(new_move),
                          "base_seconds": base_time, "new_seconds": new_time,
                          "base": base_value, "new": new_value, "best": best}), flush=True)


if __name__ == "__main__":
    main()
