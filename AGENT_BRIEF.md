# Brief cho agent tiếp quản dự án

Cập nhật ngày 23/11/2026 sau khi đối chiếu bản thảo với các bảng đã công bố. Nghiên cứu trên tám thư viện đã có bản thảo và PDF. Mục 9 ghi phần cần chủ dự án và cộng sự hoàn tất.

Đọc thêm khi cần chi tiết: [HANDOFF.md](HANDOFF.md) (nhật ký bàn giao theo ngày), [research brief gốc](CODEX_RESEARCH_BRIEF_SLM_JVM_BRANCH_PROFILING.md), [protocol đăng ký trước](experiments/study/protocol.md), [bản thảo](paper/manuscript.md).

## 1. Mục tiêu nghiên cứu

**Câu hỏi trung tâm:** một code model nhỏ (SLM), đông cứng và không fine-tune, có ước lượng được tỉ lệ một lệnh nhảy có điều kiện trong bytecode Java đi tới đích nhảy hay không, chỉ từ thông tin tĩnh? Và nó có tốt hơn các baseline cấu trúc và lexical mạnh hay không?

**Đại lượng cần ước lượng:** với site *i* và workload *w*, p = t / (t + f). Ở đây t là số lần nhảy tới đích, f là số lần đi thẳng. Nếu cùng một site có hai xác suất đo được khác nhau, một giá trị dự đoán cố định sẽ có sai số trên ít nhất một workload.

**"Zero-run":** vẫn phải chạy Java để tạo nhãn. "Zero-run" chỉ có nghĩa là khi dự đoán cho thư viện kiểm tra, mô hình không nhận count, profile hay workload ID nào của chính thư viện đó.

**Bốn câu hỏi nghiên cứu:**

| RQ | Nội dung |
| --- | --- |
| RQ1 | SLM (hỏi trực tiếp, hoặc dùng làm bộ trích đặc trưng) so với các predictor cấu trúc |
| RQ2 | Che tên định danh thì thay đổi gì; biểu diễn của SLM có thêm giá trị gì so với đặc trưng lexical |
| RQ3 | Chuyển giao sang thư viện chưa thấy khi huấn luyện |
| RQ4 | Nhãn thay đổi bao nhiêu khi đổi tỉ lệ input trên cùng một đoạn code |

**Mục tiêu công bố:** một preprint thực nghiệm trên arXiv (cs.PL, đăng chéo cs.SE và cs.LG). Kết quả âm tính vẫn được công bố nếu baseline nghiêm túc.

**Ngoài phạm vi bài đầu tiên:** sinh profile JVM đầy đủ, lan truyền tần suất qua call graph, tích hợp GraalVM PGO hoặc `.iprof`, sửa HotSpot/C2/Graal, đo throughput, fine-tune model.

## 2. Nhóm và vai trò

- **Chủ dự án:** Tran Vu Bao Minh, tác giả thứ nhất.
- **Cộng sự Java:** tác giả thứ hai, phụ trách kiểm thử độc lập phần đo Java. Chưa có tên và đơn vị công tác.
- **AI agent** (OpenAI Codex, sau đó Anthropic Claude Code): làm thiết kế, code, phân tích và viết bản thảo theo ủy quyền của chủ dự án. Agent không phải tác giả. Bản thảo có câu khai báo việc dùng AI.

## 3. Thiết kế nghiên cứu

**Đăng ký trước** ở commit `e6e775c`, trước khi thu nhãn: mô hình, fold, hai phép so sánh chính và chỉ số đánh giá. Mọi thứ thêm sau đó đều được ghi là exploratory.

**Corpus** ([corpus.json](experiments/configs/corpus.json), [corpus](experiments/study/corpus/)):
- 8 thư viện Maven: Commons Codec, Guava, JavaPoet, Joda-Time, jsoup, JTS, Maven Artifact, JSON-java.
- Mỗi thư viện lấy 1 class và một bộ method cố định.
- Tổng 193 site tĩnh, trong đó 138 site chạy tới ở cả hai workload. 55 site không chạy tới được giữ lại với nhãn null.

**Workload:** mỗi thư viện có hai họ input là A và B.
- Workload normal: mỗi khối 20 lần lặp có 17 input họ A và 3 input họ B.
- Workload shift: đảo ngược tỉ lệ này.
- Driver lặp 100 lần, seed 1516.

