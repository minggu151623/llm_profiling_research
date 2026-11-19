# Research Brief for Codex — Semantic-Aware Static Branch Prediction on JVM

> **Trạng thái:** Working research brief, 19/11/2026  
> **Nhóm:** 02 người — 01 AI/ML researcher và 01 Java/JVM engineer; Codex là công cụ hỗ trợ nghiên cứu và kỹ thuật, **không phải tác giả**.  
> **Mục tiêu công bố:** Một empirical **arXiv preprint**, trước khi cân nhắc workshop/conference.  
> **Nguồn gốc:** Tóm tắt các quyết định trong cuộc thảo luận của nhóm và đề cương ban đầu *Zero-Run Profile Synthesis*. **Đây không phải specification đã kiểm chứng hoặc kết quả nghiên cứu.**

## 0. Hướng dẫn quan trọng dành cho Codex

1. **Khảo sát repo trước khi tạo/sửa bất cứ thứ gì**: đọc README, cấu trúc, build files, tests, git status và các quyết định có sẵn. Không ghi đè hoặc xóa công việc của nhóm.
2. Đọc tài liệu này làm **định hướng**, không coi giả thuyết là sự thật. Nếu một tuyên bố về paper, phiên bản phần mềm hoặc benchmark chưa được kiểm chứng, đánh dấu `UNVERIFIED` và dẫn đến nguồn gốc trực tiếp.
3. **Bắt đầu bằng literature + thiết kế dataset + minimal vertical slice**, chưa tự khởi động fine-tuning lớn, cài những dependency không cần thiết, hay tích hợp Native Image.
4. Mọi thí nghiệm phải có **config, seed, dataset version, lệnh chạy, logs và kết quả**. Không tự tạo số liệu, trích dẫn, DOI hoặc tuyên bố SOTA.
5. Phân biệt **thông tin static được cấp cho model** với **runtime labels/ground truth**. Không đưa counts, workload-specific runtime profile hoặc đặc trưng dẫn xuất từ chúng vào feature của bài kiểm tra zero-run.
6. Sau khi audit repo, đưa ra kế hoạch nhỏ có acceptance criteria và ghi lại những lựa chọn phải hỏi nhóm trước khi thay đổi phạm vi. Chỉ triển khai những việc tương thích với repo hiện có.

## 1. Mục tiêu khoa học

### 1.1. Tên paper làm việc

**Can Small Language Models Predict Runtime Branch Behavior from Static Java Bytecode?**

Tên hướng nghiên cứu thay thế: **Semantic-Aware Static Branch Probability Prediction Using Small Language Models**.

### 1.2. Câu hỏi trung tâm

> Can SLMs leverage semantic information available in Java bytecode to improve **static branch-probability estimation** over strong structural and lexical baselines, without running the **target application** for profiling at inference time?

Giả thuyết làm việc: tên class/method/field, signatures, constants và ngữ cảnh code có thể giúp một SLM suy luận một số loại nhánh (ví dụ guard/validation/error handling) tốt hơn một mô hình chỉ dựa vào CFG. **Chưa có bằng chứng kết luận rằng SLM vượt GraalSP/GraalNN hoặc embeddings.**

### 1.3. Giới hạn mang tính nguyên lý

Xác suất một nhánh phụ thuộc **code lẫn workload**:

\[
P(b\mid C,\Sigma,W),
\]

với `C` = code/CFG, `Σ` = static semantic metadata, `W` = phân phối input/runtime workload. Mô hình zero-run không quan sát được `W` của workload chưa biết, nên chỉ ước lượng được **prior qua các workload** hoặc xác suất theo một protocol workload xác định. **Không thể suy ra duy nhất một runtime probability từ bytecode khi workload không được cho.**

*Zero-run* ở đây **không có nghĩa là không bao giờ chạy Java**: phải chạy ứng dụng trong giai đoạn tạo nhãn cho dataset và evaluation. Nó nghĩa là ở thời điểm dự đoán cho ứng dụng test chưa thấy, không dùng các profiling run của chính ứng dụng đó làm đầu vào.

