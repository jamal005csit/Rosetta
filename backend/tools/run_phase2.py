"""Run ingest+observe+specify offline (no Meta key needed)."""
import argparse
import logging
from pathlib import Path

from backend.stages import stage1_ingest
from backend.stages.stage2_observe import observe_job
from backend.stages.stage3_specify import specify_job

log = logging.getLogger(__name__)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True, help="jobs/<id> dir")
    ap.add_argument("--video", default="", help="source mp4 to copy as upload.mp4")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    jd = Path(a.video) if False else Path(a.job)
    jd.mkdir(parents=True, exist_ok=True)
    if a.video:
        import shutil
        shutil.copy(a.video, jd / "upload.mp4")
    if (jd / "upload.mp4").exists():
        log.info("ingest: %s", stage1_ingest.ingest(jd))
    obs = observe_job(jd, client=None)
    log.info("observations=%d", len(obs["observations"]))
    spec = specify_job(jd, client=None)
    log.info("screens=%d rules=%d journey=%d", len(spec["screens"]), len(spec["rules"]), len(spec["journey"]))

if __name__ == "__main__":
    main()