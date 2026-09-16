"""
lib/analysis_runner.py — Pipeline execution wrapper for ExoTrace.

Wraps the existing src/ pipeline scripts for use from the Streamlit UI.
Supports single-star reanalysis and full sector survey.
"""

import os
import subprocess
import time
import uuid
import sys
import streamlit as st

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_command(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a pipeline command with proper encoding."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=_PROJECT_ROOT,
        timeout=60 * 30,
    )


def _init_history():
    """Ensure analysis history exists in session state."""
    if "analysis_history" not in st.session_state:
        st.session_state.analysis_history = []
    if "running_analyses" not in st.session_state:
        st.session_state.running_analyses = 0


def run_single_analysis(tic_id: str, status_container=None) -> dict:
    """
    Run a single-star reanalysis using 07_reanalyze.py.

    Args:
        tic_id: The TIC ID to analyze.
        status_container: Optional st.status container for progress updates.

    Returns:
        dict with keys: success, message, tic_id, job_id
    """
    _init_history()
    job_id = str(uuid.uuid4())[:8]
    job = {
        "job_id": job_id,
        "type": "single",
        "target": f"TIC {tic_id}",
        "status": "running",
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": None,
        "results_count": 0,
    }
    st.session_state.analysis_history.insert(0, job)
    st.session_state.running_analyses += 1

    steps = [
        ("step_1", "Connecting to MAST archive..."),
        ("step_2", "Downloading TESS data..."),
        ("step_3", "Building light curve..."),
        ("step_4", "Removing noise..."),
        ("step_5", "Detecting dips..."),
        ("step_6", "Computing ingress/egress..."),
        ("step_7", "Computing asymmetry..."),
        ("step_8", "Classifying results..."),
    ]

    try:
        if status_container is not None:
            for i, (step_key, step_desc) in enumerate(steps[:2]):
                status_container.update(label=step_desc, state="running")
                time.sleep(0.3)

        from lib.settings_manager import load_analysis_settings
        cfg = load_analysis_settings()
        sigma_val = float(st.session_state.get("sigma_val", cfg["sigma_threshold"]))
        asym_val = float(st.session_state.get("min_asym_val", cfg["asymmetry_min"]))
        detrend_val = float(st.session_state.get("detrend_win", cfg["detrend_window"]))
        result = _run_command([
            sys.executable, "src/07_reanalyze.py", "--tic-id", str(tic_id).strip(),
            "--sigma", str(sigma_val), "--min-duration", str(cfg["min_duration"]),
            "--max-duration", str(cfg["max_duration"]), "--asymmetry-min", str(asym_val),
            "--detrend-window", str(detrend_val),
        ])

        if status_container is not None:
            for i, (step_key, step_desc) in enumerate(steps[2:]):
                status_container.update(label=step_desc, state="running")
                time.sleep(0.2)

        if result.returncode == 0:
            job["status"] = "complete"
            job["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.running_analyses = max(0, st.session_state.running_analyses - 1)
            if status_container is not None:
                status_container.update(label="Analysis complete!", state="complete")
            return {"success": True, "message": "Analysis completed", "tic_id": tic_id, "job_id": job_id}
        else:
            job["status"] = "failed"
            job["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.running_analyses = max(0, st.session_state.running_analyses - 1)
            if status_container is not None:
                status_container.update(label="Analysis failed", state="error")
            return {"success": False, "message": result.stderr or "Unknown error", "tic_id": tic_id, "job_id": job_id}
    except Exception as e:
        job["status"] = "failed"
        job["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.running_analyses = max(0, st.session_state.running_analyses - 1)
        return {"success": False, "message": str(e), "tic_id": tic_id, "job_id": job_id}


def run_sector_survey(sectors: str, max_stars: int = 100, status_container=None) -> dict:
    """
    Run a full sector survey pipeline (steps 01 through 06).

    Args:
        sectors: Comma-separated sector numbers.
        max_stars: Maximum stars per sector.
        status_container: Optional st.status container.

    Returns:
        dict with keys: success, message, sectors, job_id
    """
    _init_history()
    job_id = str(uuid.uuid4())[:8]
    job = {
        "job_id": job_id,
        "type": "survey",
        "target": f"Sectors {sectors}",
        "status": "running",
        "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": None,
        "results_count": 0,
    }
    st.session_state.analysis_history.insert(0, job)
    st.session_state.running_analyses += 1

    from lib.settings_manager import load_analysis_settings
    cfg = load_analysis_settings()
    sigma_val = float(st.session_state.get("sigma_val", cfg["sigma_threshold"]))
    asym_val = float(st.session_state.get("min_asym_val", cfg["asymmetry_min"]))
    detrend_val = float(st.session_state.get("detrend_win", cfg["detrend_window"]))
    pipeline_steps = [
        ("step_1", "Building sample...", [sys.executable, "src/01_build_sample.py", f"--sectors={sectors}", f"--max-per-sector={max_stars}"]),
        ("step_2", "Downloading light curves...", [sys.executable, "src/02_download_lc.py"]),
        ("step_3", "Detrending...", [sys.executable, "src/03_detrend.py", "--window-days", str(detrend_val), "--force"]),
        ("step_5", "Detecting dips...", [sys.executable, "src/04_detect_dips.py", "--sigma", str(sigma_val), "--min-duration", str(cfg["min_duration"]), "--max-duration", str(cfg["max_duration"])]),
        ("step_7", "Computing asymmetry...", [sys.executable, "src/05_asymmetry.py", "--asymmetry-min", str(asym_val)]),
        ("step_8", "Validating candidates...", [sys.executable, "src/06_validate.py"]),
    ]

    try:
        for step_key, step_desc, cmd in pipeline_steps:
            if status_container is not None:
                status_container.update(label=step_desc, state="running")
            result = _run_command(cmd)
            if result.returncode != 0:
                job["status"] = "failed"
                job["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.running_analyses = max(0, st.session_state.running_analyses - 1)
                if status_container is not None:
                    status_container.update(label=f"Failed at: {step_desc}", state="error")
                return {"success": False, "message": result.stderr or f"Failed at {step_desc}", "sectors": sectors, "job_id": job_id}

        job["status"] = "complete"
        job["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.running_analyses = max(0, st.session_state.running_analyses - 1)
        if status_container is not None:
            status_container.update(label="Survey complete!", state="complete")
        return {"success": True, "message": "Survey completed", "sectors": sectors, "job_id": job_id}

    except Exception as e:
        job["status"] = "failed"
        job["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.running_analyses = max(0, st.session_state.running_analyses - 1)
        return {"success": False, "message": str(e), "sectors": sectors, "job_id": job_id}


def get_analysis_history() -> list[dict]:
    """Return analysis history merging persistent records with active session jobs."""
    _init_history()
    try:
        from lib.scan_history import get_scan_history
        persistent = get_scan_history()
    except Exception:
        persistent = []

    results = []
    seen_tics = set()

    # 1. Any active in-flight running jobs from session state
    for job in st.session_state.get("analysis_history", []):
        if job.get("status") == "running":
            t_id = str(job.get("tic_id", "")).replace("TIC", "").strip()
            seen_tics.add(t_id)
            results.append(job)

    # 2. Add persistent records from disk
    for r in persistent:
        tic_str = str(r.get("tic_id", "")).strip()
        if not tic_str:
            continue
        if tic_str in seen_tics:
            continue

        raw_status = str(r.get("status", "مكتمل بنجاح ✓"))
        is_comp = "مكتمل" in raw_status or "complete" in raw_status.lower() or "نجاح" in raw_status
        status_key = "complete" if is_comp else "failed"

        results.append({
            "job_id": f"scan_{tic_str}",
            "tic_id": tic_str,
            "type": "single" if int(r.get("sectors_count", 1) or 1) <= 10 else "survey",
            "target": f"TIC {tic_str}",
            "star_name": r.get("star_name", f"النجم المضيف TIC {tic_str}"),
            "status": status_key,
            "status_label": raw_status,
            "start_time": r.get("timestamp", "—"),
            "end_time": r.get("timestamp", "—"),
            "sectors_count": int(r.get("sectors_count", 1) or 1),
            "dips_count": int(r.get("dips_count", 0) or 0),
            "comets_count": int(r.get("comets_count", 0) or 0),
            "summary": r.get("summary", ""),
        })

    return results

