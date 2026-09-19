# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Thanh Phong
**Nhóm:** Alone
**Ngày:** 19/9/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> *Viết 1-2 câu: Cosine similarity đo mức độ giống nhau về **hướng của hai vector**. Với text embedding, cosine similarity cao thường cho thấy hai câu có ý nghĩa hoặc ngữ cảnh gần nhau.
*

**Cặp câu có similarity cao:**

- A: `Con mèo đang ngủ trên ghế sofa.`
- B: `Một chú mèo đang nghỉ ngơi trên chiếc ghế dài.`

Hai câu sử dụng từ ngữ khác nhau nhưng cùng diễn đạt ý nghĩa là một con mèo đang nghỉ ngơi trên ghế, nên embedding của chúng dự kiến có cosine similarity cao.

**Cặp câu có similarity thấp:**

- A: `Con mèo đang ngủ trên ghế sofa.`
- B: `Nhà máy sản xuất chip đang mở rộng dây chuyền.`

Hai câu nói về hai chủ đề hoàn toàn khác nhau, nên hướng của hai vector embedding dự kiến khác nhau và cosine similarity thấp.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> *Cosine similarity tập trung vào **hướng của vector** thay vì độ lớn tuyệt đối của vector. Điều này phù hợp với text embedding vì ta thường quan tâm đến mức độ gần nhau về mặt ngữ nghĩa hơn là độ dài hoặc magnitude của vector. Ngoài ra, khi vector đã được chuẩn hóa về độ dài 1 thì dot product chính là cosine similarity.
*

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:
$$ ceil((10000−50)/(500−50))
 = ceil(9950/450)
 = ceil(22.111...) $$
> *Đáp án: 23*

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> *Viết 1-2 câu: 25 chunks, Overlap lớn hơn giúp các chunk liên tiếp giữ lại nhiều ngữ cảnh chung hơn. Điều này có thể giúp embedding và quá trình retrieval không làm mất thông tin nằm ở ranh giới giữa hai chunk. Tuy nhiên, overlap lớn cũng làm tăng số lượng chunk, từ đó tăng chi phí lưu trữ, embedding và tìm kiếm.*

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:

SentenceChunker chia văn bản dựa trên ranh giới câu. Tôi sử dụng regular expression để tách văn bản sau các dấu kết thúc câu ., !, ? nhưng vẫn giữ lại dấu câu trong từng câu. Sau đó, các câu được gom thành từng chunk, mỗi chunk có tối đa max_sentences_per_chunk câu.

Các trường hợp đặc biệt được xử lý gồm:

Text rỗng → trả về [].
Số câu ít hơn giới hạn → gom thành một chunk.
Loại bỏ khoảng trắng thừa bằng strip().
Giữ nguyên dấu câu trong nội dung câu.

Một hạn chế của cách tiếp cận này là regex đơn giản có thể nhận diện sai dấu chấm trong một số trường hợp như từ viết tắt (TS., v.v.) hoặc số thập phân (3.14).


**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:

RecursiveChunker chia văn bản theo nhiều mức separator với thứ tự ưu tiên:

["\n\n", "\n", ". ", " ", ""]

Tôi ưu tiên các ranh giới lớn và tự nhiên như đoạn văn, dòng và câu trước khi chuyển xuống các mức nhỏ hơn.

Nếu một phần sau khi split vẫn dài hơn chunk_size, _split() tiếp tục được gọi đệ quy với separator tiếp theo. Sau khi chia nhỏ, các phần liền kề được ghép lại nếu tổng độ dài không vượt quá chunk_size.

Các base case gồm:

Text rỗng → [].
Text đã nhỏ hơn hoặc bằng chunk_size → giữ nguyên thành một chunk.
Không còn separator → chia theo kích thước ký tự.
separators=[] → fallback sang chia theo kích thước ký tự để tránh lỗi.

Cách này giúp ưu tiên giữ nguyên cấu trúc và ngữ nghĩa của văn bản thay vì cắt cứng theo số ký tự ngay từ đầu.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:

EmbeddingStore chịu trách nhiệm lưu các Document cùng vector embedding và thực hiện tìm kiếm theo độ tương đồng.

add_documents() không tự động chunk tài liệu. Mỗi Document được thêm vào tương ứng với một record trong collection. Việc chunking được thực hiện trước đó ở tầng Chunker, sau đó mỗi chunk được tạo thành một Document riêng.

Khi search() được gọi, query được chuyển thành embedding rồi so sánh với các vector đã lưu. Các vector được chuẩn hóa nên có thể sử dụng dot product để tính cosine similarity. Kết quả được sắp xếp theo độ tương đồng và trả về top_k document phù hợp nhất.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:

