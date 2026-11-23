# Can small language models predict runtime branch behavior from static Java bytecode?

Dự án của nhóm hai người nghiên cứu xác suất một lệnh nhảy có điều kiện trong bytecode Java sẽ đi đến đích nhảy. Khi dự đoán, mô hình chỉ đọc dữ liệu tĩnh. Nhóm chạy Java trong giai đoạn thu nhãn để biết hai cạnh thực sự được thực thi bao nhiêu lần.

## Bản thảo và kết quả

Trên 138 nhánh được quan sát ở tám thư viện Java, sai số tuyệt đối trung bình theo thư viện (macro MAE) trên workload normal là 0,424 khi hỏi trực tiếp Qwen 0.5B, 0,325 với lexical ridge và 0,327 khi dùng hidden state của Qwen. Lexical ridge có sai số thấp hơn cách hỏi trực tiếp ở cả tám thư viện. So sánh embedding với lexical ridge chưa cho thấy ưu thế rõ ràng. [Đọc bản thảo](paper/manuscript.md) · [Bảng kết quả](experiments/study/evaluation/) · [Tái lập thí nghiệm và Hình 1](experiments/study/README.md)

## DAG và thư viện bài báo

**[Mở sơ đồ DAG và danh mục tài liệu nghiên cứu](research/literature/README.md)**. Mỗi bài có ghi chú đọc và đường dẫn tới nguồn gốc. [DAG dạng YAML](research/dependency_graph.yaml) · [BibTeX](research/literature/papers.bib)

## Pilot đầu tiên

Một fixture tự viết biên dịch bằng Temurin 25 cho 6 nhánh bytecode, bao gồm vòng lặp và biểu thức short-circuit. Hai workload cho 12 cặp nhánh–workload, trong đó 10 cặp được quan sát. Hai cặp còn lại cùng thuộc phương thức không được gọi. Đây là kiểm tra pipeline trên một chương trình, chưa có kết quả dự đoán của mô hình. [Kết quả và provenance](experiments/results/decisions-v0.1/) · [Thiết kế và tiêu chí nghiệm thu](research/decisions.md)

| Cùng lệnh trong cùng file class | Taken | Fall-through | Xác suất đo được |
| --- | ---: | ---: | ---: |
| `guard(I)I`, BCI 1, workload `mostly-positive` | 9 | 1 | 0.90 |
| `guard(I)I`, BCI 1, workload `mostly-negative` | 2 | 8 | 0.20 |

Ở source, điều kiện là `n < 0`. Trong bytecode, `ifge 6` nhảy khi `n >= 0`. Có thể đếm trực tiếp các số thỏa điều kiện trong từng mảng input rồi so với hai bảng nhãn. [Fixture](java/fixtures/Decisions.java) · [Workload](experiments/configs/pilot.json) · [Disassembly](experiments/results/decisions-v0.1/javap.txt)

## Chạy lại pilot từ thư mục gốc

Dùng Temurin HotSpot 25, Maven 3.9.11 trên `PATH`, Python 3.13 và môi trường ảo. Đặt `JAVA_HOME` trỏ đến JDK 25. Bản ghi tham chiếu dùng Temurin 25.0.5.1+2 trên macOS arm64. Maven tải những thư viện được khai báo trong POM ở lần chạy đầu. [Maven build](java/pom.xml) · [Phiên bản thực tế](experiments/results/decisions-v0.1/manifest.json)

```sh
python3.13 -m venv .pilot-venv
. .pilot-venv/bin/activate
python -m pip install -r data/requirements.txt
python -m unittest discover -s data/tests -v
python scripts/pilot.py java/target-pilot-run
python data/validate.py java/target-pilot-run experiments/configs/pilot.json
```

Tham số cuối của runner là một thư mục kết quả **mới**. Có thể đặt ngoài repo. Runner chạy JUnit, biên dịch fixture, xuất static JSONL, chạy một JVM mới cho mỗi workload, đối chiếu kết quả hàm và kiểm tra toàn bộ nhãn trước khi công bố thư mục kết quả. Để chỉ kiểm tra mẫu đã commit, dùng `python data/validate.py experiments/results/decisions-v0.1 experiments/configs/pilot.json`.

## Bàn giao giữa hai thành viên

Cộng sự phụ trách kiểm thử độc lập phần đo Java. Hướng dẫn gồm cách tạo báo cáo và bảy phép kiểm tra thủ công. DAG đang chờ báo cáo của cộng sự ở nút `JAVA`. [Hướng dẫn kiểm thử](java/TESTING.md) · [Kiểm tra thủ công](java/MANUAL_TESTING.md)

[Bàn giao cho agent](AGENT_BRIEF.md) · [Nhật ký dự án](HANDOFF.md) · [Research brief gốc](CODEX_RESEARCH_BRIEF_SLM_JVM_BRANCH_PROFILING.md)
