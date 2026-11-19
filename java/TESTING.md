# Bàn giao kiểm thử Java

**Người phụ trách độc lập:** thành viên kiểm thử Java. **Trạng thái:** đã chạy kiểm tra tự động trên máy phát triển. Lần xác nhận do thành viên thực hiện đang chờ. Phạm vi là mã Java, hướng nhảy bytecode, dữ liệu đếm và khả năng chạy lại.

## Chạy từ thư mục gốc

Trên Linux hoặc macOS, dùng Eclipse Temurin HotSpot 25.0.5.1+2, Maven 3.9.11 và Python 3.11 trở lên. Đặt `JAVA_HOME` tới JDK. Lệnh đầu cho biết Maven có đang dùng đúng JDK đó hay không. Thư mục tạm giúp lưu kết quả của từng lần chạy riêng. [Bản Temurin theo nền tảng](https://github.com/adoptium/temurin25-binaries/releases/tag/jdk-25.0.5.1%2B2) · [Toolchain Linux đã pin](../.github/workflows/study.yml)

```sh
mvn -v
mvn -B -ntp -f java/pom.xml clean test
scratch=$(mktemp -d)
python3 scripts/corpus.py "$scratch/corpus"
for expected in experiments/study/corpus/*/*.jsonl; do
    cmp "$expected" "$scratch/corpus/${expected#experiments/study/corpus/}" || exit 1
done
```

Maven chạy 5 test. Runner tải các JAR đã pin và kiểm tra SHA-256, dùng `javap` để đối chiếu từng nhánh, rồi chạy phiên bản gốc và phiên bản gắn probe trong các JVM mới với `-Xverify:all`. Dữ liệu đo gồm 32 file JSONL cho tám project. `cmp` trả mã thoát 0 khi từng cặp file giống nhau. Trong `manifest.json`, các trường môi trường phản ánh máy thực hiện. [Mã chạy](../scripts/corpus.py) · [Config và checksum](../experiments/configs/corpus.json) · [Tập tham chiếu](../experiments/study/corpus/)

## Ba phép đối chiếu bằng tay

| Phép thử | Kết quả kỳ vọng |
| --- | --- |
| Hai nhánh `iflt` và `ifeq` cùng nhảy đến BCI 17. Một cạnh `goto` độc lập cũng đến đó. | Với sáu cặp đầu vào trong test, BCI 1 có taken/fall-through 2/4, BCI 5 có 1/3, BCI 11 có 2/1. Mỗi probe đếm theo cạnh xuất phát. |
| Joda-Time `safeMultiply(II)I`, BCI 19, `IFLE` | Với 100 cặp `(n,n)` ở mỗi workload, bình phương theo `long` cho biết có 95 tích nằm trong miền `int` ở `normal` và 73 ở `shift`. Nhãn tại BCI 19 lần lượt là 95/5 và 73/27. |
| Mỗi nhánh trong tám class đã chọn | ID trong static và context trùng nhau. Hai phiên bản context có cùng thứ tự opcode và đúng một dấu `>>` tại lệnh điều kiện. Một nhánh có mặt trong cả hai bảng nhãn kể cả khi chưa chạy. |

Bộ test cũng kiểm tra phương thức fixture chưa được gọi, trường hợp ném ngoại lệ và các nhánh biên dịch từ biểu thức short-circuit. [Tests cho corpus](src/test/java/org/branchpilot/CorpusVerificationTest.java) · [Tests cho fixture](src/test/java/org/branchpilot/BranchesTest.java)

Khi bàn giao, ghi commit, OS/kiến trúc, phiên bản JDK/Maven, kết quả 5 test và kết quả đối chiếu 32 file. Nếu `cmp` phát hiện sai khác, giữ thư mục tạm, báo project, workload và branch ID đầu tiên khác biệt.
