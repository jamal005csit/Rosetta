"""Generate the React application and execute a real Playwright replay."""
import argparse
import logging
from pathlib import Path

from backend.app.config import meta_key
from backend.muse.client import MuseClient
from backend.stages.stage4_generate import generate_job
from backend.stages.stage5_replay import replay_job


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    job_dir = Path(args.job)
    client = MuseClient.from_env(job_dir) if meta_key() else None
    print(generate_job(job_dir, client=client))
    steps = replay_job(job_dir)
    successful = sum(1 for step in steps if step["success"])
    print(f"replay steps={len(steps)} successful={successful}")


if __name__ == "__main__":
    main()
