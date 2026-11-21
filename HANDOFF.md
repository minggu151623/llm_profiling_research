# Bàn giao nghiên cứu dự đoán nhánh Java

**Nhánh làm việc:** `research/empirical-study`. Người dùng giao cho Codex thực hiện nghiên cứu đến bản thảo và báo cáo. Cộng sự phụ trách chạy kiểm thử Java độc lập. Chỉ ghi nhận lần kiểm thử của cộng sự khi nhận được kết quả thực tế. Bản thảo và quyết định nộp arXiv là hai mốc riêng.

## Mốc có thể kiểm tra lại

| Commit | Nội dung |
| --- | --- |
| `61bb555` | Pilot P0–P1 đã merge vào main, gồm DAG và schema v0. |
| `e6e775c` | Đăng ký trước metric, model, hai loại holdout, split tám project và giới hạn lấy mẫu. |
| `36013ae` | Khóa artifact, checksum, method, bộ input và hai phân phối trước khi thu nhãn. |
| `ff71e33` | CLI inference với revision Qwen cụ thể, hai biểu diễn và kiểm tra digest. |
| `46b3fe0` | Corpus đầu tiên, runner Java và phần fit/predict của evaluator. Manifest macOS đã đối chiếu hash source, output và 16 cặp checksum hành vi. |

Tám project có tổng 193 vị trí nhánh static, 138 vị trí có support ở mỗi workload. Con số này đếm coverage riêng từng workload. Pilot cũ không nằm trong tám project. [Protocol](experiments/study/protocol.md) · [Folds](experiments/study/config.json) · [Manifest](experiments/study/corpus/manifest.json)

## Cách tiếp quản

1. Clone repo, checkout nhánh trên, chạy `git status -sb`, `git log -8 --oneline`, xem PR và Actions đang chạy. Nếu dùng cùng workspace, giữ các thay đổi chưa commit, kiểm tra process và output trước khi chạy lại. Trên máy khác mọi input chuẩn đều lấy từ Git hoặc từ URL đã pin. Các đường dẫn `/tmp` dưới đây chỉ là cache trên máy gốc.
2. **Kiểm tra Java.** Dùng Temurin HotSpot 25.0.5.1+2, Maven 3.9.11, đặt JAVA_HOME và thêm cả hai vào PATH. Chạy `python3 scripts/corpus.py /tmp/corpus-replay` với đường dẫn output mới. Đối chiếu inventory, context, counts và output digests với corpus tham chiếu cho từng project và workload. Runner tự chạy JUnit và javap. Lưu manifest riêng cho mỗi nền tảng. Máy gốc có toolchain dưới `/tmp/jvm-pilot.MSq6P4` và JAR đã kiểm SHA trong `/tmp/branchstudy-jars`.
3. **Inference không đọc nhãn.** Dùng môi trường riêng theo [hướng dẫn SLM](ml/slm/README.md). Chạy `python ml/slm/predict.py experiments/study/corpus /tmp/slm-out --device cpu --threads 4 --batch-size 8`. Trên máy gốc có thể dùng `/opt/anaconda3/bin/python` với `--device mps --model-dir /tmp/qwen-branch.Xgk0ki` khi weights đã khớp hash trong predict.py. Cache range có thể tiếp tục bằng fast_download.py trong thư mục đó. Chỉ chấp nhận output khi CLI hoàn thành và manifest khớp. Không commit model weights hoặc JAR.
4. **Đánh giá.** Dùng Python 3.12, môi trường riêng cài `ml/requirements.txt`. Chạy `python ml/evaluate.py experiments/study/corpus /tmp/slm-out /tmp/evaluation-new`. Đầu ra phải gồm prediction từng branch/fold, coverage, pruning, hyperparameter và các bảng MAE/Brier/calibration/CI. Kiểm tra kết quả cả 8 fold, 9 model, 2 workload và tình huống seen-project/shift. Giữ nguyên protocol nếu kết quả âm.
5. **Báo cáo.** Kiểm tra nguồn gốc của related work. Raman & Li §4.3 đã dùng embedding tên callee trong dự đoán xác suất nhánh LLVM; xác minh bản gốc trước khi đặt claim. Phân biệt với nhận định về Graal IR, xác suất bytecode, code model zero-shot và benchmark throughput. Viết bản thảo trong paper/, cập nhật DAG và bảng bằng chứng, cung cấp hướng dẫn tái lập Linux và file test cho cộng sự. Báo kết quả thực đo và phần chưa xác minh cho người dùng.

