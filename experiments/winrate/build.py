"""Build a frozen or experimental player with its normal or a screening clock."""

import argparse
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("player", nargs="+", choices=("baseline", "early-proof", "midgame-margin", "midgame-outcome"))
    parser.add_argument("--milliseconds", type=int, default=2650)
    args = parser.parse_args()
    if not 1 <= args.milliseconds <= 2650:
        parser.error("choose a clock between 1 and 2650 milliseconds")
    (HERE / "bin").mkdir(exist_ok=True)
    for name in args.player:
        source = (HERE / (name + ".cpp")).read_text()
        if source.count("milliseconds(2650)") != 1:
            raise ValueError("unexpected search clock in " + name)
        source = source.replace("milliseconds(2650)", f"milliseconds({args.milliseconds})")
        suffix = "" if args.milliseconds == 2650 else f"-{args.milliseconds}ms"
        subprocess.run([os.environ.get("CXX", "c++"), "-std=c++17", "-O2", "-x", "c++", "-",
                        "-o", HERE / "bin" / (name + suffix)], input=source, text=True, check=True)


if __name__ == "__main__":
    main()
