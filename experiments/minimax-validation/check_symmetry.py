"""Test mirrored copies of two independently scored, unique-best-move positions."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import match
from audit_games import coordinates


def main():
    old = ROOT / "experiments/winrate/records"
    outcomes = {}
    for line in (old / "missed-win-moves.jsonl").read_text().splitlines():
        proof = json.loads(line)
        for key in ("first", "second"):
            outcomes[tuple(proof[key])] = proof[key + "_value"]
    draw = next(row for row in map(json.loads, (HERE / "results/tactics.jsonl").read_text().splitlines())
                if row["case"] == "only-draw")
    draws = {(r, c): (v > 0) - (v < 0) for r, c, v in draw["alternatives"]}
    for label, data, values in (("win-21", (old / "missed-win.board").read_text(), outcomes),
                                ("only-draw", draw["board"], draws)):
        cells = [sq for row in match.ROWS for sq in row]
        original = dict(zip(cells, map(int, data.split()), strict=True))
        for vertical in (False, True):
            for horizontal in (False, True):
                def transform(square):
                    r, c = square
                    return (7 - r if vertical else r, 13 - c if horizontal else c)
                board = {transform(sq): disk for sq, disk in original.items()}
                legal = match.legal_moves(board, 1)
                transformed = {transform(match.ROWS[r-1][c-1]): v for (r, c), v in values.items()}
                assert set(legal) == set(transformed)
                best = max(values.values())
                unique, = [sq for sq, value in transformed.items() if value == best]
                for attempt in range(2):
                    sq, wall = match.ask_player(HERE / "bin/player", board, 1, legal)
                    print(json.dumps(dict(case=label, vertical=vertical, horizontal=horizontal,
                                          attempt=attempt + 1, board=match.board_input(board, 1),
                                          expected=coordinates(unique), actual=coordinates(sq),
                                          chosen=transformed[sq], best=best, wall_s=wall)), flush=True)


if __name__ == "__main__":
    main()
