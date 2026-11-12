# Traspaso: resultados de BERTopic sobre issues de software cuántico en GitHub

Guía corta para el equipo que va a analizar los resultados. Las rutas son relativas a la raíz del
repositorio (`C:\Users\catuk\Documents\cuantica\analisisissues`).

## 1. Qué hace este proyecto

Toma los **issues** de GitHub de unos 100 repositorios con componentes cuánticos (Qiskit, PennyLane,
Cirq, Braket, tket, ...), los limpia, los agrupa en **temas** con BERTopic y busca **patrones que se
repiten entre proyectos distintos**.

```
miner.db  ->  preprocess  ->  BERTopic  ->  patrones / temas entre proyectos  ->  métricas  ->  reporte
```

| Paso | Comando | Escribe |
|------|---------|---------|
| 1 Limpiar | `python -m src.cli preprocess` | `data/processed/issues_clean.jsonl` |
| 2 Temas | `python -m src.cli topic-model --output-dir data/analysis` | `topics.jsonl`, `doc_topics.jsonl`, ... |
| 3 Patrones | `python -m src.cli extract-patterns --output-dir data/analysis` | `quantum_patterns.jsonl`, `cross_project_patterns.*` |
| 4 Métricas | `python -m src.cli compute-metrics --output-dir data/analysis` | `maintainability_metrics.json`, `comparisons.json` |
| 5 Reporte | `python -m src.cli generate-report` | `reports/quantum_maintainability_report.md` |

Todo de una vez: `python -m src.cli run-pipeline` (unos 30 minutos en una GTX 1660 Ti; casi todo el
tiempo se va en las vistas temporales y en la reasignación de outliers).

## 2. Dónde está cada cosa

| Qué | Ruta |
|-----|------|
| Dataset de origen (SQLite, solo lectura) | `quantum-gh-dataset-2026-10-22/miner.db` (ver `README_DATASET.txt` en esa carpeta) |
| Configuración (umbrales, modelo, semilla) | `config.yaml` |
| Categorías de patrones y palabras clave | `config/quantum_taxonomy.yaml` |
| Código | `src/` (`topic_model.py`, `cross_project.py`, `patterns.py`, `metrics.py`, `report.py`) |
| Tests (182) | `tests/` (`python -m pytest -q`) |
| Issues limpios (seudonimizados) | `data/processed/issues_clean.jsonl` |
| **Resultados** | `data/analysis/` |
| Reporte final | `reports/quantum_maintainability_report.md` |
| Modelo BERTopic guardado | `data/analysis/model/` |

`data/` y `reports/` están en `.gitignore`: **no viajan por git**, hay que compartirlos aparte.

## 3. Los resultados, archivo por archivo (`data/analysis/`)

Empieza por los tres primeros.

| Archivo | Qué es | Columnas clave |
|---------|--------|----------------|
| `cross_project_patterns.csv` | **Archivo principal.** Una fila por tema, marcada si se repite entre repos | `topic_id, name, cross_project, n_repos, n_supporting_repos, n_issues, top_repo, top_repo_share, evenness, keywords, supporting_repos` |
| `topics.jsonl` | Los 151 temas | `topic_id, name, keywords, count, representative_docs, top_repo, top_repo_share, n_repos, repo_specific` |
| `doc_topics.jsonl` | Issue -> tema (`-1` = outlier) | `issue_id` (`owner/repo#numero`), `topic_id`, `probability` |
| `cross_project_patterns.jsonl` | Lo mismo que el CSV más `per_repo` (issues y prevalencia por repo) y `example_issue_ids` | |
| `quantum_patterns.jsonl`, `pattern_summary.csv` | Categorías de la taxonomía por palabras clave (12) con sus issues | `pattern_id, frequency, topic_share, supporting_issue_ids, example_quotes` |
| `candidate_categories.jsonl` | Temas que la taxonomía no explica (candidatos a categoría nueva) | `topic_id, matched_share` |
| `topics_reduced.jsonl`, `doc_topics_reduced.jsonl` | El mismo resultado con los outliers reasignados por similitud (más cobertura, menos calidad) | |
| `topics_over_time.jsonl`, `topics_per_class.jsonl` | Frecuencia de cada tema por intervalo de tiempo / por repo | |
| `maintainability_metrics.json`, `maintainability_summary.csv` | Métricas por repo (tiempo de resolución, Gini, entropía de temas, ...) | |
| `comparisons.json` | Vistas por repo, por familia de SDK y con tope (máx. 1000 issues por repo) | |
| `run_summary.json` | 35 340 issues, 151 temas, 49,9 % de outliers, 3 temas de ruido | |
| `topic_visualization.html` | Gráficos interactivos de BERTopic (ábrelo en el navegador) | |

