# Análisis de mantenibilidad de issues de GitHub en software cuántico

Pipeline en Python que analiza issues de GitHub de repositorios con componentes de
computación cuántica (Qiskit, Cirq, PennyLane, Amazon Braket, Q#, etc.) para identificar
patrones de mantenibilidad en productos híbridos cuántico-clásicos.

## Descripción general

El proyecto aborda un vacío en la investigación de ingeniería de software: entender los
desafíos de mantenibilidad de sistemas híbridos cuántico-clásicos, todavía novedosos en la
industria. Aplica modelado de tópicos (BERTopic) y extracción de patrones específicos del
dominio sobre issues de GitHub para identificar modos de falla comunes, cuantificar su
prevalencia y producir recomendaciones accionables.

**Los resultados de la corrida vigente están versionados en el repositorio.** Clonar
alcanza para analizarlos: no hace falta re-ejecutar el pipeline.

## Inicio rápido

### 1. Entorno

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# Windows PowerShell: .\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Los pines de `click<8.2` y `hdbscan==0.8.40` en `requirements.txt` son necesarios: el
pipeline no arranca con otras versiones.

### 2. Datos de entrada

El pipeline lee un dataset SQLite (`miner.db`) cuya ruta declara `input.db_path` en
`config.yaml`. Un argumento `--db` la reemplaza.

El dataset no se versiona: pesa cientos de MB y es el origen de los datos, no un
resultado. `preprocess --input` todavía acepta un JSONL legado, con una línea por issue.

### 3. Ejecutar el pipeline

```bash
# Pipeline completo
python -m src.cli run-pipeline

# O paso por paso
python -m src.cli preprocess
python -m src.cli topic-model
python -m src.cli extract-patterns
python -m src.cli compute-metrics
python -m src.cli generate-report
```

En Linux/macOS: `./run_pipeline.sh`. En Windows: `.\run_pipeline.ps1`. Ambos aceptan la
ruta a `miner.db` como primer argumento y activan `.venv` si existe.

`run-pipeline` redirige **todas** las salidas al directorio de resultados
(`--output-dir`, por defecto `data/analysis`): la visualización y los CSV de resumen
quedan ahí, no en `reports/`, aunque `config.yaml` declare esas rutas. Solo el reporte
Markdown se escribe en `reports/`.

La corrida completa tarda alrededor de 33 minutos con GPU CUDA en un equipo de gama
media. Con CPU no está medida y es bastante más lenta.

### 4. Ver los resultados

- **Reporte**: `reports/quantum_maintainability_report.md`
- **Visualización**: `data/analysis/topic_visualization.html` (abrir en el navegador)
- **Métricas**: `data/analysis/maintainability_metrics.json`
- **Patrones**: `data/analysis/quantum_patterns.jsonl`
- **Patrones entre proyectos**: `data/analysis/cross_project_patterns.csv`

Guía de lectura para el equipo de análisis: `HANDOFF.md`, que incluye la referencia de
cada archivo de salida y de cada campo (sección 3).

## Etapas del pipeline

| Etapa | Comando | Salida | Descripción |
|---|---|---|---|
| 1. Preprocesamiento | `preprocess` | `data/processed/issues_clean.jsonl` | Limpieza, normalización y clasificación |
| 2. Modelado de tópicos | `topic-model` | `data/analysis/topics.jsonl` | Descubrimiento de tópicos con BERTopic |
| 3. Patrones | `extract-patterns` | `data/analysis/quantum_patterns.jsonl` | Extracción de patrones cuánticos |
| 4. Métricas | `compute-metrics` | `data/analysis/maintainability_metrics.json` | Indicadores de mantenibilidad |
| 5. Reporte | `generate-report` | `reports/quantum_maintainability_report.md` | Reporte científico |

## Configuración

Todos los parámetros se ajustan en `config.yaml`:

- **Preprocesamiento**: filtrado de bots por autor (`author_type` Bot, sufijo `[bot]` o
  nombres exactos en `bot_users`), `automated_comment_patterns` anclados para comentarios
  de plantilla, longitud mínima de cuerpo, eliminación de bloques de código, resúmenes de
  código, tracebacks y logs de compilación, eliminación de plantillas
  (`strip_templates`), filtro en dos pasadas que descarta líneas repetidas en al menos
  `repeated_line_min_issues` issues distintos y comentarios repetidos en al menos
  `repeated_comment_min_issues`, descarte de documentos duplicados exactos
  (`drop_exact_duplicates`, se conserva la primera aparición) y descarte de issues con
  menos de `min_chars` caracteres limpios de título y cuerpo.
- **BERTopic**: modelo de embeddings, parámetros de UMAP/HDBSCAN, tamaño mínimo de clúster
  (`--min-topic-size` fija `hdbscan_min_cluster_size`), `reproducible` (siembra UMAP),
  embeddings calculados una vez y cacheados en `paths.cache_dir`, `reduce_outliers`
  (desactivado por defecto; escribe salidas `*_reduced` separadas), `min_df`/`max_df` del
  vectorizador y `domain_stop_words`.
- **Patrones cuánticos**: 12 categorías versionadas en `config/quantum_taxonomy.yaml`.
- **Métricas**: cálculo de Gini y cuantiles de resolución.
- **Reporte**: anonimización y límites de citas.

## Taxonomía de patrones

Las categorías y sus términos viven en `config/quantum_taxonomy.yaml`. El bloque
`quantum_patterns` de `config.yaml` es legado y se ignora.

| Categoría | Descripción |
|---|---|
| `transpilation_compilation` | Fallas de compilación y transpilación de circuitos |
| `noise_error_mitigation` | Ruido, mitigación y corrección de errores |
| `hardware_backend` | Acceso a hardware, calibración y colas |
| `qubit_mapping_routing` | Mapeo de qubits y ruteo |
| `gradients_autodiff` | Circuitos parametrizados y gradientes |
| `performance_scaling` | Rendimiento y memoria del simulador |
| `pulse_control` | Control de pulsos |
| `dependency_version` | Conflictos de versión y dependencias |
| `documentation_examples` | Documentación y ejemplos |
| `algorithm_convergence` | Convergencia de algoritmos variacionales |
| `sim_vs_hardware` | Discrepancias entre simulador y hardware |
| `reproducibility` | Resultados no deterministas |

## Salidas

Las salidas se escriben en `data/analysis/` y están versionadas en el repositorio.

| Archivo | Contenido |
|---|---|
| `topics.jsonl` | Una fila por tópico: nombre, palabras clave, conteo, documentos representativos, `top_repo`, `top_repo_share`, `n_repos`, `repo_specific` |
| `doc_topics.jsonl` | Id de issue (`owner/repo#n`) → id de tópico (`-1` = outlier) y probabilidad |
| `topics_reduced.jsonl`, `doc_topics_reduced.jsonl` | Resultado secundario con los outliers reasignados por similitud de embeddings: más cobertura, menor calidad |
| `cross_project_patterns.{jsonl,csv}` | Por tópico: repos que lo sostienen, prevalencia por repo, proporción del repo principal, uniformidad y marca `cross_project` |
| `quantum_patterns.jsonl`, `pattern_summary.csv`, `candidate_categories.jsonl` | Categorías de la taxonomía y tópicos que la taxonomía no explica |
| `topics_over_time.jsonl`, `topics_per_class.jsonl` | Vistas temporal y por repo (`bertopic.temporal_views: false` las omite; tardan decenas de minutos) |
| `maintainability_metrics.json`, `comparisons.json` | Métricas por repo y agregadas, y comparaciones por repo, por familia y con tope |
| `run_summary.json` | Cantidad de tópicos, proporción de outliers, tópicos de ruido y tópicos específicos de un repo |
| `topic_visualization.html` | Vistas interactivas de BERTopic |

## Privacidad

`preprocessing.anonymize_authors` (activo por defecto) reemplaza autores, comentaristas y
asignados por seudónimos con sal (`u_<12 hex>`, estables por persona, sin distinguir
mayúsculas) y enmascara `@menciones` y correos electrónicos en títulos, cuerpos y
comentarios. El filtrado de bots usa el nombre real antes de seudonimizar. Cambiar
`author_salt` hace que los seudónimos no se puedan enlazar con una versión anterior.

Los nombres de repositorio son proyectos públicos y se anonimizan solo en el reporte
(`report.anonymize`).

Alcance completo del enmascaramiento, decisiones aceptadas y artefactos que no se
comparten: `docs/data-handling.md`.

## Tests

```bash
pytest -q
pytest --cov=src tests/
```

## Estructura del proyecto

```
src/                        Código del pipeline
├── cli.py                  Punto de entrada (Typer)
├── config.py               Carga de configuración
├── models.py               Modelos de datos y enmascaramiento
├── preprocess.py           Limpieza y normalización
├── topic_model.py          Modelado de tópicos con BERTopic
├── patterns.py             Extracción de patrones cuánticos
├── metrics.py              Métricas de mantenibilidad
└── report.py               Generación del reporte
tests/                      Suite de tests
config/                     Taxonomía de patrones versionada
docs/                       Política de manejo de datos
data/analysis/              Resultados versionados
reports/                    Reporte entregable
.github/workflows/          Integración continua
config.yaml                 Configuración del pipeline
run_pipeline.sh             Ejecutor para Linux/macOS
run_pipeline.ps1            Ejecutor para Windows
HANDOFF.md                  Guía de análisis para el equipo
```

No se versionan: `data/processed/`, `data/cache/`, `data/analysis/model/` y las corridas
previas al enmascaramiento. Ver `.gitignore` y `docs/data-handling.md`.

## Citación

Si usás este trabajo en una investigación, citá:

```bibtex
@misc{quantum-issues-analysis,
  title={Quantum Software Maintainability Analysis via GitHub Issue Mining},
  year={2026},
  note={Analysis of hybrid quantum-classical software maintainability patterns}
}
```
