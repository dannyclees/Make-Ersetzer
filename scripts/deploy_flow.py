"""Baut und deployt einen Ablauf nach Cloud Run anhand seiner flow.yaml.

  python scripts/deploy_flow.py sales/onepage-zu-monday

Benötigt: PROJECT_ID, REGION, angemeldetes gcloud und docker.
"""

import os
import subprocess
import sys
from pathlib import Path

import yaml


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main(flow_dir: str) -> None:
    root = Path(__file__).resolve().parents[1]
    spec = yaml.safe_load((root / flow_dir / "flow.yaml").read_text(encoding="utf-8"))
    project, region = os.environ["PROJECT_ID"], os.environ["REGION"]
    tag = os.environ.get("GITHUB_SHA", "manual")[:12]
    image = f"{region}-docker.pkg.dev/{project}/flows/{spec['name']}:{tag}"

    if spec.get("typ", "service") != "service":
        sys.exit(f"Typ {spec.get('typ')!r} wird noch nicht unterstützt")

    run(["docker", "build", "-f", f"{flow_dir}/Dockerfile", "-t", image, str(root)])
    run(["docker", "push", image])

    env = {"DEADLETTER_BUCKET": f"{project}-deadletter", **(spec.get("env") or {})}
    res = spec.get("ressourcen") or {}
    cmd = [
        "gcloud", "run", "deploy", spec["name"], "--image", image, "--region", region, "--quiet",
        "--service-account", f"flows-runtime@{project}.iam.gserviceaccount.com",
        "--set-env-vars", ",".join(f"{k}={v}" for k, v in env.items()),
        "--memory", str(res.get("memory", "512Mi")), "--cpu", str(res.get("cpu", "1")),
        "--max-instances", str(res.get("max_instances", 3)),
        "--labels", f"abteilung={spec['abteilung']},flow={spec['name']}",
    ]
    if spec.get("secrets"):
        cmd += ["--set-secrets", ",".join(f"{k}={v}:latest" for k, v in spec["secrets"].items())]
    cmd.append("--allow-unauthenticated" if spec.get("oeffentlich") else "--no-allow-unauthenticated")
    run(cmd)


if __name__ == "__main__":
    main(sys.argv[1].rstrip("/"))