### 1.4. Đóng góp khả dĩ — chỉ được tuyên bố sau thực nghiệm

- Bộ dữ liệu/protocol branch-level tái lập được với nhiều workloads, static branch IDs ánh xạ sang measured execution counts.
- Phân tích định lượng tác động của identifier/semantic information so với CFG và lexical baselines.
- Đánh giá cross-project generalization, identifier masking/renaming và workload shift.
- **Tùy chọn** sau khi có kết quả: selective/calibrated prediction chỉ dùng SLM ở các nhánh nó thực sự mang lại lợi ích.
- Kết quả âm tính cũng có thể thành empirical preprint nếu baseline nghiêm túc, dataset tốt và phân tích sâu.

## 2. Phạm vi paper đầu tiên và những gì chưa làm

**Làm:** local branch-level probability estimation; bytecode parsing; branch instrumentation; runtime ground-truth counts; strong baselines; SLM semantic ablations; statistical evaluation; literature/novelty matrix; reproducibility package.

**Chưa làm:** full zero-run JVM profile generator; call-graph-wide frequency propagation; receiver type profiling/devirtualization; GraalVM `.iprof` synthesis; sửa HotSpot/C2/Graal; khẳng định tăng throughput/startup; hệ multi-agent quy mô lớn; fine-tuning 1.5B–3B mặc định.

Tích hợp Oracle GraalVM/PGO là **future work** hoặc giai đoạn 2, không phải điều kiện cần để ra empirical preprint đầu tiên.

## 3. Tech stack được nhóm lựa chọn

| Mảng | Lựa chọn ban đầu | Cần xác minh trước khi pin |
|---|---|---|
| Java / JDK | **Java 25 LTS, Eclipse Temurin 25 (HotSpot)** | Ghi vendor, build, patch, OS, arch và output `java -version` |
| Java class files | target `--release 25` nếu phù hợp | Java 25 class major version 69 |
| Bytecode parser/instrumenter | **OW2 ASM 9.11.1** (quyết định ban đầu của nhóm) | Kiểm tra artifact trên Maven Central, API, phiên bản có sẵn và tính tương thích |
| Build & test | Maven, JUnit 5 | Pin versions; tests bắt buộc |
| ML | Python, PyTorch, scikit-learn, XGBoost | Pin env/lock dependencies |
| SLM | Code-capable SLM nhỏ, chạy zero/few-shot trước | Chọn sau khi có bộ dữ liệu nhỏ; ghi model revision/license |
| Datasets ứng viên | DaCapo, Renaissance, ứng dụng Java có workload kiểm soát | Kiểm tra **từng benchmark** chạy được trên Java 25; không mặc định tương thích |
| Execution environment | Linux cố định cho final results | Cố định CPU/JDK/VM flags; development có thể đa OS |
| Future compiler experiments | Oracle GraalVM 25 | Chỉ triển khai sau khi có baseline đáng tin |

Một distro Java **không** đồng nghĩa với Linux distro. Tránh nhầm Eclipse Temurin/Oracle GraalVM với Ubuntu/Oracle Linux.

## 4. Phân công hai người

### AI/ML researcher — owner về research question và paper

- Literature review, novelty map, research questions/hypotheses, experimental design.
- Chuẩn hóa representation và train/test split; thiết lập baseline thống kê/ML.
- SLM prompting/feature extraction, embeddings, semantic ablations, nếu cần mới fine-tuning.
- Evaluation, calibration, uncertainty, robustness, significance, figures/tables.
- Viết các phần Introduction, Related Work, Method, Results, Discussion và limitations.

**Nền tảng cần nắm:** code representation/semantics; CFG căn bản; probabilistic prediction (BCE/Brier/MAE); ML evaluation; data leakage; grouped splits; SLM representations; ablation; uncertainty/calibration; workload shift; reproducibility.

### Java/JVM engineer — owner về data provenance và profiling pipeline

