# Manejo de datos y privacidad

Este documento registra qué se enmascara en el corpus, qué no, y qué artefactos no
deben compartirse bajo ninguna circunstancia. Aplica a los resultados en
`data/analysis/` y al reporte en `reports/`.

## Enmascaramiento aplicado

El enmascaramiento corre durante `preprocess` (`src/models.py`, `mask_personal`) y la
anonimización de autores.

| Dato | Patrón | Reemplazo |
|---|---|---|
| Correo electrónico | `EMAIL_PATTERN` | `[EMAIL]` |
| Mención `@usuario` | `MENTION_PATTERN` | `@user` |
| Autor del issue | anonimización en preprocess | `u_<hash>` |
| URL | `URL_PATTERN` | `[URL]` |
| Código en línea | `INLINE_CODE_PATTERN` | `[CODE]` |
| Bloque de código | `summarize_fenced_code` | `[CODE_BLOCK]` |

El corpus procesado (`data/processed/issues_clean.jsonl`) contiene 0 correos
electrónicos, 1.761 marcas `[EMAIL]` y 73.492 marcas `@user`.

## Qué no se enmascara, y por qué

### Rutas de home con nombre de usuario

El texto de los issues incluye rutas del tipo `/Users/nate`, `C:\Users\cambi` o
`/home/leon`. El masking no las cubre.

**Decisión (2026-11-12): se aceptan como dato público.** Provienen de issues públicos de
GitHub y ya son visibles en el origen; enmascararlas requeriría re-ejecutar el pipeline
completo (33 min) sin beneficio de seguridad real.

Estado medido en `data/analysis/`: 30 ocurrencias en 12 fragmentos distintos
(`/Users/juliegermain`, `/Users/nate`, `C:\Users\cambi`, `C:\Users\ED`, `C:\Users\DELL`,
`/Users/Administrator`, `/home/leon`, `/home/pi`, `/home/ubuntu`, `/home/DIR`, y variantes).
El reporte markdown no contiene ninguna.

Si esta decisión se revisa en el futuro, el cambio va en `HOME_PATH_PATTERN` dentro de
`mask_personal`, y exige regenerar el corpus y los resultados.

## Artefactos que no se comparten

| Ruta | Motivo |
|---|---|
| `data/run_b/` | Previo al masking: 4.046 correos sin enmascarar |
| `data/run_r/` | Previo al masking: 4.036 correos sin enmascarar |
| `data/cache/` | Embeddings derivados, innecesarios para analizar |
| `data/analysis/model/` | Modelo BERTopic, solo necesario para re-inferir |

`data/processed/` contiene el corpus ya enmascarado y puede compartirse, pero no es
necesario para analizar los resultados: para eso alcanza con `issue_index.jsonl`.

## Verificación antes de compartir

Ejecutar desde la raíz del repo. Falla con código 1 si aparece un correo o un patrón de
secreto en el set que se va a compartir.

```python
import re
import sys
from pathlib import Path

TARGETS = [Path("reports"), Path("data/analysis")]
EXCLUDE = {Path("data/analysis/model")}

PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "token": re.compile(
        r"ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}"
        r"|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}"
    ),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}

hits = 0
for root in TARGETS:
    for path in root.rglob("*"):
        if not path.is_file() or any(path.is_relative_to(ex) for ex in EXCLUDE):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                hits += 1
                print(f"{path}: {name}: {match.group()[:40]}")

print(f"coincidencias: {hits}")
sys.exit(1 if hits else 0)
```

Resultado esperado sobre los resultados actuales: `coincidencias: 0`.
