"""Public package API for the audio oscillator exercise."""

from .oscillator import (
    OscError,
    detune,
    hard_sync,
    phase_inc,
    polyblep,
    render_batch,
    render_note,
    validate_osc,
    waveform,
)

__all__ = [
    "OscError",
    "detune",
    "hard_sync",
    "phase_inc",
    "polyblep",
    "render_batch",
    "render_note",
    "validate_osc",
    "waveform",
]
