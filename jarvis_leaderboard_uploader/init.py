"""
jarvis_leaderboard_uploader
===========================
A Python package to automate submitting results to the JARVIS Leaderboard
(https://pages.nist.gov/jarvis_leaderboard/).

Quickstart
----------
From Python:
    from jarvis_leaderboard_uploader import JarvisUploader
    uploader = JarvisUploader(repo_path="/path/to/your/jarvis_leaderboard")
    uploader.submit(
        results_file="my_predictions.csv",
        benchmark="AI-SinglePropertyPrediction-formation_energy_peratom-dft_3d-test-mae",
        contribution_name="my_model_v1",
        metadata={"model_name": "MyModel", "project_url": "https://github.com/me/mymodel"},
    )

From CLI:
    jarvis-upload --help
"""

from jarvis_leaderboard_uploader.uploader import JarvisUploader

__version__ = "0.1.0"
__all__ = ["JarvisUploader"]