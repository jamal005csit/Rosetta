"""Run media ingestion, evidence-backed observation, and AppSpec generation."""
import argparse
import logging
import shutil
from pathlib import Path

from backend.app.config import meta_key
from backend.muse.client import MuseClient
from backend.stages import stage1_ingest
from backend.stages.stage2_observe import observe_job
from backend.stages.stage3_specify import specify_job

log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True, help="job output directory, e.g. jobs/demo")
    parser.add_argument("--video", default="", help="recording file to copy to upload.mp4")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    job_dir = Path(args.job)
    job_dir.mkdir(parents=True, exist_ok=True)
    if args.video:
        shutil.copy2(args.video, job_dir / "upload.mp4")
    if (job_dir / "upload.mp4").is_file():
        log.info("ingest: %s", stage1_ingest.ingest(job_dir))
    elif not list((job_dir / "frames").glob("frame_*.png")):
        raise SystemExit("Provide --video or pre-extracted frame_*.png evidence in the job's frames directory.")

    if not meta_key():
        raise SystemExit("META_API_KEY is required; Rosetta no longer fabricates offline observations or AppSpecs.")
    client = MuseClient.from_env(job_dir)
    observations = observe_job(job_dir, client=client)
    log.info("observations=%d", len(observations["observations"]))
    appspec = specify_job(job_dir, client=client)
    log.info(
        "screens=%d rules=%d journey=%d",
        len(appspec["screens"]), len(appspec["rules"]), len(appspec["journey"]),
    )


if __name__ == "__main__":
    main()