- Tạo tooling đọc `.class`/`.jar` từ **Temurin 25** bằng ASM; xây CFG, branch identifiers, context, metadata.
- Instrument conditional branches để đo **taken** và **fall-through** counts; liên kết về **bytecode gốc**.
- Build test programs và benchmark runners, tạo nhiều workloads, kiểm tra số đếm đúng.
- Xuất dữ liệu có schema rõ ràng; kiểm tra instrumentation không thay đổi behavior và không làm mất nhánh.
- Viết JUnit tests, tool/docs, script tái lập; hỗ trợ phần JVM methodology trong paper.

**Nền tảng cần nắm:** JVM classfile/constant pool/instructions/operand stack; `javap -c -v`; ASM (`ClassReader`, tree API, visitors); basic blocks/CFG; `ifeq`, `if_icmp*`, `goto`, switch, loop, exception edges; instrumentation; class loading/Java agent ở mức cần thiết; Maven/JUnit; profiling/JIT/AOT căn bản.

### Cả hai phải đồng sở hữu

Dataset schema, ý nghĩa `taken` vs `fall-through`, lựa chọn workload, test cases, validation, split protocol, benchmark validity, interpretation và tiêu chuẩn paper claim.

Quyền tác giả/thứ tự tác giả dựa trên **đóng góp thực tế và thỏa thuận của hai người**, không mặc định từ ai đề xuất ý tưởng trước.

## 5. Data contract tối thiểu

**Đơn vị dự đoán:** một *conditional bytecode branch* có hai cạnh `taken` và `fall-through`, không đồng nhất với một `if` trong source Java (short-circuit có thể tạo nhiều bytecode branches). Switch là trường hợp nhiều cạnh; tách thành nhiệm vụ mở rộng hoặc xử lý riêng theo schema.

Ví dụ schema **minh họa** (không mặc định ASM cung cấp hết mọi trường):

```json
{
  "project_id": "example-app",
  "artifact_sha256": "...",
  "jdk_vendor": "Eclipse Adoptium",
  "jdk_version": "25.x",
  "class_name": "example/PaymentService",
  "method_name": "process",
  "method_descriptor": "(Lexample/Payment;)I",
  "original_bci": 42,
  "branch_opcode": "IFEQ",
  "bytecode_context": "...",
  "cfg_features": {},
  "symbolic_context": ["Payment", "isExpired"],
  "workload_profiles": [
    {"workload_id": "normal", "taken_count": 50, "fallthrough_count": 9950},
    {"workload_id": "expired-heavy", "taken_count": 7000, "fallthrough_count": 3000}
  ]
}
```

**Lưu ý kỹ thuật:**

- `original_bci` phải gắn với bytecode **trước instrumentation**; cần thiết kế cách giữ/khôi phục offset ổn định và kiểm tra mapping. ASM không bảo đảm tiện ích lấy BCI gốc bằng mọi API.
- `taken` nghĩa là jump condition **của bytecode** đúng, có thể ngược chiều với điều kiện ở source Java.
- `p_true = taken / (taken + fallthrough)` **chỉ khi mẫu số > 0**. Branch chưa được thực thi là *unobserved*, không tự gán 0%, 50% hay 100%.
- Ghi counts tách theo workload; cân nhắc concurrency/thread safety, overflow, exceptions, warmup, input determinism và instrumentation overhead.
- Tên local variables có thể không tồn tại trong bytecode; đừng giả định reconstruct source chính xác từ `.class`.
- Những static features được công bố phải thực sự có sẵn tại inference từ `.class`/`.jar`; generated semantic descriptions là **model outputs**, không phải bytecode facts.
- Định nghĩa rõ schema/version, invariants và unit tests trước khi mở rộng số lượng benchmark.

## 6. Thiết kế thí nghiệm

### Research Questions (bản nháp)

- **RQ1:** SLM có giảm sai số branch probability so với CFG heuristics và structural ML không?
- **RQ2:** Static identifiers và semantic features đóng góp bao nhiêu so với lexical embeddings đơn giản?
- **RQ3:** Model tổng quát hóa đến các **project unseen** như thế nào?
- **RQ4:** Sai số thay đổi ra sao khi **cùng code** chạy với workloads khác nhau?
- **RQ5 (tùy chọn):** Khi nào SLM đủ đáng tin để cải thiện baseline bằng selective prediction?

