"""Run generate + replay offline."""
import argparse
import logging
from pathlib import Path

from backend.stages.stage4_generate import generate_job
from backend.stages.stage5_replay import replay_job

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    jd = Path(a.job)
    print(generate_job(jd, client=None))
    steps = replay_job(jd)
    print(f"replay steps={len(steps)}")

if __name__ == "__main__":
    main()