**Đo:**
- ASM 9.11.1 chèn hai đầu đo, taken và fall-through, cho mỗi lệnh nhảy có điều kiện.
- ID của mỗi site gồm SHA-256 file class gốc, chỉ số method và BCI gốc.
- Kiểm tra tính đúng: so hash đầu ra giữa class gốc và class đã chèn đầu đo, và đối chiếu từng lệnh với `javap`, trên cả 16 cặp class–workload.

**Mô hình** ([evaluate.py](ml/evaluate.py), [predict.py](ml/slm/predict.py)):

| Mô hình | Mô tả |
| --- | --- |
| uniform | Luôn đoán 0.5 |
| backward_taken | Đoán 1 nếu nhảy lùi, 0 nếu nhảy tiến. Trên corpus này mọi site đều nhảy tiến nên luật này luôn ra 0 |
| structural_ridge, structural_xgb | Đặc trưng opcode, hướng nhảy, khoảng cách nhảy, vị trí, cửa sổ ±5 lệnh |
| lexical_ridge | Đặc trưng cấu trúc cộng TF-IDF ký tự 2–4-gram của tên class, method, descriptor và lệnh |
| zero_full, zero_masked | Qwen2.5-Coder-0.5B-Instruct (revision `ea3f2471`) cho điểm 0–9; lấy kỳ vọng trên softmax của 10 token chữ số rồi chia 9 |
| embedding_full, embedding_masked | Vector ẩn cuối (896 chiều) ghép với đặc trưng cấu trúc, rồi qua ridge |

Dạng masked thay tên định danh và kiểu tham chiếu bằng placeholder, giữ nguyên opcode và offset.

**Đánh giá:**
- 8 fold, mỗi fold giữ lại một thư viện làm tập kiểm tra, thư viện kế tiếp làm validation, 6 thư viện còn lại để train.
- Loại site train trùng hash chuỗi opcode của method, hoặc có Jaccard trigram từ 0.9 trở lên, với tập validation hay test.
- Chỉ số chính là macro MAE: tính MAE trong từng thư viện, rồi lấy trung bình 8 thư viện.
- Khoảng tin cậy dùng project bootstrap 10.000 lần, seed 42.
- Còn có thêm setting seen-project: train trên nhãn normal của cả 8 thư viện, rồi chấm trên workload shift.

## 4. Kết quả chính

Lấy từ [metrics.csv](experiments/study/evaluation/metrics.csv). Macro MAE trên thư viện chưa thấy; thấp hơn là tốt hơn.

| Mô hình | Normal | Shift |
| --- | ---: | ---: |
| uniform 0.5 | 0.429 | 0.375 |
| structural XGBoost | 0.311 | 0.274 |
| lexical ridge | 0.325 | 0.299 |
| SLM zero-shot full | 0.424 | 0.375 |
| SLM embedding ridge full | 0.327 | 0.298 |

**Hai phép so sánh đăng ký trước** (hiệu số lấy SLM trừ lexical ridge, workload normal):
- Zero-shot: +0.099 (0.050 đến 0.152). Lexical ridge thắng ở cả 8 thư viện.
- Embedding: +0.002 (−0.022 đến 0.024). Chưa thấy ưu thế rõ ràng trên tám thư viện. Khoảng bootstrap có điều kiện trên các fold đã fit và protocol không đặt biên tương đương.

**Đặc điểm của hai readout trên corpus này**
- Điểm zero-shot gần như hằng số: nằm trong 0.339–0.489, Spearman với nhãn thật −0.04.
- Các vector ẩn gần như cùng hướng (cosine trung bình 0.996). Embedding ridge cho dự đoán gần trùng structural ridge, chênh lệch trung vị chỉ 0.003.

**RQ4:**
- 42/138 site đổi xác suất hơn 0.10 khi đảo workload.
- Với hai trace đã đo, macro MAE tối thiểu là 0.0439 nếu mỗi site chỉ nhận một dự đoán và hai workload cũng như các thư viện lần lượt được gán trọng số bằng nhau. Tần suất thực tế của các mẫu đầu vào trong từng nhóm cũng thay đổi.

**Phân tích exploratory** (trong [supplement](experiments/study/supplement/)):

