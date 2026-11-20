"""Play paired games between two compiled players using the project stdin/stdout format."""

import argparse
import json
import random
import subprocess
import time
from contextlib import nullcontext
from pathlib import Path


WIDTHS = (8, 10, 12, 14, 14, 12, 10, 8)
OFFSETS = tuple((14 - width) // 2 for width in WIDTHS)
ROWS = tuple(tuple((r, c + OFFSETS[r]) for c in range(w)) for r, w in enumerate(WIDTHS))
DIRECTIONS = tuple((dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc)


def legal_moves(board, side):
    moves = {}
    for (r, c), disk in board.items():
        if disk:
            continue
        flips = []
        for dr, dc in DIRECTIONS:
            y, x = r + dr, c + dc
            ray = []
            while board.get((y, x)) == 3 - side:
                ray.append((y, x))
                y, x = y + dr, x + dc
            if board.get((y, x)) == side:
                flips.extend(ray)
        if flips:
            moves[r, c] = flips
    return moves


def place(board, side, square, flips):
    board[square] = side
    for cell in flips:
        board[cell] = side


def opening(rng, plies):
    board = {cell: 0 for row in ROWS for cell in row}
    board[3, 6] = board[4, 7] = 1
    board[3, 7] = board[4, 6] = 2
    side = 1
    for _ in range(plies):
        moves = legal_moves(board, side)
        if not moves:
            side = 3 - side
            moves = legal_moves(board, side)
            if not moves:
                break
        square = rng.choice(list(moves))
        place(board, side, square, moves[square])
        side = 3 - side
    if legal_moves(board, side) or legal_moves(board, 3 - side):
        return board, side
    return None


def board_input(board, side):
    values = ("0", "1", "2") if side == 1 else ("0", "2", "1")
    return "".join(" ".join(values[board[cell]] for cell in row) + "\n" for row in ROWS)


def ask_player(executable, board, side, moves):
    data = board_input(board, side)
    start = time.monotonic()
    reply = subprocess.run([executable], input=data, text=True, capture_output=True,
                           check=True, timeout=3)
    elapsed = time.monotonic() - start
    if elapsed > 3:
        raise RuntimeError(f"{executable} took {elapsed:.3f} seconds")
    try:
        row, col = map(int, reply.stdout.split())
        if not 1 <= row <= len(ROWS) or not 1 <= col <= WIDTHS[row - 1]:
            raise ValueError
        square = ROWS[row - 1][col - 1]
        if square not in moves:
            raise ValueError
    except ValueError:
        raise RuntimeError(f"{executable} returned an invalid move {reply.stdout!r}") from None
    return square, elapsed


class TurnFailure(RuntimeError):
    def __init__(self, side, executable, cause):
        self.side = side
        super().__init__(f"{executable} failed on side {side}: {cause}")


def game(board, side, candidate_side, candidate, reference, history=None):
    board = board.copy()
    slowest = 0.0
    while True:
        moves = legal_moves(board, side)
        if not moves:
            side = 3 - side
            moves = legal_moves(board, side)
            if not moves:
                break
        executable = candidate if side == candidate_side else reference
        try:
            square, elapsed = ask_player(executable, board, side, moves)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            raise TurnFailure(side, executable, exc) from exc
        if history is not None:
            r, c = square
            history.append({"side": side, "row": r + 1, "column": c - OFFSETS[r] + 1,
                            "seconds": round(elapsed, 6)})
        if side == candidate_side:
            slowest = max(slowest, elapsed)
        place(board, side, square, moves[square])
        side = 3 - side
    disks = list(board.values())
    return disks.count(candidate_side), disks.count(3 - candidate_side), slowest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("--pairs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=474)
    parser.add_argument("--opening-plies", type=int, default=0,
                        help="random legal placements before the two players take over")
    parser.add_argument("--max-opening-choices", type=int,
                        help="sample openings with 2 to this many legal first moves")
    parser.add_argument("--record", type=Path, help="create a JSON Lines file with replayable games")
    args = parser.parse_args()
    if args.pairs < 1 or not 0 <= args.opening_plies <= 83:
        parser.error("use a positive pair count and 0 to 83 opening plies")
    if args.max_opening_choices is not None and args.max_opening_choices < 2:
        parser.error("the opening choice limit must be at least 2")
    rng = random.Random(args.seed)
    wins = draws = losses = 0
    output = args.record.open("x") if args.record else nullcontext()
    with output as records:
        for pair in range(1, args.pairs + 1):
            for _ in range(1000):
                position = opening(rng, args.opening_plies)
                if position is None:
                    continue
                if args.max_opening_choices is None or 2 <= len(legal_moves(*position)) <= args.max_opening_choices:
                    break
            else:
                parser.error("no eligible opening after 1000 attempts")
            board, side = position
            for candidate_side in (1, 2):
                history = [] if records else None
                if records:
                    record = {"seed": args.seed, "opening_plies": args.opening_plies, "pair": pair,
                              "candidate": args.candidate.name, "reference": args.reference.name,
                              "candidate_side": candidate_side, "starting_side": side,
                              "board": list(map(int, board_input(board, 1).split())), "moves": history}
                    if args.max_opening_choices is not None:
                        record["max_opening_choices"] = args.max_opening_choices
                try:
                    ours, theirs, elapsed = game(board, side, candidate_side,
                                                 args.candidate.resolve(), args.reference.resolve(), history)
                except TurnFailure as exc:
                    if records:
                        record["failure"] = {"side": exc.side, "reason": str(exc)}
                        print(json.dumps(record, separators=(",", ":")), file=records, flush=True)
                    raise
                if records:
                    record.update(candidate_disks=ours, reference_disks=theirs)
                    print(json.dumps(record, separators=(",", ":")), file=records, flush=True)
                wins += ours > theirs
                draws += ours == theirs
                losses += ours < theirs
                print(f"Pair {pair}, candidate side {candidate_side}: {ours}-{theirs}, "
                      f"slowest candidate move {elapsed:.3f}s", flush=True)
    print(f"Candidate: {wins} wins, {draws} draws, {losses} losses")


if __name__ == "__main__":
    main()
