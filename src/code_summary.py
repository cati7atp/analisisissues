"""Resume bloques de código y tracebacks en texto corto, útil para los temas (S11).

El cuerpo del código y las trazas agregan ruido de vocabulario, pero los nombres de las
excepciones son la señal. Un bloque pasa a `[CODE_BLOCK] <hasta 3 frames> <ExceptionClass: message>`;
el marcador es una stop word, así que al vectorizador solo llegan las palabras del resumen.
"""

import re
from typing import List

CODE_MARKER = "[CODE_BLOCK]"
MAX_FRAMES = 3
MAX_MESSAGE_CHARS = 200

TRACEBACK_START = re.compile(r"^\s*Traceback \(most recent call last\):\s*$")
FRAME_LINE = re.compile(r'^\s*File "([^"]+)", line \d+, in (\S+)')
EXCEPTION_LINE = re.compile(
    r"^((?:[A-Za-z_]\w*\.)*)([A-Z][A-Za-z0-9]*(?:Error|Exception|Warning))\b(?::\s*(.*))?$"
)
EXCEPTION_NAME = re.compile(r"\b([A-Z][A-Za-z0-9]*(?:Error|Exception))\b")
ABSOLUTE_PATH = re.compile(r"(?<!\w)(?:[A-Za-z]:\\|/)[\w.\-]+(?:[\\/][\w.\-]+)+")
FENCE = re.compile(r"```[\s\S]*?```")


def _frame_name(path: str, func: str) -> str:
    module = re.split(r"[\\/]", path)[-1].rsplit(".", 1)[0]
    return f"{module}.{func}"


def summarize_code(block: str) -> str:
    """Devuelve el marcador más hasta 3 frames, la última línea de excepción y los nombres de excepciones."""
    lines = block.splitlines()
    frames: List[str] = []
    final_line = ""
    for line in lines:
        frame = FRAME_LINE.match(line)
        if frame and len(frames) < MAX_FRAMES:
            frames.append(_frame_name(frame.group(1), frame.group(2)))
        exception = EXCEPTION_LINE.match(line.strip())
        if exception:
            message = ABSOLUTE_PATH.sub("", exception.group(3) or "")[:MAX_MESSAGE_CHARS]
            final_line = f"{exception.group(2)}: {message}".rstrip(": ")
    parts = [CODE_MARKER] + frames
    if final_line:
        parts.append(final_line)
    names = [n for n in dict.fromkeys(EXCEPTION_NAME.findall(block)) if n not in final_line]
    return " ".join(parts + names)


def summarize_fenced_code(text: str) -> str:
    return FENCE.sub(lambda m: summarize_code(m.group(0)[3:-3]), text)


def summarize_tracebacks(text: str) -> str:
    """Reemplaza los bloques `Traceback (most recent call last):` sin cercos por su resumen."""
    lines = text.split("\n")
    out: List[str] = []
    i = 0
    while i < len(lines):
        if not TRACEBACK_START.match(lines[i]):
            out.append(lines[i])
            i += 1
            continue
        block = [lines[i]]
        i += 1
        while i < len(lines) and (not lines[i].strip() or lines[i][:1] in " \t"):
            block.append(lines[i])
            i += 1
        if i < len(lines) and EXCEPTION_LINE.match(lines[i].strip()):
            block.append(lines[i])
            i += 1
        out.append(summarize_code("\n".join(block)))
    return "\n".join(out)


BUILD_MARKER = "[BUILD_LOG]"
MIN_BUILD_RUN = 3
BUILD_LINE = re.compile(
    r"^\s*(?:Collecting \S+|Using cached |Downloading |Requirement already satisfied|"
    r"Successfully (?:installed|built) |running (?:build|install|egg_info|develop|bdist)\w*|"
    r"building '.*' extension|copying \S+ -> |creating [\w./\-]+$|"
    r"(?:\S*-)?(?:gcc|g\+\+|clang)\s+-|ranlib\b)"
)


def summarize_build_logs(text: str) -> str:
    """Reemplaza series de 3 o más líneas seguidas de herramientas de instalación/build por un marcador."""
    out: List[str] = []
    run: List[str] = []

    def flush() -> None:
        matched = [l for l in run if l.strip()]
        if len(matched) >= MIN_BUILD_RUN:
            out.append(BUILD_MARKER)
        else:
            out.extend(run)
        run.clear()

    for line in text.split("\n"):
        if BUILD_LINE.match(line) or (run and not line.strip()):
            run.append(line)
        else:
            flush()
            out.append(line)
    flush()
    return "\n".join(out)
