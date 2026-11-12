# Quantum Software Maintainability Analysis Report

*Generated: 2026-11-12T22:13:46+00:00*
*Anonymized: True*

# Executive Summary

This report presents a systematic analysis of GitHub issues from repositories utilizing quantum computing components (Qiskit, Cirq, PennyLane, Amazon Braket, Q#, and related frameworks). The objective is to identify maintainability patterns specific to hybrid quantum-classical software products, which represent a novel paradigm in the software industry.

## Key Findings

- **Repositories Analyzed**: 105
- **Total Issues**: 35340
- **Median Resolution Time**: 20.1 days
- **Resolution Outcomes (closed issues)**: {'completed': 28387, 'not_planned': 1082, 'duplicate': 84}
- **Contributor Concentration (Gini)**: 0.77
- **Quantum-Specific Patterns Identified**: 12 categories, 17665 total occurrences

## Quantum Pattern Taxonomy

The analysis revealed eight distinct categories of quantum-specific maintainability challenges:

| Category | Frequency | Description |
|----------|-----------|-------------|
| Documentation and examples | 6121 | Issues related to documentation examples in quantum software development Associa... |
| SDK, version and dependency breakage | 2134 | Issues related to dependency version in quantum software development Associated ... |
| Transpilation and compilation | 1695 | Issues related to transpilation compilation in quantum software development Asso... |
| Algorithm-level questions | 1452 | Issues related to algorithm convergence in quantum software development Associat... |
| Backend, hardware access and queues | 998 | Issues related to hardware backend in quantum software development Associated to... |
| Reproducibility | 953 | Issues related to reproducibility in quantum software development Associated top... |
| Pulse-level control | 906 | Issues related to pulse control in quantum software development Associated topic... |
| Parameterized circuits and gradients | 890 | Issues related to gradients autodiff in quantum software development Associated ... |

## Maintainability Implications

Hybrid quantum-classical systems exhibit unique maintainability characteristics not captured by traditional software metrics. Hardware dependencies, algorithmic convergence uncertainties, and the simulator-hardware gap introduce failure modes that require specialized monitoring and mitigation strategies.

# Methodology

## Data Collection

Issues and comments were extracted from GitHub repositories identified as using quantum computing frameworks. The dataset includes issues from repositories matching the quantum taxonomy terms (for example: transpile, transpiler, transpilation, basis gates, optimization level).

## Preprocessing

Raw GitHub issues underwent the following cleaning steps:
1. **Bot filtering**: Removal of automated comments from dependabot, renovate, github-actions, and similar bots
2. **Normalization**: Timestamps converted to UTC ISO8601, usernames lowercased
3. **Markdown stripping**: Code fences, inline code, URLs, and mentions replaced with placeholders
4. **Deduplication**: Near-duplicate comments removed
5. **Classification**: Issues typed as bug, feature, question, or discussion based on labels and content heuristics

## Topic Modeling

We employed BERTopic (Grootendorst, 2022) for unsupervised topic discovery:
- **Embedding Model**: all-MiniLM-L6-v2 (sentence-transformers)
- **Dimensionality Reduction**: UMAP (n_neighbors=15, n_components=5)
- **Clustering**: HDBSCAN (min_cluster_size=30)
- **Topic Representation**: c-TF-IDF with KeyBERT-inspired representation
- **Minimum Topic Size**: 30

## Pattern Extraction

Quantum-specific patterns were identified through keyword matching against a curated taxonomy of 115 terms across 12 categories, validated against discovered topics.

## Metrics Computation

Maintainability metrics were computed per repository and aggregated:
- **Resolution Time**: Median days from creation to closure (by issue type)
- **Reopen Rate**: Proxy via comments after closure date
- **Contributor Concentration**: Gini coefficient of issue authorship
- **Quantum Keyword Ratios**: Proportion of issues mentioning each pattern category
- **Topic Entropy**: Shannon entropy of topic distribution per repository

# Quantum Pattern Taxonomy

## Documentation and examples (`documentation_examples`)
**Frequency**: 6121 issues
**Description**: Issues related to documentation examples in quantum software development Associated topics: 29_sphinx_theme_version sphinx_sphinx panels, 1_cuda_gpu_cudaq_nvidia, 2_pulse_schedule_pulses_duration.
**Keywords**: documentation, docs, tutorial, docstring, example notebook, broken link, typo in docs, outdated example
**Representative Quotes**:
1. "Fix the Quantum Chemistry tutorial and change the serverless dispatch to the server dispatch when the bug is removed"
2. "3e78d08]([URL] Read the [comment docs]([URL]"
3. "Writing examples in docstrings inside covalent @user commented on [Mon Nov 29 2021]([URL] - [ ] executor - [ ] _results_manager - [ ] _shared_files - [ ] _workflow @user @user this can be closed I pre..."

## SDK, version and dependency breakage (`dependency_version`)
**Frequency**: 2134 issues
**Description**: Issues related to dependency version in quantum software development Associated topics: 55_deprecation_deprecated_remove deprecated_deprecations, 2_pulse_schedule_pulses_duration, 24_migrated_nature migrated_migration needs_migrate qiskit_nature.
**Keywords**: deprecated, deprecation, qiskit-aer, breaking change, qiskit-terra, modulenotfounderror, qiskit-ibmq, import error, dependency conflict, incompatible version
**Representative Quotes**:
1. "I'm not totally sure if the /download and /upload endpoints will be deprecated as a result or if they are meant to be general purpose to store other objects besides just the Result object, will need t..."
2. "Resolve module import errors when running refactor files Someone with a deep knowledge of module import needs to ensure that the files in the refactor folder can be run without getting the following e..."
3. "If Covalent has a plugin-breaking change, there needs to be a check for non up-to-date plugins, as well as instructions for what to do"

## Transpilation and compilation (`transpilation_compilation`)
**Frequency**: 1695 issues
**Description**: Issues related to transpilation compilation in quantum software development Associated topics: 36_pass manager_passes_manager_preset, 2_pulse_schedule_pulses_duration, 115_popqc_performance regression_regression_performance.
**Keywords**: transpiler, transpile, transpilation, pass manager, basis gates, optimization level, unroller, gate decomposition, circuit compilation
**Representative Quotes**:
1. "Update action_build workflow to transpile all the re-usable actions Currently the [CODE] github workflow only transpiles the [CODE] re-usable action, however it should be updated to take a list of re-..."
2. "Optimization level 3 should now synthesize the identity properly to an empty circuit"
3. "For example, most quantum algorithms require many circuit compilations during execution"

## Algorithm-level questions (`algorithm_convergence`)
**Frequency**: 1452 issues
**Description**: Issues related to algorithm convergence in quantum software development Associated topics: 1_cuda_gpu_cudaq_nvidia, 6_gradient_qnode_gradients_hessian, 30_keras_training_pqc_benchmark.
**Keywords**: optimizer, vqe, variational, qaoa, ansatz, grover, shor, cost function, convergence, phase estimation
**Representative Quotes**:
1. "Edit: returning loss and optimizer and using the "not working" version of the function now"
2. "Recursion error while using QAOA from qiskit I am using [CODE] from the [CODE] package"
3. "Write a Covalentified version of the Pennylane Variational Classifier tutorial Include in [Covalent tutorials]([URL] a version of the [Pennylane variational classifier tutorial]([URL] which is updated..."

## Backend, hardware access and queues (`hardware_backend`)
**Frequency**: 998 issues
**Description**: Issues related to hardware backend in quantum software development Associated topics: 7_pyquil_qvm_quil_quilc, 16_qbraid_braket_amazon_amazon braket, 2_pulse_schedule_pulses_duration.
**Keywords**: calibration, queue, rigetti, ionq, quantum hardware, backend configuration, quantum processor, job failed, ibm_quantum, device availability
**Representative Quotes**:
1. "A more complex but potentially more stable and performant solution suggested by @user is to use a message queue to notify when the results is ready and use a websocket to pass this notification to the..."
2. "OS Dispatcher Refactor: Implement workflow-dispatch The Dispatcher API will be listening to the queue for new workflow submissions and pick up dispatch jobs automatically"
3. "Supervisord dispatcher queue consumer integration When [CODE] is called, we want it to automatically start the queue consumer"

## Reproducibility (`reproducibility`)
**Frequency**: 953 issues
**Description**: Issues related to reproducibility in quantum software development Associated topics: 83_seed_random_seeding_seeds, 9_mesolve_time dependent_steady_propagator, 91_flaky_tcomplexity_fermionic_simulation_test_gates fermionic_simulation_test.
**Keywords**: seed, reproducible, deterministic, stochastic, random seed, non-deterministic, different runs
**Representative Quotes**:
1. "However, the list order is not deterministic"
2. "Fix flaky Circuit insert test When running the tests on a fresh checkout I got the following failure which should be reproducible via: [CODE_BLOCK] [CODE_BLOCK] This was reported on [CODE] The hypothe..."
3. "Reproducible circuits Hi I am trying to get reproducible circuits from BQSKit for the same qiskit circuit but I keep getting circuits with different depths and gate counts"

## Pulse-level control (`pulse_control`)
**Frequency**: 906 issues
**Description**: Issues related to pulse control in quantum software development Associated topics: 2_pulse_schedule_pulses_duration, 9_mesolve_time dependent_steady_propagator, 45_openqasm_grammar_openqasm3_language.
**Keywords**: pulse, waveform, openpulse, drive channel
**Representative Quotes**:
1. "I’d be interested in contributing to such an effort Here in the @user, we have a lot of Julia-based tooling for things like fast quantum state tomography with bootstrapping, generating transport wavef..."
2. ", the Hamiltonian); qubit calibration/tuning protocols; or pulse-level optimization to enhance gate fidelity/suppress noise, etc"
3. "Applied 22, 034066 (2024) - Direct pulse-level compilation of arbitrary quantum logic gates on superconducting qutrits"

## Parameterized circuits and gradients (`gradients_autodiff`)
**Frequency**: 890 issues
**Description**: Issues related to gradients autodiff in quantum software development Associated topics: 6_gradient_qnode_gradients_hessian, 14_jax_jit_jaxpr_jax jit, 13_tensor_torch_pyhd3eb1b0_0_dmrg.
**Keywords**: gradient, autograd, differentiable, parameterized circuit, parameter-shift, backprop, autodiff, parameter binding, adjoint differentiation, parametrized circuit
**Representative Quotes**:
1. "I’m trying to use a Nesterov optimiser from the penny lane library to perform the gradient descent optimization"
2. "The loss is flat because the [gradients computed]([URL] in [CODE] are empty"
3. "Optimization not progressing with PyTorch This issue is similar to Issue #issue: when using PyTorch with Covalent, the gradients are not evaluated properly"

## Simulator performance and memory (`performance_scaling`)
**Frequency**: 740 issues
**Description**: Issues related to performance scaling in quantum software development Associated topics: 27_memory_qrisp tests_mb_mb qrisp, 1_cuda_gpu_cudaq_nvidia, 38_qualtran bloqs_qualtran_bloqs_bloqs qsp.
**Keywords**: timeout, large circuit, memory usage, qubit count, execution time, circuit depth, out of memory, simulation time, memory error, slow simulation
**Representative Quotes**:
1. "Should we add a timeout to the github test action"
2. "| From Will: this file will store "stuff from the multiprocessing info queue generated at execution time, such as a slurm job ID"
3. "110 - Benchmark after topological sort, asyncio + result DB which would be the performance improvement in this release - Update RTD & README (verify with @user) citing metrics that indicate performanc..."

## Noise and error mitigation (`noise_error_mitigation`)
**Frequency**: 738 issues
**Description**: Issues related to noise error mitigation in quantum software development Associated topics: 22_noise_noise model_noise models_model, 1_cuda_gpu_cudaq_nvidia, 30_keras_training_pqc_benchmark.
**Keywords**: noise model, error mitigation, depolarizing, error correction, decoherence, readout error, twirling, zero noise extrapolation, gate fidelity, crosstalk
**Representative Quotes**:
1. "I believe the noise model probablistically won't always cause enough photon loss to fock |0>"
2. "I envision a workflow suggested below to allow error mitigation: [CODE_BLOCK] Both lines should be able to run in parallel via a futures request"
3. "Throw an error or warning if noise model is passed to incompatible target If a noise model is passed along to a target that doesn't support noise, we run it sans noise without telling the user"

## Qubit mapping and routing (`qubit_mapping_routing`)
**Frequency**: 665 issues
**Description**: Issues related to qubit mapping routing in quantum software development Associated topics: 36_pass manager_passes_manager_preset, 115_popqc_performance regression_regression_performance, 1_cuda_gpu_cudaq_nvidia.
**Keywords**: routing, coupling map, sabre, initial layout, qubit mapping, layout pass, stochastic swap, swap insertion, qubit placement
**Representative Quotes**:
1. "__call__ routing"
2. "get_running_loop() RuntimeError: no running event loop [CODE_BLOCK] routing"
3. "egg/bqskit/passes/mapping/routing/pam"

## Simulator vs hardware discrepancy (`sim_vs_hardware`)
**Frequency**: 373 issues
**Description**: Issues related to sim vs hardware in quantum software development Associated topics: 2_pulse_schedule_pulses_duration, 1_cuda_gpu_cudaq_nvidia, 28_statevector_qcfinal_probability_near clifford.
**Keywords**: discrepancy, different results, fake backend, shot count
**Representative Quotes**:
1. "This creates a discrepancy in the server status"
2. "~~There's some discrepancy here"
3. "* (UX) Even if users provide default arguments (say, a dummy file path in the above sample), the workflow would produce different results depending on whether it is dispatched as a Covalent workflow o..."

# Maintainability Metrics

## Aggregated Metrics

| Metric | Value |
|--------|-------|
| Total Repositories | 105 |
| Total Issues | 35340 |
| Median Resolution Time (days) | 20.1 |
| Resolution Outcomes (closed) | {'completed': 28387, 'not_planned': 1082, 'duplicate': 84} |
| Contributor Gini Coefficient | 0.772 |
| Avg Issues per Repository | 336.6 |

## Per-Repository Metrics

| Repository    |   Total Issues |   Open |   Closed | Median Resolution (days)   | Outcomes                                                |   Gini |   Contributors |   Topic Entropy |
|:--------------|---------------:|-------:|---------:|:---------------------------|:--------------------------------------------------------|-------:|---------------:|----------------:|
| Repo_bf7abf43 |            776 |     68 |      708 | 17.9                       | {'completed': 675, 'not_planned': 33}                   |  0.748 |             52 |            1.8  |
| Repo_8eec19c3 |            123 |     34 |       89 | 29.8                       | {'completed': 87, 'not_planned': 2}                     |  0.49  |             41 |            3.95 |
| Repo_923ae80a |             53 |      8 |       45 | 26.7                       | {'completed': 45}                                       |  0.604 |              7 |            2.95 |
| Repo_bfdaf5f6 |             57 |      4 |       53 | 28.8                       | {'completed': 53}                                       |  0.634 |              8 |            3.88 |
| Repo_8a2f7eff |             73 |     13 |       60 | 63.6                       | {'completed': 60}                                       |  0.685 |             11 |            3.22 |
| Repo_0d4c4017 |           1306 |    382 |      924 | 26.1                       | {'completed': 919, 'duplicate': 4, 'not_planned': 1}    |  0.75  |            196 |            2.61 |
| Repo_edd3c8b9 |             46 |     16 |       30 | 11.1                       | {'completed': 30}                                       |  0.14  |             39 |            0.95 |
| Repo_a24f6690 |             33 |     24 |        9 | 13.7                       | {'completed': 9}                                        |  0.347 |             20 |            2.06 |
| Repo_c743ebe8 |            488 |    174 |      314 | 22.0                       | {'completed': 290, 'not_planned': 19, 'duplicate': 5}   |  0.702 |             64 |            3.78 |
| Repo_3d565e3d |           1674 |    274 |     1400 | 17.1                       | {'completed': 1379, 'not_planned': 21}                  |  0.717 |            345 |            4.27 |
| Repo_48f701e4 |            125 |     23 |      102 | 14.2                       | {'completed': 101, 'not_planned': 1}                    |  0.53  |             50 |            3.57 |
| Repo_e33a75f9 |            158 |     31 |      127 | 13.9                       | {'completed': 127}                                      |  0.448 |             78 |            4.75 |
| Repo_a913fade |              1 |      0 |        1 | 6.8                        | {'completed': 1}                                        |  0     |              1 |            0    |
| Repo_134614d3 |             21 |      7 |       14 | 19.1                       | {'completed': 14}                                       |  0.286 |              5 |            2.58 |
| Repo_2587cfac |           5731 |    725 |     5006 | 30.2                       | {'completed': 4728, 'not_planned': 270, 'duplicate': 8} |  0.751 |           1119 |            5.35 |
| Repo_d94af77b |            978 |    198 |      780 | 20.1                       | {'completed': 770, 'not_planned': 10}                   |  0.539 |            398 |            4.53 |
| Repo_c1f9dc98 |            309 |     45 |      264 | 67.1                       | {'completed': 263, 'not_planned': 1}                    |  0.772 |             58 |            4.08 |
| Repo_0546661a |            205 |     63 |      142 | 18.7                       | {'completed': 142}                                      |  0.721 |             31 |            3.91 |
| Repo_fe688cb1 |             46 |      8 |       38 | 24.5                       | {'completed': 36, 'not_planned': 2}                     |  0.681 |              9 |            2.85 |
| Repo_e65039e1 |             36 |      0 |       36 | 36.8                       | {'completed': 32, 'not_planned': 4}                     |  0.26  |             25 |            2.73 |
| Repo_f7804a41 |            545 |     85 |      460 | 11.9                       | {'completed': 455, 'not_planned': 5}                    |  0.8   |             71 |            4.82 |
| Repo_eea10b59 |            495 |    162 |      333 | 11.2                       | {'completed': 308, 'not_planned': 21, 'duplicate': 4}   |  0.747 |             35 |            3.31 |
| Repo_a35add70 |            251 |     21 |      230 | 10.8                       | {'completed': 230}                                      |  0.605 |             85 |            4.06 |
| Repo_b37c7c9c |            207 |     97 |      110 | 90.0                       | {'completed': 110}                                      |  0.747 |             32 |            4.17 |
| Repo_7de99b4a |             28 |     24 |        4 | 65.4                       | {'completed': 4}                                        |  0.643 |              5 |            3.1  |
| Repo_416588bf |            115 |     12 |      103 | 13.0                       | {'completed': 103}                                      |  0.584 |             36 |            3.81 |
| Repo_d2f53349 |            340 |     41 |      299 | 6.7                        | {'completed': 299}                                      |  0.796 |             63 |            3.26 |
| Repo_b259a373 |            187 |     14 |      173 | 62.1                       | {'completed': 164, 'duplicate': 1, 'not_planned': 8}    |  0.653 |             23 |            4    |
| Repo_cd9a052d |            176 |     19 |      157 | 26.0                       | {'completed': 153, 'not_planned': 4}                    |  0.478 |             72 |            3.55 |
| Repo_16a7a8a3 |              3 |      3 |        0 | N/A                        | {}                                                      |  0     |              3 |           -0    |
| Repo_1f225676 |             43 |      1 |       42 | 113.0                      | {'completed': 42}                                       |  0.66  |              8 |            3.95 |
| Repo_3583ae5d |             36 |     22 |       14 | 48.1                       | {'completed': 14}                                       |  0.382 |             16 |            3.17 |
| Repo_80dfc9af |            493 |    153 |      340 | 12.2                       | {'completed': 338, 'not_planned': 2}                    |  0.797 |             68 |            2.33 |
| Repo_133e4390 |            294 |     77 |      217 | 6.1                        | {'completed': 217}                                      |  0.843 |             32 |            3.01 |
| Repo_4829e4a9 |             87 |     33 |       54 | 11.5                       | {'completed': 54}                                       |  0.5   |             32 |            2.35 |
| Repo_321db3b7 |             34 |      5 |       29 | 7.9                        | {'completed': 29}                                       |  0.511 |             13 |            3.32 |
| Repo_e45f8fb0 |             84 |     25 |       59 | 20.1                       | {'completed': 59}                                       |  0.487 |             38 |            3.43 |
| Repo_1eaffd16 |            222 |     85 |      137 | 10.6                       | {'completed': 133, 'not_planned': 3, 'duplicate': 1}    |  0.653 |             66 |            2.64 |
| Repo_1ba02c8e |             82 |     25 |       57 | 6.9                        | {'completed': 55, 'not_planned': 2}                     |  0.471 |             33 |            2.26 |
| Repo_677e03cf |             80 |      9 |       71 | 13.0                       | {'completed': 69, 'not_planned': 2}                     |  0.419 |             36 |            2.86 |
| Repo_e3418ccb |            363 |    149 |      214 | 10.9                       | {'completed': 194, 'not_planned': 14, 'duplicate': 6}   |  0.764 |             48 |            3.36 |
| Repo_be55b9e4 |             58 |     20 |       38 | 29.5                       | {'completed': 37, 'not_planned': 1}                     |  0.474 |             19 |            3.92 |
| Repo_9e887faf |              2 |      1 |        1 | 1.7                        | {'completed': 1}                                        |  0     |              2 |            0    |
| Repo_3c0ce5f5 |             27 |      8 |       19 | 154.9                      | {'completed': 15, 'not_planned': 4}                     |  0.265 |             19 |            2.73 |
| Repo_8ea4b746 |           1038 |     52 |      986 | 5.2                        | {'completed': 910, 'not_planned': 71, 'duplicate': 5}   |  0.716 |            222 |            1.22 |
| Repo_71d711c0 |             13 |      3 |       10 | 2.9                        | {'completed': 10}                                       |  0.462 |              3 |            2.32 |
| Repo_888694ad |              2 |      0 |        2 | 75.7                       | {'completed': 2}                                        |  0     |              2 |            1    |
| Repo_25cf2e0d |             23 |     11 |       12 | 33.7                       | {'completed': 12}                                       |  0.23  |             17 |            2.75 |
| Repo_6ac7f133 |             15 |      2 |       13 | 6.2                        | {'completed': 12, 'not_planned': 1}                     |  0.453 |              5 |            2.52 |
| Repo_df6747d9 |            233 |     65 |      168 | 5.9                        | {'completed': 165, 'not_planned': 2, 'duplicate': 1}    |  0.36  |            131 |            3.16 |
| Repo_cd1cc456 |            641 |    188 |      453 | 23.2                       | {'completed': 451, 'not_planned': 2}                    |  0.696 |            122 |            3.29 |
| Repo_d3aea5b2 |            880 |    224 |      656 | 20.3                       | {'completed': 610, 'not_planned': 43, 'duplicate': 3}   |  0.781 |             79 |            4.22 |
| Repo_e64a503d |            114 |      9 |      105 | 36.0                       | {'completed': 99, 'not_planned': 6}                     |  0.625 |             30 |            3.82 |
| Repo_f8caa4d9 |             46 |      7 |       39 | 9.0                        | {'completed': 39}                                       |  0.386 |             24 |            3.45 |
| Repo_8fdaa6be |             60 |     16 |       44 | 54.6                       | {'completed': 44}                                       |  0.627 |             10 |            3.83 |
| Repo_31f898b3 |             54 |      0 |       54 | 23.4                       | {'completed': 54}                                       |  0.539 |             20 |            1.92 |
| Repo_bd633d70 |             44 |      5 |       39 | 15.9                       | {'completed': 39}                                       |  0.413 |             21 |            3.75 |
| Repo_de80ceea |             49 |     11 |       38 | 33.2                       | {'completed': 28, 'not_planned': 9, 'duplicate': 1}     |  0.402 |             25 |            2.52 |
| Repo_d253539f |             34 |      6 |       28 | 43.9                       | {'completed': 27, 'duplicate': 1}                       |  0.654 |              9 |            1.79 |
| Repo_b148d73c |            889 |    100 |      789 | 15.5                       | {'completed': 741, 'not_planned': 45, 'duplicate': 3}   |  0.674 |            239 |            2.17 |
| Repo_9ee8f066 |             76 |      8 |       68 | 31.0                       | {'completed': 62, 'not_planned': 5, 'duplicate': 1}     |  0.436 |             28 |            0.83 |
| Repo_255c3934 |            276 |    103 |      173 | 54.6                       | {'completed': 170, 'not_planned': 3}                    |  0.53  |             86 |            3.36 |
| Repo_f639e53d |             89 |     22 |       67 | 13.7                       | {'completed': 67}                                       |  0.533 |             38 |            3.14 |
| Repo_69f2371c |            364 |     37 |      327 | 21.0                       | {'completed': 326, 'not_planned': 1}                    |  0.73  |             49 |            3.62 |
| Repo_a692b87d |            271 |     18 |      253 | 62.2                       | {'completed': 228, 'not_planned': 25}                   |  0.638 |             30 |            4.5  |
| Repo_774331b2 |            480 |     89 |      391 | 42.6                       | {'not_planned': 16, 'completed': 366, 'duplicate': 9}   |  0.679 |            142 |            2.91 |
| Repo_1b815bdf |            317 |     27 |      290 | 28.8                       | {'completed': 256, 'not_planned': 32, 'duplicate': 2}   |  0.834 |             26 |            3.24 |
| Repo_b74b5c99 |              1 |      1 |        0 | N/A                        | {}                                                      |  0     |              1 |            0    |
| Repo_11fb04fc |            607 |     53 |      554 | 18.8                       | {'completed': 548, 'duplicate': 1, 'not_planned': 5}    |  0.731 |             85 |            5.61 |
| Repo_16776d48 |            485 |    109 |      376 | 37.8                       | {'completed': 373, 'not_planned': 3}                    |  0.74  |             85 |            3.97 |
| Repo_5d59ad4c |            599 |     18 |      581 | 56.7                       | {'completed': 481, 'not_planned': 97, 'duplicate': 3}   |  0.759 |            100 |            3.29 |
| Repo_f95263fd |            439 |     54 |      385 | 28.1                       | {'completed': 363, 'not_planned': 22}                   |  0.701 |            102 |            4.18 |
| Repo_3e6a6e7b |            154 |     44 |      110 | 12.4                       | {'completed': 110}                                      |  0.445 |             73 |            2.97 |
| Repo_944ad850 |             51 |      8 |       43 | 3.9                        | {'completed': 43}                                       |  0.264 |             35 |            3.22 |
| Repo_6cd3bd0c |           2505 |     99 |     2406 | 48.4                       | {'completed': 2320, 'not_planned': 84, 'duplicate': 2}  |  0.81  |            319 |            5.89 |
| Repo_7c4f6594 |            342 |     16 |      326 | 38.7                       | {'completed': 317, 'not_planned': 9}                    |  0.636 |            100 |            4.81 |
| Repo_c181dde8 |            587 |    233 |      354 | 45.0                       | {'completed': 336, 'not_planned': 18}                   |  0.795 |             53 |            2.48 |
| Repo_a847de82 |             98 |     12 |       86 | 68.2                       | {'completed': 84, 'not_planned': 2}                     |  0.649 |             20 |            3.76 |
| Repo_28c85552 |            459 |     76 |      383 | 12.1                       | {'completed': 382, 'not_planned': 1}                    |  0.735 |            109 |            3.42 |
| Repo_37848d4e |            260 |     31 |      229 | 16.0                       | {'completed': 225, 'not_planned': 4}                    |  0.678 |             65 |            4.17 |
| Repo_18fd2c10 |             55 |     20 |       35 | 6.1                        | {'completed': 35}                                       |  0.544 |             19 |            3.15 |
| Repo_3c2944e6 |            137 |     83 |       54 | 47.5                       | {'completed': 54}                                       |  0.655 |             33 |            3.62 |
| Repo_fee9645c |            370 |     61 |      309 | 21.0                       | {'completed': 308, 'not_planned': 1}                    |  0.786 |             22 |            1.95 |
| Repo_5e8f7f32 |             90 |     16 |       74 | 5.1                        | {'completed': 74}                                       |  0.632 |             26 |            2.77 |
| Repo_61233351 |           1060 |     86 |      974 | 33.5                       | {'completed': 972, 'duplicate': 2}                      |  0.495 |            475 |            3.63 |
| Repo_4833c126 |             62 |      9 |       53 | 0.8                        | {'completed': 53}                                       |  0.751 |              7 |            4.1  |
| Repo_16a98aa8 |            804 |    217 |      587 | 20.1                       | {'completed': 581, 'not_planned': 5, 'duplicate': 1}    |  0.648 |            206 |            2.82 |
| Repo_f3aca179 |            155 |     16 |      139 | 7.5                        | {'completed': 139}                                      |  0.544 |             52 |            2.93 |
| Repo_c6ba34ad |             32 |     10 |       22 | 0.7                        | {'completed': 22}                                       |  0.226 |             23 |            2.52 |
| Repo_549f6999 |             82 |      2 |       80 | 1.3                        | {'completed': 80}                                       |  0.644 |             23 |            4.36 |
| Repo_31ed59a2 |             49 |      7 |       42 | 3.9                        | {'completed': 42}                                       |  0.575 |             18 |            2.65 |
| Repo_006bf3c5 |             66 |     20 |       46 | 4.7                        | {'completed': 46}                                       |  0.58  |             20 |            3.29 |
| Repo_f78c5185 |            377 |     33 |      344 | 68.5                       | {'completed': 313, 'not_planned': 17, 'duplicate': 14}  |  0.591 |            137 |            3.82 |
| Repo_c289da06 |             42 |      1 |       41 | 2.7                        | {'completed': 41}                                       |  0.339 |             25 |            3.93 |
| Repo_a046f77d |              2 |      0 |        2 | 243.7                      | {'completed': 2}                                        |  0     |              2 |           -0    |
| Repo_5345a97e |            222 |     22 |      200 | 5.2                        | {'completed': 200}                                      |  0.559 |             69 |            2.15 |
| Repo_20659ff4 |             37 |     13 |       24 | 75.7                       | {'completed': 24}                                       |  0.553 |             13 |            2.13 |
| Repo_e6fad09e |            962 |     76 |      886 | 36.7                       | {'completed': 838, 'not_planned': 47, 'duplicate': 1}   |  0.824 |             85 |            5.07 |
| Repo_884f5599 |            164 |     11 |      153 | 5.4                        | {'completed': 153}                                      |  0.832 |             13 |            3.92 |
| Repo_60b2528f |            243 |     37 |      206 | 13.5                       | {'completed': 180, 'not_planned': 25, 'duplicate': 1}   |  0.73  |             13 |            4.76 |
| Repo_e87623a8 |            608 |      7 |      601 | 8.5                        | {'completed': 566, 'not_planned': 33, 'duplicate': 2}   |  0.876 |             36 |            3.75 |
| Repo_10d6f79b |             27 |      9 |       18 | 7.2                        | {'completed': 18}                                       |  0.543 |              9 |            2.22 |
| Repo_89b459fb |             76 |     11 |       65 | 232.3                      | {'completed': 50, 'not_planned': 15}                    |  0.522 |             30 |            3.07 |
| Repo_8fa7aa18 |            233 |     19 |      214 | 26.1                       | {'completed': 212, 'not_planned': 1, 'duplicate': 1}    |  0.52  |             89 |            3.06 |
| Repo_7e3af9f2 |            299 |     56 |      243 | 62.1                       | {'completed': 240, 'not_planned': 2, 'duplicate': 1}    |  0.77  |             31 |            0.75 |

## Issue Type Distribution

| Type | Count | Percentage |
|------|-------|------------|
| bug | 17139 | 48.5% |
| feature | 10377 | 29.4% |
| discussion | 7008 | 19.8% |
| question | 816 | 2.3% |

## Quantum Pattern Prevalence

| Pattern | Prevalence |
|---------|------------|
| documentation_examples | 17.3% |
| dependency_version | 6.0% |
| transpilation_compilation | 4.8% |
| algorithm_convergence | 4.1% |
| hardware_backend | 2.8% |
| reproducibility | 2.7% |
| pulse_control | 2.6% |
| gradients_autodiff | 2.5% |
| performance_scaling | 2.1% |
| noise_error_mitigation | 2.1% |
| qubit_mapping_routing | 1.9% |
| sim_vs_hardware | 1.1% |

# Comparative Discussion

## Quantum vs Classical Maintainability

Traditional software maintainability metrics (resolution time, resolution outcomes, contributor concentration) provide a baseline, but quantum software introduces additional dimensions:

### 1. Hardware Dependency Risk
Unlike classical software, quantum programs depend on physical quantum hardware with:
- Calibration drift requiring frequent recalibration
- Queue times affecting development velocity
- Device availability impacting reproducibility
- **Evidence**: 2.8% of issues mention hardware/backend concerns

### 2. Algorithmic Uncertainty
Variational quantum algorithms (VQE, QAOA) exhibit:
- Barren plateaus preventing gradient-based optimization
- Convergence to local minima
- Sensitivity to ansatz choice and initialization
- **Evidence**: 4.1% of issues discuss convergence

### 3. Simulator-Hardware Gap
Results on noiseless simulators often diverge from hardware execution due to:
- Noise model fidelity limitations
- Shot noise and readout errors
- Crosstalk and correlated errors not captured in simulation
- **Evidence**: 1.1% of issues report discrepancies

### 4. Compilation Fragility
Quantum circuit transpilation introduces:
- Non-deterministic routing/layout decisions
- Optimization-level-dependent behavior
- Basis gate decomposition variations
- **Evidence**: 4.8% of issues involve transpilation

### 5. Gradient Computation Challenges
Hybrid quantum-classical gradients require:
- Parameter-shift rules (circuit evaluations scale with parameters)
- Adjoint differentiation (simulator-only)
- Framework-specific autodiff integration (PennyLane, TFQ, JAX)
- **Evidence**: 2.5% of issues involve gradients

## Topic Model Insights

The BERTopic model discovered 102 dominant thematic clusters across repositories, revealing that quantum issues naturally organize around:
- Hardware access and backend management
- Algorithm implementation and debugging
- Framework version compatibility
- Result validation and reproducibility

## Implications for Practitioners

1. **Monitoring**: Traditional CI/CD insufficient; need quantum-specific health checks (calibration status, queue times)
2. **Testing**: Require hardware-in-the-loop testing, not just simulator validation
3. **Dependencies**: Pin quantum framework versions rigorously; breaking changes are frequent
4. **Documentation**: Hardware-specific behavior must be documented alongside algorithmic logic
5. **Skills**: Teams need quantum physics literacy alongside software engineering

# Cross-Project Patterns

A topic is a cross-project pattern when at least 3 repositories each hold 3 or more of its issues and no single repository holds more than 90% of it. Outlier issues are never counted.

**114 of 162 topics qualify.**

| Topic | Keywords | Repos | Issues | Top repo share | Evenness |
|-------|----------|-------|--------|----------------|----------|
| 17 | changelog, actions, action, release notes, workflow, github actions | 24 | 214 | 14% (Repo_6cd3bd0c) | 0.85 |
| 1 | cuda, gpu, cudaq, nvidia, cuda quantum, 08 22 | 19 | 752 | 68% (Repo_0d4c4017) | 0.41 |
| 29 | sphinx, theme, version sphinx, sphinx panels, sphinx version, sphinx documentation | 18 | 141 | 13% (Repo_e6fad09e) | 0.88 |
| 30 | keras, training, pqc, benchmark, h1, qcnn | 17 | 133 | 22% (Repo_f78c5185) | 0.85 |
| 35 | flake, wycheproof, flaky, set_dly, simphony, notebooks | 15 | 113 | 17% (Repo_6cd3bd0c) | 0.89 |
| 2 | pulse, schedule, pulses, duration, waveform, scheduling | 14 | 681 | 45% (Repo_2587cfac) | 0.53 |
| 15 | temp, tmp pip, pip build, linux x86_64, 0y2uped9 pyqrllib, build 0y2uped9 | 14 | 226 | 54% (Repo_61233351) | 0.59 |
| 18 | clifford, stabilizer, cliffords, qunit, clifford gate, cdr | 14 | 203 | 18% (Repo_2587cfac) | 0.81 |
| 22 | noise, noise model, noise models, model, noisy, noisemodel | 14 | 190 | 23% (Repo_d94af77b) | 0.78 |
| 48 | links, link, llms txt, broken, broken links, page | 14 | 100 | 14% (Repo_6cd3bd0c) | 0.92 |
| 60 | wheels, wheel, cibuildwheel, arm64, runners, ppc64le | 14 | 89 | 10% (Repo_48f701e4) | 0.92 |
| 10 | qasm, cx cx, cx, exporter, qr, 11 cx | 13 | 263 | 49% (Repo_2587cfac) | 0.61 |
| 13 | tensor, torch, pyhd3eb1b0_0, dmrg, tensors, pytorch | 13 | 241 | 36% (Repo_3d565e3d) | 0.65 |
| 23 | matplotlib, plot, plotting, py35_0, histogram, pyqtgraph | 13 | 189 | 34% (Repo_2587cfac) | 0.73 |
| 38 | qualtran bloqs, qualtran, bloqs, bloqs qsp, qsp, routecqc | 13 | 109 | 14% (Repo_6cd3bd0c) | 0.89 |
| 41 | ic, support python, files x86, ic program, thomas appdata, program files | 13 | 106 | 8% (Repo_e33a75f9) | 0.94 |
| 21 | unitary, unitary matrix, qsd, decomposition, matrix, unitaries | 12 | 191 | 34% (Repo_2587cfac) | 0.73 |
| 28 | statevector, qcfinal, probability, near clifford, mid circuit, probabilities | 12 | 142 | 30% (Repo_2587cfac) | 0.74 |
| 4 | coupling, coupling map, layout, swap, transpile, transpiler | 11 | 440 | 81% (Repo_2587cfac) | 0.31 |
| 27 | memory, qrisp tests, mb, mb qrisp, ram, 01343 | 11 | 145 | 34% (Repo_d94af77b) | 0.73 |
| 37 | gflow, graph, flow, graphs, pauli flow, graphviz | 11 | 110 | 33% (Repo_b259a373) | 0.79 |
| 63 | jupyter, notebooks, jupyter notebooks, notebook, crumble, jupyter notebook | 11 | 87 | 16% (Repo_2587cfac) | 0.87 |
| 6 | gradient, qnode, gradients, hessian, jacobian, parameter shift | 10 | 416 | 56% (Repo_3d565e3d) | 0.52 |
| 26 | job, jobs, ibmq, status, coupling_map version, attribute spec | 10 | 153 | 40% (Repo_2587cfac) | 0.73 |
| 7 | pyquil, qvm, quil, quilc, forest, pyquil api | 9 | 406 | 79% (Repo_16a98aa8) | 0.33 |

# Topic Model Visualization

[Interactive Topic Visualization](../data/analysis/topic_visualization.html)

# Threats to Validity

## Internal Validity

1. **Keyword-Based Pattern Detection**: Patterns identified via keyword matching may produce false positives (keyword mentioned in unrelated context) or false negatives (concept discussed without exact keyword). Manual validation of a sample is recommended.

2. **Issue Classification Heuristics**: Issue typing (bug/feature/question) relies on labels and text heuristics, which may misclassify issues, especially in repositories with inconsistent labeling practices.

3. **No Event History**: The dataset has no event timeline, so reopen rate and label churn are not reported; closed issues are broken down by `state_reason` instead.

4. **Label Churn**: True label churn requires event data; current implementation returns 0 as placeholder.

## External Validity

1. **Repository Selection Bias**: Analysis limited to repositories matching quantum keywords and minimum star thresholds; may miss early-stage or private quantum projects.

2. **Language Bias**: GitHub issues predominantly in English; non-English discussions not captured.

3. **Temporal Scope**: Snapshot analysis; maintainability patterns may evolve as quantum frameworks mature.

4. **Framework Coverage**: Keyword list may not capture all quantum frameworks (e.g., newer ones like CUDA-Q, Qadence).

## Construct Validity

1. **Maintainability Operationalization**: Metrics chosen (resolution time, resolution outcomes, Gini) are proxies; true maintainability includes cognitive load, onboarding time, and change failure rate not measured here.

2. **Topic Model Stability**: BERTopic results vary with random seeds and hyperparameters; results should be validated across multiple runs.

# Conclusions

This analysis of 35340 GitHub issues across 105 quantum software repositories reveals that hybrid quantum-classical systems exhibit distinct maintainability challenges requiring specialized engineering practices.

## Key Contributions

1. **Quantum Pattern Taxonomy**: Eight categories of quantum-specific issues identified, providing a vocabulary for practitioners and researchers.

2. **Quantitative Baselines**: First systematic measurement of resolution times, resolution outcomes, and contributor concentration in quantum repositories.

3. **Methodological Framework**: Reproducible pipeline combining BERTopic topic modeling with domain-specific pattern extraction.

## Recommendations

### For Quantum Software Engineers
- Implement hardware health monitoring in CI pipelines
- Design algorithms with simulator-hardware gap in mind
- Pin quantum framework dependencies; test upgrades in isolation
- Invest in reproducibility infrastructure (seed management, environment capture)

### For Framework Maintainers
- Improve error messages for transpilation and gradient failures
- Provide migration guides for breaking changes
- Stabilize core APIs; quantum ecosystem suffers from rapid churn

### For Researchers
- Validate pattern taxonomy with practitioner surveys
- Extend analysis to pull requests and commit data
- Investigate correlation between quantum patterns and production incidents
- Develop quantum-specific maintainability metrics (e.g., calibration-aware MTTR)

## Future Work

- Longitudinal analysis tracking pattern evolution across framework versions
- Integration with GitHub Actions workflow data for CI/CD failure patterns
- Practitioner interviews to validate and enrich pattern descriptions
- Extension to quantum-specific package ecosystems (PyPI, conda-forge)

# References

1. Grootendorst, M. (2022). BERTopic: Neural topic modeling with a class-based TF-IDF procedure. *arXiv preprint arXiv:2203.05794*.
2. McKinney, W. (2010). Data Structures for Statistical Computing in Python. *Proceedings of the 9th Python in Science Conference*.
3. Pedregosa, F. et al. (2011). Scikit-learn: Machine Learning in Python. *Journal of Machine Learning Research*.
