PY ?= python3

.PHONY: test selftest legacy-test phase2-test phase3-test phase4-test phase5-test phase6-test frontend-build run-legacy api frontend

test:
	$(PY) -m pytest backend/tests -v

selftest:
	$(PY) -m pytest backend/tests/test_selftest.py backend/tests/test_muse_client.py -v
	$(PY) -m backend.tools.selftest --mock

legacy-test:
	$(PY) -m pytest backend/tests/test_legacy_rules.py -v

phase2-test:
	$(PY) -m pytest backend/tests/test_observations.py backend/tests/test_spec_evidence.py -v

phase3-test:
	$(PY) -m pytest backend/tests/test_generate.py backend/tests/test_replay_determinism.py -v

phase4-test:
	$(PY) -m pytest backend/tests/test_parity.py backend/tests/test_score_repair_report.py -v

phase5-test:
	$(PY) -m pytest backend/tests/test_export.py backend/tests/test_api_frontend.py backend/tests/test_readme.py -v

phase6-test:
	$(PY) -m pytest backend/tests/test_muse_client.py backend/tests/test_selftest.py -v

frontend-build:
	cd frontend && npm install && npm run build

run-legacy:
	$(PY) legacy_app/app.py

api:
	uvicorn backend.app.main:app --reload --port 8000

frontend:
	cd frontend && npm install && npm run dev
