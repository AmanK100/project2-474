"""Trace root search progress on the independently verified missed-win fixture."""

import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOARD = (HERE / "records/missed-win.board").read_text()
EDITS = {
    "best = candidate;\n                // On larger": """
best = candidate;
                std::cerr << "completed depth " << d << " best " << best << '\\n';
                // On larger""",
    "findWinningMove(p, legal, empty, best);": """
std::cerr << "starting proof at depth " << d << '\\n';
                    findWinningMove(p, legal, empty, best);
                    std::cerr << "finished outcome proof, best " << best << '\\n';""",
    "int outcome = search(m.child": """
std::cerr << "testing for draw or better, square " << m.square << '\\n';
            int outcome = search(m.child""",
    "if (outcome > 0) continue;": """
std::cerr << "draw probe returned " << outcome << '\\n';
            if (outcome > 0) continue;""",
    "if (search(m.child, m.replies, remaining, remaining, -1, 0, reply) < 0)": """
std::cerr << "testing for win, square " << m.square << '\\n';
        if (search(m.child, m.replies, remaining, remaining, -1, 0, reply) < 0)""",
}


def main():
    for name in ("baseline", "early-proof"):
        source = (HERE / f"{name}.cpp").read_text()
        for marker, replacement in EDITS.items():
            if source.count(marker) != 1:
                raise ValueError(f"unexpected source at {marker}")
            source = source.replace(marker, replacement.strip())
        binary = HERE / "bin" / (name + "-trace")
        subprocess.run([os.environ.get("CXX", "c++"), "-O2", "-std=c++17", "-x", "c++",
                        "-", "-o", binary], input=source, text=True, check=True)
        run = subprocess.run([binary], input=BOARD, text=True, capture_output=True, check=True, timeout=3)
        print(f"{name}\n{run.stderr}output {run.stdout.strip()}", flush=True)


if __name__ == "__main__":
    main()