### So sánh bắt buộc

1. CFG/branch heuristics (triển khai có nguồn và giải thích, **không gán sai Ball–Larus thành 50/50**).
2. Structural features + logistic regression hoặc XGBoost.
3. Structural + method/class identifiers hoặc lexical embeddings + regression.
4. SLM zero/few-shot trên một representation xác định.
5. SLM embeddings/structured semantic extraction + regression.
6. Ablation: xóa/mask/rename identifiers, đổi cách biểu diễn, stratify theo branch type.
7. Nếu có điều kiện và tương thích: so với GraalSP/GraalNN. **Không tự nhận SOTA** nếu chưa có so sánh tương đương.

### Quy tắc đánh giá

- **Group split theo project/repository**, deduplicate library/method gần giống nhau; tránh chia ngẫu nhiên branch ở cùng project cho train/test rồi gọi là cross-project generalization.
- Tách bài kiểm tra `unseen-project` và `seen-project/new-workload`; đây là hai thiết lập khác nhau.
- Không tuning trên test set; xác định protocol chọn hyperparameter bằng validation.
- Báo MAE, Brier score, calibration/reliability, performance theo nhóm nhánh; có thể thêm execution-weighted metrics và bootstrap confidence intervals **theo nhóm project/workload**.
- Không làm mất nhánh khó bằng filtering tùy tiện; báo coverage, tỷ lệ unobserved, failure modes, inference time/cost.
- Cần phân biệt *prediction error* với cải thiện compiler performance. Paper giai đoạn 1 không claim runtime speedup.

### Điều kiện go/no-go

Sau khi có extractor, nhãn kiểm chứng và strong baselines: nếu SLM không hơn embedding + structural baseline, chuyển sang **empirical/negative-results paper** về giới hạn semantic priors và workload shift thay vì ép kết quả có lợi cho giả thuyết.

## 7. Literature review — nhóm paper và điều cần xác minh

**Đây là danh mục xuất phát từ trao đổi, KHÔNG phải bibliography đã kiểm chứng đầy đủ. Codex phải đọc paper gốc, lấy DOI/URL chính thức, trích chính xác phần Method/Evaluation, ghi version/JDK/distro nếu paper thật sự công bố.**

### A. Static branch profiling / compiler

- **GraalSP** — ML-based static profiling trên GraalVM; kiểm tra paper chính thức, loại profile, feature set, ground-truth và baseline.
- **GraalNN: Context-Sensitive Static Profiling with Graph Neural Networks** (CGO 2025) — GNN với CFG/calling context; đối chứng rất gần.
- **Improving ML-Based Static Profiling Using Method Names** (2025) — semantic identifiers/embeddings; xác nhận chính xác prediction target (method hotness hay branch).
- **GraalMHC** (CC 2026, theo thảo luận trước) — method hotness; kiểm tra artifact và bản công bố.
- **The Promise of Static Profiling: Exploring the Limits** (MoreVMs 2026, theo thảo luận trước) — phạm vi các loại profile; kiểm tra nguồn gốc và findings.
- Classical branch prediction heuristics: **Ball–Larus**, **Wu–Larus** và related work; đọc bản gốc trước khi mô tả giả định của phương pháp.

### B. LLM/program execution/semantics

- **Phaedrus** (OOPSLA 2026, theo thảo luận trước): xem prediction target, input, việc dùng LLM và mức tương đồng thực sự với nhiệm vụ branch-level.
- **T-REX** (OOPSLA 2026, theo thảo luận trước): xem teacher-student, execution semantics/distillation; có thể gợi ý modeling methodology nhưng không coi là nghiên cứu branch probabilities.
- Các nghiên cứu về code understanding, execution prediction, identifier embeddings, code representations và OOD evaluation.

### C. AI-assisted research workflows — *không phải trực tiếp related work của branch profiling*

- Anthropic, **Formalizing Fermat's Last Theorem** — ví dụ dependency DAG/tri thức được lưu có cấu trúc, proof/claim tracking.
- OpenAI, bài **Navier–Stokes** (2026, theo thảo luận) — tham khảo việc tổ chức nhiều hướng nghiên cứu và tổng hợp bằng AI/Codex.

