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