## Trạng thái checkpoint ban đầu

Checkpoint ghi ngày 19/11/2026 sau thu corpus macOS. Chưa có kết quả Qwen thật hay bảng so sánh được kiểm chứng ở commit 46b3fe0. Tại commit này ml/evaluate.py còn thiếu module summarize. Cần chạy môi trường Linux cố định, inference thật, kiểm tra chống leakage, metrics/CI, literature bổ sung, manuscript và bàn giao kiểm thử Java. Tiến độ sau checkpoint xem mục cập nhật ở cuối file và lịch sử Git.

## Tái lập và đánh giá

Corpus tám project đã được chạy lại trên runner Ubuntu 24.04, khớp cả 32 file JSONL với macOS. Lần chạy Linux gốc là [Actions 44496268635](https://github.com/minggu151623/llm_profiling_research/actions/runs/44496268635). Xem trạng thái và đọc log bằng `gh run view 44496268635`, tải artifact bằng `gh run download 44496268635 -n linux-reference -D /tmp/linux-reference` khi run kết thúc. [PR nghiên cứu](https://github.com/minggu151623/llm_profiling_research/pull/2)

Đã có tổng hợp metric/CI tại `ml/summarize.py`, 11 công trình với liên kết vào DAG, và hướng dẫn kiểm tra độc lập tại [java/TESTING.md](java/TESTING.md). Khi có corpus/SLM/evaluation tương ứng, kiểm tra toàn bộ join, checksum, macro MAE và tính bất biến giữa hai workload bằng `python3 scripts/verify_study.py CORPUS SLM EVALUATION`. Cache JAR mặc định của runner ở `~/.cache/branch-study/jars`.

## Cập nhật 19/11/2026: bản thảo đầy đủ

Bản thảo [paper/manuscript.md](paper/manuscript.md) đã có abstract, kết quả RQ1–RQ4, Table 2, Figure 1, chi phí, discussion và conclusion. Mọi số liệu lấy từ `experiments/study/evaluation/` (lần chạy Linux, SciPy 1.15.3). Chạy lại trên macOS với SciPy 1.17.1 cho dự đoán lệch tối đa 9 × 10⁻⁶ mỗi site và macro MAE lệch dưới 10⁻⁶. `verify_study.py` và `test_study.py` đều đạt.

Kết quả chính: rating zero-shot gần như hằng số (0.34–0.49, Spearman −0.04), MAE 0.424 so với 0.429 của 0.5 và 0.325 của lexical ridge. Embedding ridge bằng lexical ridge (+0.002, CI −0.022 đến 0.024). Hidden state của Qwen có cosine trung bình 0.996 nên ridge gần như chỉ dùng phần structural. Lần chạy exploratory trừ trung bình train ([ml/centered.py](ml/centered.py)) không cải thiện (+0.017 so với lexical). Các phân tích masking, support, persistence và centering được ghi rõ là exploratory.

Còn mở: kiểm thử Java độc lập của cộng sự vẫn chờ kết quả thực tế. Bản thảo chưa có danh sách tác giả và chưa có quyết định nộp arXiv. CI `score.yml` chạy cả hai bước supplement trên Linux ([Actions 44499327262](https://github.com/minggu151623/llm_profiling_research/actions/runs/44499327262)); `centered.csv` trong repo lấy từ lần chạy đó, còn bản macOS lệch dưới 2 × 10⁻⁷.

## Cập nhật 21/11/2026: LaTeX và GraalSP

Bản LaTeX nằm ở [paper/main.tex](paper/main.tex). Chạy `./paper/build.sh` (cần Tectonic) để có `paper/build/main.pdf` và gói `paper/build/arxiv.tar.gz` cho arXiv. Mỗi lần sửa nội dung phải sửa cả `manuscript.md` lẫn `main.tex`. [scripts/check_paper.py](scripts/check_paper.py) kiểm tra ba điều: con số hai bản khớp nhau, link tương đối trong Markdown còn tồn tại, và mọi `\repo{...}` có mặt ở commit ghi trong `\repocommit`. Workflow `paper.yml` chạy script này mỗi khi `paper/` thay đổi, rồi biên dịch lại bằng pdfLaTeX và BibTeX của TeX Live trên Ubuntu 24.04, giống cách arXiv xử lý bản nộp. Lần chạy [44782753135](https://github.com/minggu151623/llm_profiling_research/actions/runs/44782753135) ra PDF 11 trang, không có trích dẫn thiếu hay dòng tràn lề. Khi thêm link tới file mới, commit file đó trước rồi đổi `\repocommit` sang commit ấy.

Không đọc được toàn văn bài GraalSP trên tạp chí (ScienceDirect trả về 403). Luận án tiến sĩ năm 2025 của tác giả thứ nhất thì đọc được toàn văn. Bảng 6.2 trong luận án báo cáo RMSE 0.299 và R² 0.551 cho XGBoost, trên các chương trình benchmark tách riêng khỏi 323.350 nhánh dùng để train. Vì vậy câu "GraalSP không báo cáo sai số cấp nhánh" trong bản thảo đã được thay bằng con số này. Bản thảo cũng ghi thêm RMSE gộp của dự án ([ml/rmse.py](ml/rmse.py)): structural XGBoost 0.381, hằng số 0.5 là 0.442. Phân tích này là mô tả, không đăng ký trước. Chi tiết và số trang nằm ở [reading note](research/literature/reading_notes/graalsp.md). Lần chạy CI Linux [44781783997](https://github.com/minggu151623/llm_profiling_research/actions/runs/44781783997) tạo lại các bảng supplement, lệch tối đa 4 × 10⁻⁷ so với bản trong repo. Dự đoán ridge giữa hai lần chạy Linux lệch tối đa 4.5 × 10⁻⁶, không đổi chữ số nào trong bản thảo.

Câu khai báo AI giờ ghi cả OpenAI Codex và Anthropic Claude Code, đúng với những công cụ đã tham gia. Bản thảo cũng trích dẫn ASM, scikit-learn, XGBoost và báo cáo kỹ thuật Qwen2.5-Coder; metadata đã đối chiếu với arXiv, Crossref, JMLR và trang của ASM. Còn chờ chủ dự án: danh sách tác giả, duyệt câu khai báo AI và quyết định nộp arXiv. Kiểm thử Java độc lập vẫn chờ cộng sự.

## Cập nhật 21/11/2026: chạy lại kiểm thử Java trên main

Sau khi merge PR #5–#9, người duy trì repo đã chạy lại toàn bộ [TESTING.md](java/TESTING.md) và [MANUAL_TESTING.md](java/MANUAL_TESTING.md) trên `main` tại commit 18a4f3b, với Temurin 25.0.5.1+2 và Maven 3.9.11 trên macOS arm64. Kết quả: JUnit 5/5 đạt; dựng lại corpus từ đầu cho 32/32 file JSONL giống hệt bản trong repo; `verify_study.py` đạt; M1 đến M7 đều cho đúng kết quả tài liệu ghi (M6 đạt 16/16 cho cả manifest trong repo lẫn manifest mới, M7 bị từ chối với `Corpus digest mismatch`). Đây không phải kiểm thử độc lập, nên node `JAVA` trên DAG vẫn ở trạng thái `awaiting_external_test`.

## Cập nhật 21/11/2026: thử model 1.5B, tác giả và giấy phép

Theo lựa chọn của chủ dự án, mình chạy thêm một thí nghiệm exploratory với Qwen2.5-Coder-1.5B-Instruct (revision `2e1fd397`) trên Linux ([Actions 44862417201](https://github.com/minggu151623/llm_profiling_research/actions/runs/44862417201)). Prompt, cách đọc kết quả và các fold giữ nguyên; tokenizer giống hệt bản 0.5B. Kết quả không đổi kết luận. Rating zero-shot nằm trong 0.499–0.557, Spearman 0.02, MAE 0.435, chênh +0.110 (0.061 đến 0.159) so với lexical ridge. Embedding ridge đạt MAE 0.326, chênh +0.001 (−0.023 đến 0.024) so với lexical ridge và −0.001 so với bản 0.5B. Output nằm ở [supplement/qwen-1.5b](experiments/study/supplement/qwen-1.5b/), bảng so sánh ở [scale.csv](experiments/study/supplement/scale.csv). Chấm lại trên macOS lệch tối đa 3 × 10⁻⁷.

Người kiểm thử Java sẽ là tác giả thứ hai. `paper/main.tex` đang giữ chỗ `[COAUTHOR NAME AND AFFILIATION]`, và `paper/build.sh` sẽ không tạo gói arXiv cho đến khi chỗ này được thay bằng tên thật. Giấy phép arXiv đã chọn là CC BY 4.0.
