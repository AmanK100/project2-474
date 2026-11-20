"""Test endgames through the unchanged CLI, with independent outcomes or exact margins."""

import json
import random
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / "experiments/winrate/records"
sys.path.insert(0, str(ROOT / "tests"))
import match
from audit_games import coordinates, verify


def read_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def positions():
    if "--stress" in sys.argv:
        rng = random.Random(519773)
        for empty in (21, 22, 23, 24):
            for case in range(3):
                while True:
                    pos = match.opening(rng, 84 - empty)
                    if pos and len(match.legal_moves(*pos)) >= 2:
                        break
                yield f"fresh-{empty}-{case + 1}", *pos, {}
        return
    rng = random.Random(152907)
    for empty in (11, 12, 13, 14, 16, 18, 20):
        for case in range(4):
            while True:
                pos = match.opening(rng, 84 - empty)
                if pos and len(match.legal_moves(*pos)) >= 2:
                    break
            yield f"fresh-{empty}-{case + 1}", *pos, {}
    original = read_lines(OLD / "proofs.jsonl")
    for supplement in ("long-proofs.jsonl", "deep-proofs.jsonl"):
        for row in read_lines(OLD / supplement):
            for key in ("base", "new", "best"):
                if row[key] != -9:
                    original[row["id"] - 1][key] = row[key]
    winners = [("set", row) for row in original if row["best"] == 1]
    winners += [("winning", row) for row in read_lines(OLD / "winning-proofs.jsonl")]
    assert len(winners) == 10
    cells = [sq for row in match.ROWS for sq in row]
    for group, row in winners:
        board = dict(zip(cells, row["board"], strict=True))
        cache = {tuple(row[f"{k}_move"]): row[k] for k in ("base", "new") if row[k] != -9}
        if group == "set" and row["id"] == 14:
            for pair in read_lines(OLD / "missed-win-moves.jsonl"):
                for key in ("first", "second"):
                    cache[tuple(pair[key])] = pair[f"{key}_value"]
        yield f"{group}-{row['id']}", board, 1, cache


def sign(value):
    return (value > 0) - (value < 0)


def main():
    for label, board, side, cache in positions():
        moves = match.legal_moves(board, side)
        chosen, wall = match.ask_player(HERE / "bin/player", board, side, moves)
        empty = list(board.values()).count(0)
        data = match.board_input(board, side)
        row = dict(case=label, empty=empty, board=data, legal=len(moves),
                   move=coordinates(chosen), wall_s=wall)
        if empty <= 13:
            result = subprocess.run([HERE / "bin/truth"], input=data, text=True, capture_output=True,
                                    check=True, timeout=60)
            v = list(map(int, result.stdout.split()))
            margins = dict(zip(v[::4], v[1::4], strict=True))
            margin = margins[chosen[0] * 16 + chosen[1]]
            best = max(margins.values())
            row.update(margin=margin, best_margin=best, chosen=sign(margin), best=sign(best),
                       source="fresh exact margin")
        elif row["move"] in cache:
            row.update(chosen=cache[row["move"]], best=1, source="archived independent move proof")
        else:
            seconds = 4
            value, _, best = verify(HERE / "bin/verify", seconds, board, side, chosen, chosen)
            if not label.startswith("fresh-"):
                assert best in (1, -9)
                best = 1
            if value == -9 or best == -9:
                seconds = 15
                retry, _, root = verify(HERE / "bin/verify", seconds, board, side, chosen, chosen)
                if value == -9:
                    value = retry
                if best == -9:
                    best = root
            row.update(chosen=value, best=best, seconds_per_query=seconds, source="fresh move proof")
        print(json.dumps(row), flush=True)


if __name__ == "__main__":
    main()
