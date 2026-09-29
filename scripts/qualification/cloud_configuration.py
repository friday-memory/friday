"""Assert final candidate configuration without exposing secret values."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.deploy import gcp_candidate as deployment


def main():
    deployment.configure()
    state = json.loads(deployment.STATE.read_text())
    expected = deployment.config("prod")
    service = deployment.gc(
        "run", "services", "describe", deployment.SERVICE, "--region", deployment.REGION
    )
    template = service["spec"]["template"]
    annotations = template["metadata"]["annotations"]
    assert annotations["run.googleapis.com/cpu-throttling"] == "true"
    assert annotations["autoscaling.knative.dev/maxScale"] == "2"
    assert annotations.get("autoscaling.knative.dev/minScale", "0") == "0"
    assert service["metadata"]["annotations"]["run.googleapis.com/maxScale"] == "2"
    assert service["metadata"]["annotations"].get("run.googleapis.com/minScale", "0") == "0"
    assert (
        service["metadata"]["annotations"].get("run.googleapis.com/invoker-iam-disabled", "false")
        == "false"
    )
    assert not template["spec"].get("volumes")
    assert template["spec"]["serviceAccountName"] == deployment.RUNTIME
    container = template["spec"]["containers"][0]
    assert container["image"] == state["image"]
    env = {v["name"]: v for v in container["env"]}
    assert env["FRIDAY_STORAGE_BACKEND"]["value"] == "turso"
    assert env["TURSO_DATABASE_URL"]["value"] == expected["TURSO_DATABASE_URL"]
    for key, suffix in (("FRIDAY_API_KEY", "api-key"), ("TURSO_AUTH_TOKEN", "turso-token")):
        ref = env[key]["valueFrom"]["secretKeyRef"]
        assert ref["name"] == deployment.secret_name("prod", suffix)
        assert ref["key"] == state["secrets"][ref["name"]]
    assert service["status"]["latestReadyRevisionName"] == state["revision"]
    assert any(
        t["revisionName"] == state["revision"] and t["percent"] == 100
        for t in service["status"]["traffic"]
    )
    job = deployment.gc(
        "run", "jobs", "describe", deployment.JOB, "--region", deployment.REGION
    )
    job_spec = job["spec"]["template"]["spec"]["template"]["spec"]
    assert job_spec["serviceAccountName"] == deployment.RUNTIME
    job_container = job_spec["containers"][0]
    assert job_container["image"] == state["image"]
    job_env = {v["name"]: v for v in job_container["env"]}
    assert job_env["TURSO_DATABASE_URL"]["value"] == expected["TURSO_DATABASE_URL"]
    assert (
        job_env["TURSO_AUTH_TOKEN"]["valueFrom"]["secretKeyRef"]["name"]
        == deployment.secret_name("prod", "turso-token")
    )
    schedule = deployment.gc(
        "scheduler", "jobs", "describe", deployment.SCHEDULE, "--location", deployment.REGION
    )
    assert schedule["state"] == "ENABLED" and schedule["schedule"] == "0 3 * * *"
    assert schedule["timeZone"] == "UTC"
    assert schedule.get("status", {}).get("code", 0) == 0
    target = schedule["httpTarget"]
    assert target["oauthToken"]["serviceAccountEmail"] == deployment.SCHEDULER
    assert (
        target["uri"]
        == f"https://run.googleapis.com/v2/projects/{deployment.PROJECT}/locations/{deployment.REGION}/jobs/{deployment.JOB}:run"
    )
    assert not any("key" in k.lower() or "authorization" in k.lower() for k in target["headers"])
    print(
        "FINAL_CLOUD_CONFIGURATION=PASS\nPRODUCTION_SECRET_REFERENCES=PASS\nSCHEDULER_PRODUCTION_TARGET=PASS"
    )


if __name__ == "__main__":
    main()
