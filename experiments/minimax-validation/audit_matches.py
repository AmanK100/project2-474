"""Independently score the candidate's late turns in each completed match."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tests"))
from audit_games import audit


def main():
    output = HERE / "results/match-audit.jsonl"
    previous = [json.loads(line) for line in output.read_text().splitlines()] if output.exists() else []
    seen = {(r["suite"], r["pair"], r["candidate_side"]) for r in previous}
    with output.open("a") as out:
        for file in sorted((HERE / "results").glob("*.jsonl")):
            if not file.stem.startswith(("baseline-", "shallow-", "greedy-")):
                continue
            for line in file.read_text().splitlines():
                record = json.loads(line)
                key = (file.stem, record["pair"], record["candidate_side"])
                if key in seen or "failure" in record:
                    continue
                turns = audit(record, HERE / "bin/verify", 2, 22, record["candidate_side"])
                drops = [turn for turn in turns if -1 <= turn["played"] < turn["best"]]
                print(json.dumps(dict(suite=key[0], pair=key[1], candidate_side=key[2],
                                      turns=turns, drops=drops)), file=out, flush=True)


if __name__ == "__main__":
    main()
