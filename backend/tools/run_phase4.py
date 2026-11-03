"""Run score + repair + report offline."""
import argparse
import logging
from pathlib import Path

from backend.stages.stage6_score import score_job
from backend.stages.stage6_repair import repair_job
from backend.stages.stage6_report import generate_report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--max-rounds", type=int, default=3)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    jd = Path(a.job)
    par = score_job(jd, client=None)
    print(f"score parity={par['parity']} pass={par['pass']}")
    rep = repair_job(jd, client=None, max_rounds=a.max_rounds)
    print(f"repair rounds={rep['rounds']} final={rep['final_parity']} pass={rep['pass']}")
    rp = generate_report(jd)
    print(f"report {rp}")


if __name__ == "__main__":
    main()