**Nguyên tắc:** DAG quản lý nghiên cứu ≠ CFG của Java ≠ GNN là mô hình ML. Không trình bày DAG phối hợp công việc như đóng góp mới trong branch prediction.

### Deliverables của literature

1. `research/literature/papers.bib` — chỉ ghi citation đã xác minh, không tự bịa metadata.
2. `research/literature/evidence_matrix.csv` — gợi ý cột: `paper_id, year, venue, url, doi, problem, prediction_target, input_representation, learning_method, benchmarks, jdk_version, jdk_distribution, metrics, artifact, limitations, relevant_claim, evidence_page_section, verification_status`.
3. `research/literature/novelty_map.md` — mỗi claim của đề tài được đối chiếu với prior work, bằng chứng và gap còn mở.
4. `research/literature/reading_notes/` — 1 file/paper, tách **author claims** khỏi **our interpretation** và **unverified**.

## 8. Research Dependency Graph và Codex workflow

Mượn nguyên lý DAG quản lý dependencies từ các dự án formalization, nhưng ở quy mô vừa đủ:

```text
RQ0: SLM semantic signal cho branch probability?
├── LIT: kiểm chứng closest related work
├── DATA: static extractor + runtime counts + schema validation
├── BASE: structural & lexical baselines
├── E1: semantic/identifier ablations
├── E2: cross-project generalization
└── E3: workload shift
       └── CLAIMS: kết luận được hỗ trợ bởi kết quả
```

Lưu trong `research/dependency_graph.yaml` (hoặc file tương đương nếu repo đã có convention). Mỗi nút nên có: `id`, `type`, `owner`, `dependencies`, `status`, `acceptance_criteria`, `evidence_paths`.

**Vai trò hỗ trợ Codex**: literature scout (tìm nguồn), critical reviewer (tìm prior work bác bỏ novelty), research engineer (triển khai tests/ML), reproducibility auditor (soát seed/split/log), writing assistant (bản thảo). Những vai trò này không bắt buộc là 5 agents chạy song song.

**Human review bắt buộc** khi: chọn RQ, chốt novelty, thay đổi nhãn/schema, chạy benchmark lớn, đánh giá claims, quyết định authorship, đưa bản thảo lên arXiv.

## 9. Repo layout gợi ý (chỉ tạo nếu chưa có cấu trúc tương đương)

```text
slm-branch-profiling/
├── README.md
├── research/
│   ├── questions.md
│   ├── decisions.md
│   ├── dependency_graph.yaml
│   └── literature/
│       ├── papers.bib
│       ├── evidence_matrix.csv
│       ├── novelty_map.md
│       └── reading_notes/
├── java/
│   ├── extractor/
│   ├── instrumentation/
│   └── tests/
├── data/
│   ├── schema/
│   └── samples/                # dữ liệu mẫu hợp pháp, nhỏ
├── ml/
│   ├── baselines/
│   ├── slm/
│   └── evaluation/
├── experiments/
│   ├── configs/
│   └── results/                # metadata; không commit dataset khổng lồ
└── paper/
```

Để Codex làm việc an toàn: tránh chứa credentials, dữ liệu người dùng nhạy cảm hoặc bản copy full-text papers trái quyền trong repo; kiểm tra license của benchmark/model; document mọi nguồn dữ liệu và quy trình AI-assisted writing theo yêu cầu venue.

## 10. Backlog đề xuất cho Codex (ưu tiên theo thứ tự)

### P0 — Repo audit & scientific foundations

- [ ] Báo cáo repo hiện có: build, directory structure, versions, tests, modules đã triển khai, blockers.
- [ ] Tạo `research/questions.md` với RQ1–RQ4 và phạm vi rõ ràng.
- [ ] Tạo evidence matrix + reading notes cho **3 công trình quan trọng nhất**: GraalSP, GraalNN, Method Names. Xác minh title, DOI/URL, method, evaluation.
- [ ] Viết `research/literature/novelty_map.md`: *đã có*, *chưa chắc*, *câu hỏi cần thử nghiệm*.
- [ ] Đề xuất schema JSON/JSONL v0 + quy tắc branch IDs, labeling, validation; cả hai nghiên cứu viên duyệt.

