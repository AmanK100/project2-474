"""Exercise the actual one-board executable and measure each child in a fresh process."""

import json
import random
import resource
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import match


def measure():
    data = sys.stdin.read()
    start = time.monotonic()
    try:
        proc = subprocess.run([HERE / "bin/player"], input=data, text=True,
                              capture_output=True, timeout=3)
        code, output, error = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        code, output, error = None, "", "timeout"
    seconds = time.monotonic() - start
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return dict(code=code, stdout=output, stderr=error, wall_s=seconds,
                rss_bytes=rss if sys.platform == "darwin" else rss * 1024)


def cases():
    cells = [sq for row in match.ROWS for sq in row]
    sample = (ROOT / "tests/assignment.board").read_text()
    board = dict(zip(cells, map(int, sample.split()), strict=True))
    sample_moves = match.legal_moves(board, 1)
    assert len(sample_moves) == 6 and match.ROWS[6][5] in sample_moves
    for i in range(5):
        text = sample if i < 4 else "\t\n".join(sample.split())
        yield f"assignment-{i+1}", text, sample_moves
    rng = random.Random(322010)
    for plies in (0, 24, 44, 65, 76):
        board, side = match.opening(rng, plies)
        yield f"random-{plies}-placements", match.board_input(board, side), match.legal_moves(board, side)
    for i in range(4):
        board = dict.fromkeys(cells, 0)
        row = match.ROWS[3] if i < 2 else match.ROWS[0]
        if i % 2:
            row = row[::-1]
        board[row[-1]] = 1
        for sq in row[1:-1]:
            board[sq] = 2
        yield f"long-ray-{i+1}", match.board_input(board, 1), {row[0]}
    while True:
        position = match.opening(rng, 82)
        if position and not match.legal_moves(*position):
            break
    yield "forced-pass", match.board_input(*position), set()
    for label, values in (("full-draw", [1, 2] * 44), ("early-terminal", [0] + [1] * 87)):
        yield label, " ".join(map(str, values)), set()
    for label, value in (("short", "0 " * 87), ("out-of-range", "0 " * 87 + "3"),
                         ("non-numeric", "0 " * 87 + "x"), ("empty-input", "")):
        yield label, value, None


def main():
    for name, data, moves in cases():
        worker = subprocess.run([sys.executable, "-B", __file__, "--one"], input=data,
                                text=True, capture_output=True, check=True)
        result = json.loads(worker.stdout)
        allowed = sorted([r + 1, c - match.OFFSETS[r] + 1] for r, c in (moves or ()))
        if moves is None:
            success = result["code"] == 1 and result["stdout"] == ""
        else:
            allowed = allowed or [[0, 0]]
            acceptable = [f"{r} {c}\n" for r, c in allowed]
            success = result["code"] == 0 and result["stdout"] in acceptable
        success = success and not result["stderr"] and result["wall_s"] <= 3
        print(json.dumps(dict(case=name, passed=success, allowed=allowed, **result)), flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["--one"]:
        print(json.dumps(measure()))
    else:
        main()