| Phân tích | Kết quả |
| --- | --- |
| Che tên định danh | Cả 193 rating zero-shot tăng, trung bình 0.053. Macro MAE của mỗi readout trên normal thay đổi tối đa 0.003 |
| 119 site có ít nhất 20 lượt chạy trên normal | Chỉ chấm normal. Chênh MAE so với lexical ridge là −0.001 cho embedding và +0.107 cho zero-shot |
| Centering embedding | MAE 0.342, không tốt hơn lexical ridge |
| Persistence (chép nhãn normal của chính site) | 0.088 trên workload shift |
| RMSE gộp | XGBoost 0.381, hằng số 0.442. GraalSP báo 0.299 nhưng trên dữ liệu khác, không so trực tiếp được |
| Qwen2.5-Coder-1.5B (revision `2e1fd397`) | Kết luận giữ nguyên: zero-shot 0.435, embedding 0.326 |

## 5. Lịch sử thực hiện

| PR | Ngày | Nội dung |
| --- | --- | --- |
| [#1](https://github.com/minggu151623/llm_profiling_research/pull/1) | 19/11 | Research brief, khảo sát tài liệu, DAG, schema v0, công cụ đo Java 25 bằng ASM, pilot trên một fixture |
| [#2](https://github.com/minggu151623/llm_profiling_research/pull/2) | 19/11 | Đăng ký trước, corpus 8 thư viện, inference Qwen 0.5B, evaluator, các phân tích bổ sung, bản thảo Markdown, Figure 1, CI tái lập trên Linux |
| [#3](https://github.com/minggu151623/llm_profiling_research/pull/3) | 19/11 | Viết lại hướng dẫn kiểm thử Java bằng tiếng Anh, thêm 7 bước kiểm tra tay M1–M7 |
| [#4](https://github.com/minggu151623/llm_profiling_research/pull/4) | 19/11 | Bản LaTeX `paper/main.tex`, build bằng Tectonic |
| [#5](https://github.com/minggu151623/llm_profiling_research/pull/5) | 20/11 | Trích RMSE của GraalSP từ luận án, thêm RMSE gộp, `check_paper.py` chạy trong CI |
| [#6](https://github.com/minggu151623/llm_profiling_research/pull/6) | 20/11 | Trích dẫn phần mềm đã dùng, khai báo cả hai AI agent |
| [#7](https://github.com/minggu151623/llm_profiling_research/pull/7) | 20/11 | Build bằng pdfLaTeX + BibTeX trong CI, giống cách arXiv xử lý |
| [#8](https://github.com/minggu151623/llm_profiling_research/pull/8) | 20/11 | Tờ khai nộp arXiv `paper/ARXIV.md` |
| [#9](https://github.com/minggu151623/llm_profiling_research/pull/9) | 20/11 | Cập nhật DAG |
| [#10](https://github.com/minggu151623/llm_profiling_research/pull/10) | 20/11 | Ghi lại lần người duy trì tự chạy lại test Java: tất cả đều qua, nhưng không tính là kiểm thử độc lập |
| [#11](https://github.com/minggu151623/llm_profiling_research/pull/11) | 21/11 | Chạy lại với model 1.5B, thêm chỗ trống cho tên tác giả thứ hai, chọn giấy phép CC BY 4.0 |
| [#12](https://github.com/minggu151623/llm_profiling_research/pull/12) | 21/11 | Test cho các script bổ sung, thêm `scripts/java_report.py` |
| [#13](https://github.com/minggu151623/llm_profiling_research/pull/13) | 21/11 | Vẽ điểm rỗng của bản 1.5B lên Figure 1 |

Các lần chạy CI dùng làm tham chiếu:
- Corpus trên Linux: Actions [44496268635](https://github.com/minggu151623/llm_profiling_research/actions/runs/44496268635).
- Inference 1.5B: [44862417201](https://github.com/minggu151623/llm_profiling_research/actions/runs/44862417201). Chạy lại lần hai cho sai khác 0.0.
- Chấm điểm và Figure 1 hiện tại: [44865751986](https://github.com/minggu151623/llm_profiling_research/actions/runs/44865751986).
- PDF hiện hành nằm trong artifact `paper-pdflatex` của [lần build thành công trên main](https://github.com/minggu151623/llm_profiling_research/actions/workflows/paper.yml?query=branch%3Amain).

## 6. Bản đồ repo

| Đường dẫn | Nội dung |
| --- | --- |
| `java/` | Công cụ đo bằng ASM (`src/main/java/org/branchpilot/`), driver workload (`corpus/Workloads.java`), `TESTING.md`, `MANUAL_TESTING.md` |
| `scripts/corpus.py` | Tải JAR đã pin, chạy JUnit, javap cho 16 cặp thư viện–workload, xuất corpus |
| `scripts/verify_study.py` | Kiểm tra join, checksum, macro MAE |
| `scripts/check_paper.py` | Kiểm tra số liệu khớp giữa Markdown và LaTeX, link tồn tại, `\repo` có mặt ở `\repocommit`, script và ba bảng của Hình 1 khớp phiên bản ghim |
| `scripts/java_report.py` | Chạy kiểm tra Java tự động và in khung báo cáo cho cộng sự |
| `ml/slm/predict.py` | Inference Qwen 0.5B, có kiểm tra SHA-256 của weights |
| `ml/slm/scale.py` | Wrapper đổi checkpoint sang 1.5B |
| `ml/evaluate.py`, `summarize.py`, `study_data.py` | Fold, fit, dự đoán, metric, bootstrap |
| `ml/sensitivity.py`, `centered.py`, `rmse.py`, `scale.py`, `figures.py` | Các phân tích exploratory và hình |
| `ml/test_study.py`, `ml/test_supplements.py`, `data/tests/` | Unit test |
| `experiments/study/` | `protocol.md`, `config.json` (fold), `corpus/`, `slm/`, `evaluation/`, `supplement/` |
| `paper/` | `manuscript.md`, `main.tex`, `build.sh`, `ARXIV.md`, `project-results.png` |
| `research/` | `dependency_graph.yaml` (DAG trạng thái), `literature/` (ghi chú đọc, `papers.bib`, `evidence_matrix.csv`) |

## 7. Chạy lại

**Môi trường:**
- Temurin 25.0.5.1+2 và Maven 3.9.11, có trên `PATH`, với `JAVA_HOME` trỏ tới JDK này.
- Python 3.12.13.
- Dùng hai môi trường ảo riêng: `ml/requirements.txt` cho đánh giá, `ml/slm/requirements.txt` cộng torch 2.10.0 CPU cho inference.

Lệnh đầy đủ có trong [experiments/study/README.md](experiments/study/README.md). Thư mục output phải là thư mục mới. Tóm tắt:

```sh
python scripts/corpus.py /tmp/x/corpus
python ml/slm/predict.py experiments/study/corpus /tmp/x/slm --device cpu --threads 4 --batch-size 8
python ml/evaluate.py experiments/study/corpus experiments/study/slm /tmp/x/evaluation
python scripts/verify_study.py experiments/study/corpus experiments/study/slm /tmp/x/evaluation
python -m unittest discover -s ml -p 'test_*.py'
python scripts/check_paper.py
./paper/build.sh
```

**CI** (`.github/workflows/`):

| Workflow | Việc làm |
| --- | --- |
| `study.yml` | Tái lập corpus và inference trên Linux |
| `score.yml` | Test, đánh giá, verify, các phân tích bổ sung, Figure 1 |
| `paper.yml` | `check_paper.py` và build bằng pdfLaTeX |
| `scale.yml` | Inference 1.5B; riêng phần forward mất khoảng 11 phút trên CPU |

## 8. Quy tắc bắt buộc

1. **Không bịa** số liệu, trích dẫn, DOI, tên người, hay kết quả kiểm thử. Mọi con số trong bản thảo phải truy được về một file trong `experiments/study/`.
2. **Tách đăng ký trước và exploratory.** Không đổi protocol, fold hay phép so sánh chính sau khi đã thấy kết quả. Phân tích mới phải ghi rõ là exploratory, trong cả bản thảo lẫn docstring.
3. **Thông tin tĩnh và nhãn runtime phải tách biệt.** Không đưa count, workload ID hay đặc trưng suy ra từ nhãn vào input của mô hình.
4. **Sửa đồng thời `paper/manuscript.md` và `paper/main.tex`**, rồi chạy `check_paper.py`.
   - Khi thêm `\repo{path}` tới file mới: commit file trước, rồi đổi `\repocommit` sang commit đó.
   - Xem `\repocommit` ở đầu `paper/main.tex` để lấy đúng phiên bản của script và ba bảng dùng cho Hình 1.
5. **Node `JAVA` trong DAG giữ trạng thái `awaiting_external_test`** cho tới khi có báo cáo thật của cộng sự. Lần người duy trì tự chạy lại không được tính.
6. **Không tự chấp nhận giấy phép thay chủ dự án.** Qwen 3B dùng Qwen Research License (phi thương mại), chỉ chạy khi chủ dự án nói rõ "chạy 3B".
7. **Không commit weights model hay file JAR.** Kiểm tra hash của chúng bằng danh sách trong code.
8. **Quy ước Git:**
   - Làm trên `research/empirical-study`, mở PR vào `main`, merge bằng merge commit.
   - Mỗi commit một thay đổi rõ ràng, viết message bằng tiếng Anh.
   - Commit kết thúc bằng `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (hoặc dòng tương ứng của agent đang làm).
   - PR body kết thúc bằng dòng ghi công của agent.
9. **Văn phong bản thảo:** câu ngắn, chủ động, không dùng dấu gạch ngang dài (em dash), không phóng đại kết luận.
10. **Giữ DAG và [HANDOFF.md](HANDOFF.md) luôn đúng** sau mỗi mốc. Ghi thêm mục cập nhật có ngày vào HANDOFF.md.

## 9. Việc còn mở

Mọi việc dưới đây cần chủ dự án hoặc cộng sự. Agent chỉ làm phần kỹ thuật sau khi đã nhận được input của họ.

| Việc | Đang chờ | Agent làm gì khi có input |
| --- | --- | --- |
| Tên và đơn vị công tác của tác giả thứ hai | Chủ dự án (đã trả lời "Để sau") | Thay `[COAUTHOR NAME AND AFFILIATION]` trong `paper/main.tex` (`manuscript.md` không có danh sách tác giả), chạy `./paper/build.sh` để tạo `paper/build/arxiv.tar.gz`, cập nhật `ARXIV.md` |
| Báo cáo kiểm thử Java độc lập | Cộng sự chạy `python scripts/java_report.py` và M1–M7 trong `java/MANUAL_TESTING.md` | Ghi kết quả vào `java/TESTING.md` và HANDOFF.md, đổi trạng thái node `JAVA`; nếu có sai lệch thì điều tra trước khi sửa bất cứ thứ gì |
| Duyệt câu khai báo AI | Chủ dự án | Sửa câu đó ở cả hai bản thảo |
| Endorsement và nộp arXiv | Chủ dự án, bằng tài khoản arXiv của mình | Không làm thay; chỉ chuẩn bị file và metadata |
| Model 3B (tuỳ chọn) | Chủ dự án chấp nhận giấy phép | Dùng lại pipeline 1.5B: tạo wrapper mới, liệt kê hash của các file weights chia nhỏ, chạy CI, chấm điểm bằng `ml/scale.py`, ghi là exploratory |

## 10. Đã cân nhắc và loại

- **Qwen 7B:** cần nhiều RAM hơn 16 GB của runner GitHub.
- **Bài GraalSP bản tạp chí:** ScienceDirect trả về 403. Dùng luận án năm 2025 của tác giả thứ nhất thay thế (Bảng 6.2). Số trang nằm trong [reading note](research/literature/reading_notes/graalsp.md).
- **So trực tiếp với GraalSP hay GraalNN:** phải ánh xạ cạnh của Graal IR về đúng lệnh nhảy bytecode gốc, nên nằm ngoài phạm vi bài này.

## 11. Bẫy kỹ thuật đã gặp

- **macOS:** wheel xgboost cần `libomp.dylib`. Nếu không có libomp của Homebrew, đặt `DYLD_FALLBACK_LIBRARY_PATH` trỏ tới một thư mục chỉ chứa thư viện đó.
- **Tải weights trong CI:** đặt `HF_HUB_DISABLE_XET=1`.
- **BibTeX** tự hạ chữ hoa của từ viết tắt (VESPA, CodeT5, LLMs). Phải bọc chúng trong `{}`.
- **`check_paper.py`** đã chuẩn hóa chữ số mũ và bỏ qua hash trong `\texttt{}`. Khi viết số theo kiểu mới, kiểm tra cả hai bản thảo vẫn ra cùng bộ số.
- **Bảng 1 trong LaTeX** dùng `tabularx`, vì bảng thường bị tràn lề.
- **Chênh lệch số học giữa các nền tảng:** chạy lại trên macOS lệch so với Linux tối đa khoảng 10⁻⁵ mỗi site. Các bảng trong repo lấy từ Linux CI.
