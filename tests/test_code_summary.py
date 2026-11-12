"""Tests for code and traceback summarization (S11)."""

from src.models import clean_text

TRACEBACK = """Traceback (most recent call last):
  File "/home/alice/venv/lib/python3.10/site-packages/qiskit/compiler/transpiler.py", line 300, in transpile
    pm.run(circuits)
  File "/home/alice/venv/lib/python3.10/site-packages/qiskit/passmanager.py", line 12, in run
    self._execute()
  File "C:\\Users\\bob\\venv\\lib\\site-packages\\qiskit\\passes.py", line 77, in _execute
    do_work()
  File "/home/alice/venv/lib/python3.10/site-packages/qiskit/other.py", line 5, in do_work
    raise TranspilerError("Unable to map the circuit")
qiskit.transpiler.exceptions.TranspilerError: Unable to map the circuit"""


def test_fenced_traceback_keeps_exception_and_drops_body():
    text = "It crashes:\n```\n" + TRACEBACK + "\n```\nPlease help."
    result = clean_text(text)
    assert "TranspilerError: Unable to map the circuit" in result
    assert "pm.run(circuits)" not in result
    assert "do_work()" not in result
    assert "It crashes:" in result and "Please help." in result


def test_traceback_keeps_at_most_three_frames_without_paths():
    result = clean_text("```\n" + TRACEBACK + "\n```")
    assert "transpile" in result and "_execute" in result
    assert "do_work" not in result  # the fourth frame is dropped
    assert "/home/alice" not in result and "bob" not in result and "300" not in result


def test_fenced_code_without_exception_is_only_a_marker():
    result = clean_text("Before\n```python\nprint('hello')\nx = 1\n```\nAfter")
    assert "[CODE_BLOCK]" in result
    assert "print" not in result and "x = 1" not in result


def test_exception_class_in_plain_code_is_kept():
    result = clean_text("```python\nraise QiskitError('boom')\n```")
    assert "QiskitError" in result
    assert "boom" not in result


def test_unfenced_traceback_is_summarized_too():
    text = "I get this:\n" + TRACEBACK + "\nAny idea?"
    result = clean_text(text)
    assert "TranspilerError: Unable to map the circuit" in result
    assert "pm.run(circuits)" not in result
    assert "Traceback" not in result
    assert "I get this:" in result and "Any idea?" in result


def test_prose_mentioning_errors_is_untouched():
    text = "A QiskitError was raised when I call run."
    assert clean_text(text) == text