search_with_filter() bổ sung điều kiện lọc metadata vào quá trình tìm kiếm. Các document được giới hạn theo filter trước khi thực hiện việc so sánh similarity và chọn top_k kết quả.

delete_document() xóa document dựa trên ID. Sau khi xóa, document đó không còn trong collection và không thể xuất hiện trong các kết quả tìm kiếm tiếp theo.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:

KnowledgeBaseAgent kết hợp vector search với LLM theo pipeline:

User Question
      ↓
EmbeddingStore.search()
      ↓
Retrieved Documents
      ↓
Context
      ↓
Prompt
      ↓
llm_fn()
      ↓
Answer

Khi nhận câu hỏi, agent trước tiên tìm các document liên quan trong EmbeddingStore. Nội dung của các document này được đưa vào context của prompt cùng với câu hỏi của người dùng.

LLM sau đó sử dụng context được retrieval để tạo câu trả lời. Nhờ vậy, agent có thể trả lời dựa trên dữ liệu trong knowledge base thay vì chỉ dựa vào kiến thức có sẵn của mô hình.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
pytest tests/ -q
..........................................                               [100%]
42 passed in 0.05s
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Con mèo đang ngủ trên ghế sofa. | Một chú mèo đang nghỉ ngơi trên chiếc ghế dài. | cao | 0.628 | Có |
| 2 | Điều kiện SAT để xét tuyển là gì? | Thí sinh cần SAT từ 1200 điểm, mỗi môn từ 600 điểm. | cao | 0.583 | Có |
| 3 | Con mèo đang ngủ trên ghế sofa. | Nhà máy sản xuất chip đang mở rộng dây chuyền. | thấp | 0.238 | Có |
| 4 | Ngành Kỹ thuật Máy tính có hướng Hệ thống nhúng và Robot. | UIT đào tạo hướng chuyên sâu Hệ thống nhúng và Robot. | cao | 0.687 | Có |
| 5 | Thời gian đào tạo chương trình liên kết là bao lâu? | Sinh viên có thể học tại UIT hoặc chuyển tiếp sang Birmingham City University. | thấp | 0.285 | Có |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp 5 có cùng chủ đề chương trình liên kết nhưng similarity thấp (0.285) vì một câu hỏi về thời lượng, câu còn lại nói về địa điểm học. Điều này cho thấy embedding ưu tiên ý nghĩa cụ thể hơn là chỉ trùng miền chủ đề hay từ khóa.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Ngưỡng đầu vào THPT 2025 và yêu cầu riêng của Thiết kế vi mạch? | `2025...#13`: ngưỡng 22 điểm, riêng Toán >= 6.5. | 0.686 | Có, top-1 | 22 điểm; Thiết kế vi mạch yêu cầu Toán tối thiểu 6.5 [1]. |
| 2 | Điều kiện điểm SAT theo chứng chỉ quốc tế? | `2025...#7`: SAT >= 1200, mỗi môn >= 600. | 0.585 | Có, top-3 | SAT từ 1200, mỗi môn từ 600 [3]. |
| 3 | Thí sinh đạt giải cao đăng ký thông tin khi nào? | `2025...#6`: 27/6/2025 đến hết 28/7/2025. | 0.586 | Có, top-1 | Từ 27/6/2025 đến hết 28/7/2025 [1]. |
| 4 | Kỹ thuật Máy tính có hai hướng chuyên sâu nào? | `nganh-ky-thuat-may-tinh#4`: Vi mạch & phần cứng; Nhúng & Robot. | 0.600 | Có, top-1 | Thiết kế vi mạch và phần cứng; Hệ thống nhúng và Robot [1]. |
| 5 | Chương trình KHMT liên kết quốc tế kéo dài bao lâu và học ở đâu? | Top-3 chưa có chunk `...#12` chứa thời lượng/địa điểm. | 0.612 | Chưa | Agent báo ngữ cảnh chưa đủ; cần cải thiện truy xuất chunk thời lượng/địa điểm. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 4 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Metadata không chỉ là dữ liệu mô tả: khi được sao chép vào mọi chunk, nó cho phép lọc trước retrieval và tránh trộn lẫn tài liệu khác đối tượng. So sánh kết quả cũng cho thấy một query nhiều ý cần chunk chứa trọn vẹn các ý đó; nếu không, agent nên trả lời thiếu thông tin thay vì bịa.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 8 / 10 |
| **Tổng phần cá nhân** | **58 / 60** |
