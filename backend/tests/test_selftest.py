from backend.tools.selftest import run, schema
import jsonschema

def test_selftest_schema_valid():
    data = run(True)
    jsonschema.validate(data, schema())
    assert len(data["observations"]) >= 1
    assert all("t" in o for o in data["observations"])