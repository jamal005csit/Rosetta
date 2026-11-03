"""Score actual browser evidence, run constrained repair, and generate the report."""
import argparse
import logging
from pathlib import Path

from backend.app.config import meta_key
from backend.muse.client import MuseClient
from backend.stages.stage6_score import score_job
from backend.stages.stage6_repair import repair_job
from backend.stages.stage6_report import generate_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--max-rounds", type=int, default=3)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    if not meta_key():
        raise SystemExit("META_API_KEY is required for visual judging and evidence-based repair.")
    job_dir = Path(args.job)
    client = MuseClient.from_env(job_dir)
    parity = score_job(job_dir, client=client)
    print(f"score parity={parity['parity']} pass={parity['pass']}")
    repair = repair_job(job_dir, client=client, max_rounds=args.max_rounds)
    print(
        f"repair rounds={repair['rounds']} "
        f"final={repair['final_parity']} pass={repair['pass']}"
    )
    report = generate_report(job_dir)
    print(f"report {report}")


if __name__ == "__main__":
    main()
