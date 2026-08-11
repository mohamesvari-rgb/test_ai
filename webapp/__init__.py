"""
Web GUI for the Scientific Evaluation Agent.

A small local Flask app that lets you define the challenge in a form, upload the
participants' Word answers, run the evaluation, and download the generated
Persian report (Word + PDF).

Launch with:
    python gui.py
"""

from .app import create_app

__all__ = ["create_app"]
