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

## 4. Exploratory supplements

These analyses were specified after the primary results and are labelled exploratory in the manuscript. The first and third read only the saved predictions. The second refits the registered folds after subtracting each fold's training-mean SLM state. The third pools held-out sites into an RMSE, the statistic that Graal IR static-profiling work reports. [Supplementary tables](supplement/)

```sh
/tmp/branch-eval-env/bin/python ml/sensitivity.py experiments/study/evaluation/predictions.csv /tmp/jvm-reference/supplement
/tmp/branch-eval-env/bin/python ml/centered.py experiments/study/corpus experiments/study/slm /tmp/jvm-reference/supplement
/tmp/branch-eval-env/bin/python ml/rmse.py experiments/study/evaluation/predictions.csv /tmp/jvm-reference/supplement
```

The exploratory 1.5B rerun keeps the registered prompts, readouts and folds and swaps only the checkpoint. The workflow `scale.yml` runs it on Linux; [the committed outputs](supplement/qwen-1.5b/) come from Actions run 44862417201. Inference downloads about 3 GB of pinned weights.

```sh
python ml/slm/scale.py experiments/study/corpus /tmp/slm-1.5b --device cpu --threads 4 --batch-size 8
cd ml && /tmp/branch-eval-env/bin/python scale.py ../experiments/study/corpus /tmp/slm-1.5b ../experiments/study/evaluation /tmp/jvm-reference/supplement
```

On macOS, the xgboost wheel loads `libomp.dylib` at import. If Homebrew's libomp is absent, point `DYLD_FALLBACK_LIBRARY_PATH` at a directory containing only that library.