### Qué significa "patrón entre proyectos" aquí

Un tema se marca `cross_project = True` cuando al menos **3 repos tienen 3 o más** de sus issues y
ningún repo concentra más del **90 %** del tema (`cross_project:` en `config.yaml`). Los outliers nunca
cuentan. Es un criterio generoso: 104 de 151 temas lo cumplen. Cortes más estrictos (calculados desde
`per_repo`):

| Regla | Temas |
|-------|-------|
| 3 repos x 3 issues, repo principal <= 90 % (por defecto) | 104 |
| 5 repos x 5 issues, repo principal <= 70 % | 38 |
| 8 repos x 5 issues, repo principal <= 60 % | 11 |

Cambiar los umbrales no obliga a reentrenar: edita `config.yaml` y ejecuta
`python -m src.cli extract-patterns --output-dir data/analysis`.

## 4. Primeros pasos para el análisis

```python
import pandas as pd
cp = pd.read_csv("data/analysis/cross_project_patterns.csv")
fuertes = cp[(cp.cross_project) & (cp.n_supporting_repos >= 8) & (cp.top_repo_share <= 0.6)]
print(fuertes[["topic_id", "keywords", "n_supporting_repos", "n_issues"]])
```

Para leer un issue de ejemplo: toma un id de `example_issue_ids` y búscalo en
`data/processed/issues_clean.jsonl` (`repo` + `issue_number`) o en `miner.db`.

Para reconstruir el entorno: `py -3.12 -m venv .venv`, instala una versión de `torch` con CUDA y luego
`pip install -r requirements.txt` (importan los pines `click<8.2` y `hdbscan==0.8.40`).

## 5. Léelo antes de confiar en los resultados

1. **Los temas son similitud de texto, no "el mismo bug".** Un tema compartido por 38 repos significa
   redacción parecida. Valida a mano: lee unos 30 issues de los temas 4, 2, 10 y 20 antes de afirmar un
   patrón.
2. **Cerca de la mitad de los issues (49,9 %) son outliers** y no pertenecen a ningún tema, así que los
   patrones describen la mitad del corpus. El modelo de embeddings es genérico (`all-MiniLM-L6-v2`) y
   entiende poco el vocabulario cuántico.
3. **No todo es cuántico.** Los temas de CI/coverage, sphinx, wheels y docstrings son mantenimiento
   general. Sepáralos de pulse, ruido, Clifford, gradientes, transpilación y QASM.
4. **La taxonomía por palabras clave es burda.** `documentation_examples` marca 6 121 issues (17 %).
5. **`gdsfactory/gdsfactory` (1 038 issues) es diseño de chips fotónicos**, probablemente no cuántico, y
   sigue incluido (domina el tema 0). Hay que decidir si se excluye (`input.exclude_repos` en
   `config.yaml`).
6. **Qiskit tiene muchísimos más issues**, así que los temas se inclinan hacia él; por eso los criterios
   limitan la proporción del repo principal.
7. **No verificado:** que dos corridas den temas idénticos (la semilla está fija, pero no corrí dos veces)
   ni el CI de GitHub en Ubuntu/Python 3.11. La spec original (S19-S29) no está guardada en el repo.

## 6. Privacidad

Autores, comentaristas y asignados se reemplazan por seudónimos con sal (`u_<12 hex>`) y las
`@menciones` se enmascaran, tanto en `issues_clean.jsonl` como en todas las salidas. Los nombres de los
repositorios son proyectos públicos; el reporte los anonimiza (`report.anonymize`), pero el CSV y los
JSONL no. Cambia `preprocessing.author_salt` en `config.yaml` para que los seudónimos no se puedan
enlazar con esta versión.
