"""Summarize saved observations and verify the original project files byte-for-byte."""

from collections import Counter
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "results"
sys.path.insert(0, str(ROOT / "tests"))
import match


def rows(file):
    return [json.loads(line) for line in file.read_text().splitlines()]


def main():
    original = json.loads((OUT / "original-checksums.json").read_text())
    current = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in ROOT.rglob("*") if p.is_file() and HERE not in p.parents}
    if original != current:
        raise ValueError("files outside the validation directory differ from the starting manifest")
    report = {"original_files_verified": len(original), "source_sha256": current["reversi.cpp"]}
    cli = rows(OUT / "cli.jsonl")
    report["cli"] = dict(passed=sum(r["passed"] for r in cli), total=len(cli),
                         max_s=max(r["wall_s"] for r in cli),
                         peak_rss_MiB=max(r["rss_bytes"] for r in cli) / 2**20)
    games = {}
    times = []
    snapshots = []
    for opp in ("greedy", "shallow", "baseline"):
        stats = Counter(wins=0, draws=0, losses=0, failures=0)
        for file in sorted(OUT.glob(opp + "-*.jsonl")):
            for g in rows(file):
                if "failure" in g:
                    stats["failures"] += 1
                    continue
                side = g["candidate_side"]
                result = g["candidate_disks"] - g["reference_disks"]
                stats["wins" if result > 0 else "losses" if result < 0 else "draws"] += 1
                times.extend(m["seconds"] for m in g["moves"] if m["side"] == side)
                if file.stem == "baseline-standard":
                    board = dict(zip([sq for row in match.ROWS for sq in row], g["board"], strict=True))
                    for m in g["moves"]:
                        counts = list(board.values())
                        if counts.count(0) in (60, 44, 36, 30, 22):
                            snapshots.append(dict(side=side, empty=counts.count(0),
                                disks=[counts.count(side), counts.count(3-side)],
                                mobility=[len(match.legal_moves(board, side)), len(match.legal_moves(board, 3-side))]))
                        sq = match.ROWS[m["row"] - 1][m["column"] - 1]
                        match.place(board, m["side"], sq, match.legal_moves(board, m["side"])[sq])
        games[opp] = stats
    report["opponents"] = games
    report["match_candidate_turns"] = len(times)
    report["slowest_candidate_match_turn_s"] = max(times)
    report["standard_opening_snapshots"] = snapshots
    decision_sets = {}
    stress = {r["case"]: r for r in rows(OUT / "stress.jsonl")}
    for proof in rows(OUT / "extended-stress.jsonl"):
        for key in ("chosen", "best"):
            if proof[key] != -9:
                stress[proof["case"]][key] = proof[key]
    for pair in rows(OUT / "stress-alternatives.jsonl"):
        if pair.get("best", -9) != -9:
            stress["fresh-23-2"]["best"] = pair["best"]
    for row in rows(OUT / "endgames.jsonl") + list(stress.values()):
        group = ("known wins" if not row["case"].startswith("fresh-") else
                 "11–13" if row["empty"] <= 13 else "14–20" if row["empty"] <= 20 else "21–24")
        tally = decision_sets.setdefault(group, Counter())
        tally["positions"] += 1
        if -9 in (row["chosen"], row["best"]):
            tally["unresolved"] += 1
        else:
            tally["optimal_outcome"] += row["chosen"] == row["best"]
            tally["winnable"] += row["best"] == 1
            tally["converted"] += row["chosen"] == 1
        if "margin" in row:
            tally["optimal_margin"] += row["margin"] == row["best_margin"]
    report["endgames"] = decision_sets
    audits = rows(OUT / "match-audit.jsonl")
    turns = [turn for a in audits for turn in a["turns"]]
    report["audit"] = dict(games=len(audits), turns=len(turns), unresolved=sum(
        -9 in (t["played"], t["best"]) for t in turns), proven_drops=sum(len(a["drops"]) for a in audits))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