**Done khi:** Có tài liệu minh bạch, nguồn gốc xác minh, kế hoạch minimal vertical slice; chưa cần model.

### P1 — Minimal end-to-end data pipeline

- [ ] Ứng dụng Java nhỏ có `if/else`, `&&/||`, loop, switch, exception, tests.
- [ ] ASM extractor tạo branch records cho conditional branches; xử lý switch riêng hoặc đánh dấu unsupported có chủ đích.
- [ ] Instrument branch counts có tests kiểm tra `taken/fallthrough`, preservation of behavior và mapping đến original bytecode.
- [ ] Chạy ≥ 2 workload cố ý khác phân phối; xuất JSON/JSONL có provenance.
- [ ] Python validator/loader kiểm tra schema, counts không âm, null khi unobserved, unique IDs.

**Done khi:** Một nhánh có thể lần từ `.class` → static record → runtime counts → ML-ready example và xác minh bằng tay.

### P2 — ML baselines

- [ ] Grouped train/validation/test split theo project (cần ≥ vài project khác nhau để meaningful).
- [ ] Structural heuristic + XGBoost, identifier embeddings + regression.
- [ ] Prediction CLI và evaluation scripts, seed/config/reproducibility.
- [ ] Zero-shot SLM + masked identifiers; report per-branch-type & workload-shift.

**Done khi:** Có bảng so sánh với uncertainty intervals và không có label leakage.

### P3 — Paper-ready empirical analysis

- [ ] Tăng số benchmark/workloads, kiểm tra JDK 25 compatibility.
- [ ] Semantic ablations, OOD splits, robustness, cost/latency analysis.
- [ ] Phân tích cả cases SLM đúng và cases sai, threats to validity.
- [ ] Draft paper (LaTeX/Markdown tùy repo), only substantiated claims.

**Done khi:** Người ngoài có thể chạy lại các bước và tìm được artifact tương ứng với từng figure/table.

## 11. Rủi ro cần theo dõi

1. **Workload identifiability:** code giống nhau, workload khác nhau → xác suất không duy nhất.
2. **Semantic hallucination:** SLM suy diễn tên `isExpired` thành tỷ lệ hiếm mà không có data.
3. **Measurement errors:** bytecode jump direction, ASM BCI mapping, short-circuit, exception/switch, concurrency.
4. **Dataset leakage:** cùng project/library hoặc derivatives xuất hiện train và test.
5. **Weak novelty:** GraalNN/GraalSP/identifier-semantic works đã xử lý các vấn đề gần tương tự.
6. **Benchmark compatibility:** Java 25 có thể không chạy được tất cả DaCapo/Renaissance versions.
7. **Cost vs value:** SLM tốn compute so với simpler lexical/structural predictors.
8. **Citation integrity:** không được dẫn lời từ AI-generated summary thay cho paper gốc.

## 12. Definition of Success

Preprint giai đoạn 1 thành công nếu trả lời được RQ1–RQ4 bằng dữ liệu có thể kiểm tra, baselines phù hợp, ablations có ý nghĩa và diễn giải trung thực. **Không bắt buộc SLM chiến thắng mọi baseline**, cũng không bắt buộc cho ra GraalVM PGO speedup. Bản thảo phải thể hiện rõ khác biệt với prior work, data/split protocol, limitations và availability của artifacts.

---

### Lời nhắc khởi động cho Codex

> Hãy đọc file research brief này và audit repo hiện tại trước. Không bắt đầu bằng training hoặc tích hợp GraalVM. Hãy (1) trình bày những gì repo đã có, (2) liệt kê các gap so với brief, (3) xác minh 3 công trình closest related work bằng nguồn gốc, (4) đề xuất schema v0 và minimal vertical-slice P1 kèm tests, (5) gửi lại kế hoạch file-level trước những thay đổi lớn. Phân biệt facts, assumptions, hypotheses và unverified claims; không tạo kết quả thực nghiệm hoặc citation không có nguồn.
