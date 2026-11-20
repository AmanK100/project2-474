"""Check alpha-beta against plain minimax and the normal executable against an exact solver."""

import argparse
import random
import subprocess
from pathlib import Path

import match


def plain_minimax(board, side, depth, evaluation="disk"):
    choices = match.legal_moves(board, side)
    disks = list(board.values())
    margin = disks.count(side) - disks.count(3 - side)
    if not choices:
        if match.legal_moves(board, 3 - side):
            score, _ = plain_minimax(board, 3 - side, depth, evaluation)
            return -score, set()
        terminal_offset = len(board)
        if evaluation != "disk":
            terminal_offset *= 2 * len(board) + 2
        return margin + terminal_offset * ((margin > 0) - (margin < 0)), set()
    if depth == 0:
        if evaluation == "mobility" or (evaluation == "phase" and disks.count(0) > 22):
            mobility = len(choices) - len(match.legal_moves(board, 3 - side))
            return mobility * (2 * len(board) + 1) + margin, set()
        return margin, set()
    scores = {}
    for square, flips in choices.items():
        child = board.copy()
        match.place(child, side, square, flips)
        opponent_score, _ = plain_minimax(child, 3 - side, depth - 1, evaluation)
        scores[16 * square[0] + square[1]] = -opponent_score
    best = max(scores.values())
    return best, {sq for sq, score in scores.items() if score == best}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("player", type=Path)
    parser.add_argument("probe", type=Path)
    parser.add_argument("truth", type=Path)
    parser.add_argument("--evaluation", choices=("disk", "mobility", "phase"), default="phase",
                        help="cutoff evaluation used by the binaries under test")
    args = parser.parse_args()
    rng = random.Random(328801)
    fixed = []
    for i in range(24):
        position = None
        while position is None:
            position = match.opening(rng, (0, 30, 55, 78)[i % 4])
        for depth in (1, 2, 3):
            fixed.append((*position, depth))
    for _ in range(1000):
        position = match.opening(rng, 82)
        if position and not match.legal_moves(*position):
            break
    else:
        raise AssertionError("expected a reachable forced pass")
    fixed.extend([(*position, 0), (*position, 2)])
    terminal = {cell: int(cell != match.ROWS[0][0]) for row in match.ROWS for cell in row}
    fixed.extend([(terminal, 1, 0), (terminal, 2, 2)])
    queries = "".join(f"{depth}\n" + match.board_input(board, side) for board, side, depth in fixed)
    result = subprocess.run([args.probe.resolve()], input=queries, text=True, capture_output=True, check=True)
    for (board, side, depth), line in zip(fixed, result.stdout.splitlines(), strict=True):
        expected, best_moves = plain_minimax(board, side, depth, args.evaluation)
        score, square = map(int, line.split())
        assert score == expected and (square in best_moves if best_moves else square == -1)
    for board, side in (position, (terminal, 1)):
        run = subprocess.run([args.player.resolve()], input=match.board_input(board, side),
                             text=True, capture_output=True, check=True, timeout=3)
        assert run.stdout.split() == ["0", "0"]
    print(f"{len(fixed)} fixed-depth checks passed, including passes and early termination.")

    endgames = []
    for i in range(96):
        while True:
            position = match.opening(rng, 84 - (5 + i % 6))
            if position and len(match.legal_moves(*position)) >= 2:
                endgames.append(position)
                break
    queries = "".join(match.board_input(board, side) for board, side in endgames)
    result = subprocess.run([args.truth.resolve()], input=queries, text=True, capture_output=True, check=True)
    for (board, side), line in zip(endgames, result.stdout.splitlines(), strict=True):
        values = list(map(int, line.split()))
        margins = dict(zip(values[::4], values[1::4], strict=True))
        (r, c), _ = match.ask_player(args.player.resolve(), board, side, match.legal_moves(board, side))
        assert margins[16 * r + c] == max(margins.values())
    print(f"{len(endgames)} CLI endgames matched the exact optimal disk margin.")


if __name__ == "__main__":
    main()
