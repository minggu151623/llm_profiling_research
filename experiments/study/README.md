# Reproduce the eight-library study

The preregistered experiment holds out entire repositories for testing and treats two input mixtures as separate workloads. The public project roster, bytecode selectors, seed, model revision and fold order are frozen in Git. [Protocol](protocol.md) · [Fold assignments](config.json) · [JAR versions and workload definitions](../configs/corpus.json)

## 1. Reproduce the Java labels

Run with Eclipse Temurin 25.0.5.1+2, Maven 3.9.11 and Python 3.12.13. Point JAVA_HOME at this JDK and put its bin directory and Maven on PATH. Each destination below is a new directory. The runner verifies original JAR hashes, compares each selected conditional against javap, and compares original/instrumented output digests for all 16 project–workload pairs.

```sh
python scripts/corpus.py /tmp/jvm-reference/corpus
```

Original JARs are downloaded on demand from the recorded Maven Central URLs. The committed corpus consists of branch-level metadata, bounded instruction windows and labels. The reference class is the upstream JAR bytecode. Running with JDK 25 does not change its original class-file version. [Provenance](corpus/manifest.json)

## 2. Reproduce the frozen model outputs

Use a separate virtual environment for inference. CPU runs use FP32 with four threads and batches of eight. For a label-free rerun, only static.jsonl and context.jsonl are needed. To reproduce a study from an existing inference artifact, skip to step 3. [Model card, digests and readout](../../ml/slm/README.md)

```sh
python3.12 -m venv /tmp/branch-slm-env
/tmp/branch-slm-env/bin/pip install torch==2.10.0 --index-url https://download.pytorch.org/whl/cpu
/tmp/branch-slm-env/bin/pip install -r ml/slm/requirements.txt
/tmp/branch-slm-env/bin/python ml/slm/predict.py /tmp/jvm-reference/corpus /tmp/jvm-reference/slm --device cpu --threads 4 --batch-size 8
```

## 3. Fit and evaluate

The evaluator checks IDs across files, joins the two workloads only after static inputs have been constructed, and saves fold selections, predictions including unobserved sites, calibration and uncertainty tables. The project bootstrap is conditional on the eight fitted test folds. The number of distinct repositories and the artificial workload mixtures limit the interpretation of those intervals.

```sh
python3.12 -m venv /tmp/branch-eval-env
/tmp/branch-eval-env/bin/pip install -r ml/requirements.txt
/tmp/branch-eval-env/bin/python ml/evaluate.py /tmp/jvm-reference/corpus /tmp/jvm-reference/slm /tmp/jvm-reference/evaluation
/tmp/branch-eval-env/bin/python ml/figures.py /tmp/jvm-reference/evaluation /tmp/jvm-reference/project-results.png
```

The output directory must be new for each run. Runtime metadata is machine-specific. Use per-site ID, workload counts, per-project errors, and paired deltas to compare reruns.
