"""Replay recorded matches and check losing players' choices with the independent solver."""

import argparse
import json
import subprocess
from pathlib import Path

import match


def coordinates(square):
    row, column = square
    return row + 1, column - match.OFFSETS[row] + 1


def verify(executable, seconds, board, side, first, second):
    header = (seconds, *coordinates(first), *coordinates(second))
    data = " ".join(map(str, header)) + "\n" + match.board_input(board, side)
    reply = subprocess.run([executable], input=data, text=True, capture_output=True,
                           check=True, timeout=3 * seconds + 5)
    first_value, second_value, best = map(int, reply.stdout.split())
    return first_value, second_value, best


def audit(record, verifier, seconds, max_empty, loser):
    cells = [square for row in match.ROWS for square in row]
    board = dict(zip(cells, record["board"], strict=True))
    side = record["starting_side"]
    checked = []
    for move in record["moves"]:
        choices = match.legal_moves(board, side)
        if not choices:
            side = 3 - side
            choices = match.legal_moves(board, side)
        row, column = move["row"], move["column"]
        if side != move["side"] or not 1 <= row <= len(match.ROWS) or not 1 <= column <= match.WIDTHS[row - 1]:
            raise ValueError("invalid side or coordinate in game record")
        square = match.ROWS[row - 1][column - 1]
        if square not in choices:
            raise ValueError("illegal recorded move")
        empty = sum(disk == 0 for disk in board.values())
        if side == loser and empty <= max_empty:
            played, _, best = verify(verifier, seconds, board, side, square, square)
            checked.append({"empty": empty, "row": row, "column": column, "played": played, "best": best})
        match.place(board, side, square, choices[square])
        side = 3 - side
    disks = list(board.values())
    candidate = record["candidate_side"]
    if (match.legal_moves(board, 1) or match.legal_moves(board, 2)
            or disks.count(candidate) != record["candidate_disks"]
            or disks.count(3 - candidate) != record["reference_disks"]):
        raise ValueError("replay disagrees with recorded final result")
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("verifier", type=Path)
    parser.add_argument("records", type=Path, nargs="+")
    parser.add_argument("--seconds", type=int, default=2, help="solver time per query")
    parser.add_argument("--max-empty", type=int, default=22)
    args = parser.parse_args()
    if args.seconds < 1 or not 1 <= args.max_empty <= 88:
        parser.error("use positive seconds and 1 to 88 empty cells")
    for path in args.records:
        for line in path.read_text().splitlines():
            game = json.loads(line)
            candidate = game["candidate_side"]
            if "failure" in game:
                print(json.dumps({"file": path.name, "pair": game["pair"], "candidate_side": candidate,
                                  "failure": game["failure"]}), flush=True)
                continue
            margin = game["candidate_disks"] - game["reference_disks"]
            loser = candidate if margin < 0 else 3 - candidate if margin > 0 else None
            checks = audit(game, args.verifier.resolve(), args.seconds, args.max_empty, loser)
            mistakes = [check for check in checks if -1 <= check["played"] < check["best"]]
            print(json.dumps({"file": path.name, "pair": game["pair"], "candidate_side": candidate,
                              "loser": loser, "first_proven_drop": next(iter(mistakes), None),
                              "checks": checks}), flush=True)


if __name__ == "__main__":
    main()
