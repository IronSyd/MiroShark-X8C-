"""Unit tests for deleting simulations from history.

The delete endpoint is intentionally filesystem-oriented: a history card
maps to one simulation directory plus zero or more report folders. These
tests pin the safety contract without booting Neo4j or running Wonderwall.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _make_app():
    from flask import Flask

    from app.api import simulation_bp

    app = Flask(__name__)
    app.register_blueprint(simulation_bp, url_prefix="/api/simulation")
    return app


@pytest.fixture()
def isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    from app.api import simulation as simulation_api
    from app.models.task import TaskManager
    from app.services.report_agent import ReportManager
    from app.services.simulation_manager import SimulationManager
    from app.services.simulation_runner import SimulationRunner

    sim_root = tmp_path / "simulations"
    reports_root = tmp_path / "reports"
    push_root = tmp_path / "push_subscriptions"

    monkeypatch.setattr(SimulationManager, "SIMULATION_DATA_DIR", str(sim_root))
    monkeypatch.setattr(SimulationManager, "PUSH_SUBSCRIPTIONS_DIR", str(push_root))
    monkeypatch.setattr(SimulationRunner, "RUN_STATE_DIR", str(sim_root))
    monkeypatch.setattr(ReportManager, "REPORTS_DIR", str(reports_root))
    monkeypatch.setattr(simulation_api.Config, "WONDERWALL_SIMULATION_DATA_DIR", str(sim_root))

    SimulationRunner._run_states.clear()
    SimulationRunner._processes.clear()
    task_manager = TaskManager()
    with task_manager._task_lock:
        task_manager._tasks.clear()

    return {
        "sim_root": sim_root,
        "reports_root": reports_root,
        "push_root": push_root,
    }


def _write_simulation(sim_root: Path, sim_id: str, *, status: str = "completed") -> Path:
    sim_dir = sim_root / sim_id
    sim_dir.mkdir(parents=True, exist_ok=True)
    (sim_dir / "state.json").write_text(
        json.dumps(
            {
                "simulation_id": sim_id,
                "project_id": "proj_delete_test",
                "graph_id": "graph_delete_test",
                "status": status,
                "profiles_count": 4,
                "created_at": "2026-05-24T10:00:00",
                "updated_at": "2026-05-24T10:00:00",
            }
        ),
        encoding="utf-8",
    )
    (sim_dir / "simulation_config.json").write_text(
        json.dumps(
            {
                "simulation_requirement": "Will the deletion smoke test pass?",
                "time_config": {"total_simulation_hours": 1, "minutes_per_round": 60},
            }
        ),
        encoding="utf-8",
    )
    return sim_dir


def _write_report(reports_root: Path, report_id: str, sim_id: str) -> Path:
    report_dir = reports_root / report_id
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "meta.json").write_text(
        json.dumps(
            {
                "report_id": report_id,
                "simulation_id": sim_id,
                "graph_id": "graph_delete_test",
                "simulation_requirement": "Will the deletion smoke test pass?",
                "status": "completed",
                "markdown_content": "# Delete Test\n",
                "created_at": "2026-05-24T10:05:00",
            }
        ),
        encoding="utf-8",
    )
    (report_dir / "full_report.md").write_text("# Delete Test\n", encoding="utf-8")
    return report_dir


def _write_run_state(sim_dir: Path, sim_id: str, runner_status: str) -> None:
    (sim_dir / "run_state.json").write_text(
        json.dumps({"simulation_id": sim_id, "runner_status": runner_status}),
        encoding="utf-8",
    )


def test_delete_simulation_removes_folder_reports_subscriptions_and_history(isolated_storage):
    sim_id = "sim_delete_done"
    report_id = "report_delete_done"
    sim_dir = _write_simulation(isolated_storage["sim_root"], sim_id)
    report_dir = _write_report(isolated_storage["reports_root"], report_id, sim_id)
    push_file = isolated_storage["push_root"] / f"{sim_id}.json"
    push_lock = isolated_storage["push_root"] / f"{sim_id}.json.lock"
    push_file.parent.mkdir(parents=True, exist_ok=True)
    push_file.write_text("{}", encoding="utf-8")
    push_lock.write_text("", encoding="utf-8")

    client = _make_app().test_client()
    res = client.delete(f"/api/simulation/{sim_id}")

    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True
    assert body["data"]["deleted_reports"] == [report_id]
    assert not sim_dir.exists()
    assert not report_dir.exists()
    assert not push_file.exists()
    assert not push_lock.exists()

    history = client.get("/api/simulation/history")
    assert history.status_code == 200
    assert history.get_json()["data"] == []


def test_delete_unknown_simulation_returns_404_without_creating_folder(isolated_storage):
    client = _make_app().test_client()

    res = client.delete("/api/simulation/sim_missing")

    assert res.status_code == 404
    assert res.get_json()["success"] is False
    assert not (isolated_storage["sim_root"] / "sim_missing").exists()


@pytest.mark.parametrize(
    ("status", "runner_status"),
    [
        ("paused", "failed"),
        ("paused", "stopped"),
        ("preparing", None),
    ],
)
def test_delete_stale_non_active_records_succeeds(isolated_storage, status: str, runner_status: str | None):
    sim_id = f"sim_stale_{status}_{runner_status or 'idle'}"
    sim_dir = _write_simulation(isolated_storage["sim_root"], sim_id, status=status)
    if runner_status:
        _write_run_state(sim_dir, sim_id, runner_status)

    res = _make_app().test_client().delete(f"/api/simulation/{sim_id}")

    assert res.status_code == 200
    assert not sim_dir.exists()


def test_delete_active_prepare_task_returns_409(isolated_storage):
    from app.models.task import TaskManager

    sim_id = "sim_active_prepare"
    sim_dir = _write_simulation(isolated_storage["sim_root"], sim_id, status="preparing")
    TaskManager().create_task(
        task_type="simulation_prepare",
        metadata={"simulation_id": sim_id},
    )

    res = _make_app().test_client().delete(f"/api/simulation/{sim_id}")

    assert res.status_code == 409
    assert sim_dir.exists()


@pytest.mark.parametrize("runner_status", ["starting", "running", "stopping"])
def test_delete_active_runner_returns_409(isolated_storage, runner_status: str):
    sim_id = f"sim_runner_{runner_status}"
    sim_dir = _write_simulation(isolated_storage["sim_root"], sim_id)
    _write_run_state(sim_dir, sim_id, runner_status)

    res = _make_app().test_client().delete(f"/api/simulation/{sim_id}")

    assert res.status_code == 409
    assert sim_dir.exists()


def test_delete_rejects_traversal_style_ids(isolated_storage):
    client = _make_app().test_client()

    res = client.delete("/api/simulation/sim_..")

    assert res.status_code == 400
    assert res.get_json()["success"] is False
    assert list(isolated_storage["sim_root"].glob("*")) == []
