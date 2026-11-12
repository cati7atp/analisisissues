"""Tests del resumen de código y tracebacks (S11)."""

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
    assert "do_work" not in result  # el cuarto frame se descarta
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


BUILD_LOG = """Collecting dimod
  Using cached dimod-0.12.tar.gz (5.0 MB)
running build_ext
copying build/lib.macosx-10.9-x86_64-3.7/dimod/core.so -> dimod
creating build/temp.linux-aarch64
gcc -pthread -O2 -c core.c
ranlib libdimod.a
Successfully installed dimod-0.12"""


def test_unfenced_build_log_run_becomes_a_stop_word_marker():
    result = clean_text("Install fails:\n" + BUILD_LOG + "\nAny idea?")
    assert "[BUILD_LOG]" in result
    for noise in ("macosx", "ranlib", "aarch64", "copying", "Collecting"):
        assert noise not in result
    assert "Install fails:" in result and "Any idea?" in result


def test_short_runs_and_prose_are_not_build_logs():
    text = "Collecting data is slow.\ncopying results is fine.\nCreating a circuit works."
    assert clean_text(text) == "Collecting data is slow. copying results is fine. Creating a circuit works."


def test_two_separate_runs_become_two_markers():
    result = clean_text(BUILD_LOG + "\nSome text in between\n" + BUILD_LOG)
    assert result.count("[BUILD_LOG]") == 2
    assert "Some text in between" in result


def test_build_log_marker_is_a_default_stop_word():
    from src.config import BERTopicConfig
    assert "build_log" in BERTopicConfig().domain_stop_words


def test_stray_backtick_does_not_swallow_the_exception_summary():
    # forma de Qiskit/qiskit#5143: un backtick sin pareja antes del bloque y código con doble backtick después
    text = ("The transpiler doesn't handle `negative indices\n"
            "```\nTraceback (most recent call last):\n  File \"a.py\", line 1, in f\n    x()\n"
            "TranspilerError: bad layout\n```\n"
            "the culprit is ``len(layout)`` here")
    result = clean_text(text)
    assert "TranspilerError: bad layout" in result
    assert "The transpiler doesn't handle" in result and "the culprit is" in result


def test_well_formed_inline_code_is_still_replaced():
    result = clean_text("Call `transpile(qc)` and then `run()` on the backend.")
    assert result == "Call [CODE] and then [CODE] on the backend."
