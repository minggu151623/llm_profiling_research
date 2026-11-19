# Can small language models predict runtime branch behavior from static Java bytecode?

Dự án của nhóm hai người nghiên cứu xác suất một lệnh nhảy có điều kiện trong bytecode Java sẽ đi đến đích nhảy. Mô hình tương lai chỉ đọc dữ liệu tĩnh. Nhóm chạy Java trong giai đoạn thu nhãn để biết hai cạnh thực sự được thực thi bao nhiêu lần.

## DAG và thư viện bài báo

**[Mở sơ đồ DAG và danh mục ba bài báo](research/literature/README.md)**. Mỗi bài có ghi chú đọc và đường dẫn tới nguồn gốc. [DAG dạng YAML](research/dependency_graph.yaml) · [BibTeX](research/literature/papers.bib)

## Pilot đầu tiên

Một fixture tự viết biên dịch bằng Temurin 25 cho 6 nhánh bytecode, bao gồm vòng lặp và biểu thức short-circuit. Hai workload cho 12 cặp nhánh–workload, trong đó 10 cặp được quan sát. Hai cặp còn lại cùng thuộc phương thức không được gọi. Đây là kiểm tra pipeline trên một chương trình, chưa có kết quả dự đoán của mô hình. [Kết quả và provenance](experiments/results/decisions-v0.1/) · [Thiết kế và tiêu chí nghiệm thu](research/decisions.md)

| Cùng lệnh trong cùng file class | Taken | Fall-through | Xác suất đo được |
| --- | ---: | ---: | ---: |
| `guard(I)I`, BCI 1, workload `mostly-positive` | 9 | 1 | 0.90 |
| `guard(I)I`, BCI 1, workload `mostly-negative` | 2 | 8 | 0.20 |

Ở source, điều kiện là `n < 0`. Trong bytecode, `ifge 6` nhảy khi `n >= 0`. Có thể đếm trực tiếp các số thỏa điều kiện trong từng mảng input rồi so với hai bảng nhãn. [Fixture](java/fixtures/Decisions.java) · [Workload](experiments/configs/pilot.json) · [Disassembly](experiments/results/decisions-v0.1/javap.txt)

## Chạy lại từ thư mục gốc

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

| Người review | Phần cần đọc | Quyết định cần ghi vào PR |
| --- | --- | --- |
| Java/JVM engineer | [Quy ước BCI, ID và nhãn](data/schema/README.md), [tests Java](java/src/test/java/org/branchpilot/BranchesTest.java) | Xác nhận ánh xạ cạnh, phạm vi fixture và điều kiện mở rộng sang JAR |
| AI/ML researcher | [RQ và protocol đo](research/questions.md), [prior work](research/literature/novelty_map.md), [loader](data/validate.py) | Xác nhận baseline, cách tách dữ liệu và giới hạn claim |
| Cả hai | [Quyết định còn mở](research/decisions.md), [dependency graph](research/dependency_graph.yaml) | Dùng schema v0 cho pilot. Cùng duyệt bộ project, workload và manifest chia tập trước khi đo trên quy mô lớn |

[Research brief gốc](CODEX_RESEARCH_BRIEF_SLM_JVM_BRANCH_PROFILING.md)
