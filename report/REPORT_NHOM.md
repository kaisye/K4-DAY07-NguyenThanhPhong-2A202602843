# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** Alone
**Thành viên:** Nguyễn Thanh Phong
**Ngày:** 19/9/2026

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Tuyển sinh đại học tại Trường Đại học Công nghệ Thông tin, ĐHQG-HCM (UIT).

Corpus dùng các trang tuyển sinh công khai của UIT, gồm quy chế/phương thức tuyển sinh và mô tả các ngành. Chủ đề có các câu hỏi định lượng, điều kiện, quy trình và lựa chọn học tập; vì vậy phù hợp để kiểm tra semantic retrieval lẫn metadata filtering.

### Danh sách tài liệu (Data Inventory)

| # | Tên tài liệu | Nguồn | Ngày / phiên bản | Số ký tự | Metadata |
|---|---|---|---|---:|---|
| 1 | Phương thức tuyển sinh 2025 | `tuyensinh.uit.edu.vn/2025-phuong-thuc-tuyen-sinh-nam-2025` | 19/9/2026 / 2025 | 19,079 | source_url, retrieved_at, document_version, audience=student |
| 2 | Khoa học Máy tính | `tuyensinh.uit.edu.vn/nganh-dao-tao/nganh-khoa-hoc-may-tinh` | 19/9/2026 / 2025 | 12,118 | source_url, retrieved_at, document_version, audience=student |
| 3 | Kỹ thuật Máy tính | `tuyensinh.uit.edu.vn/nganh-dao-tao/nganh-ky-thuat-may-tinh` | 19/9/2026 / 2025 | 11,089 | source_url, retrieved_at, document_version, audience=student |
| 4 | KHMT liên kết quốc tế | `tuyensinh.uit.edu.vn/nganh-dao-tao/nganh-khoa-hoc-may-tinh-chuong-trinh-lien-ket-quoc-te` | 19/9/2026 / 2025 | 9,665 | source_url, retrieved_at, document_version, audience=student |
| 5 | Thiết kế vi mạch | `tuyensinh.uit.edu.vn/nganh-dao-tao/nganh-thiet-ke-vi-mach` | 19/9/2026 / 2025 | 6,564 | source_url, retrieved_at, document_version, audience=student |
| 6 | Giới thiệu UIT | `tuyensinh.uit.edu.vn/truong-dai-hoc-cong-nghe-thong-tin-dhqg-hcm` | 19/9/2026 / 2025 | 13,200 | source_url, retrieved_at, document_version, audience=public |

- [x] Corpus chỉ dùng nguồn công khai của UIT; không có dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` và `audience` trong frontmatter.

### Cấu trúc Metadata

| Trường | Kiểu | Ví dụ | Mục đích |
|---|---|---|---|
| `doc_id` | string | `nganh-ky-thuat-may-tinh` | Liên kết chunks với file gốc, phục vụ traceability và delete. |
| `source_url` | string | URL tuyển sinh UIT | Kiểm chứng nguồn trả lời. |
| `retrieved_at` | date | `2026-09-19` | Biết thời điểm thu thập. |
| `document_version` | string | `2025` | Phân biệt quy định theo năm. |
| `audience` | string | `student`, `public` | Lọc ứng viên trước similarity search. |
| `chunk_index` | integer | `13` | Truy vết chunk trong file. |

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

### Phân tích đường cơ sở (Baseline Analysis)

Frontmatter đã được bỏ trước khi đo. Các giá trị là kết quả `ChunkingStrategyComparator().compare()` với tham số mặc định.

| Tài liệu | Chiến lược | Số chunks | Độ dài TB | Giữ ngữ cảnh? |
|---|---|---:|---:|---|
| Phương thức tuyển sinh 2025 | Fixed size | 74 | 199.0 | Trung bình; có thể cắt giữa điều kiện. |
| Phương thức tuyển sinh 2025 | Sentence | 44 | 332.0 | Tốt theo câu, nhưng danh sách dài bị dồn. |
| Phương thức tuyển sinh 2025 | Recursive | 94 | 152.7 | Tốt ở đoạn ngắn, nhiều chunks. |
| Kỹ thuật Máy tính | Fixed size | 43 | 196.7 | Trung bình. |
| Kỹ thuật Máy tính | Sentence | 15 | 561.9 | Tốt nhưng chunk dài. |
| Kỹ thuật Máy tính | Recursive | 55 | 151.5 | Tốt ở các đoạn. |
| KHMT liên kết quốc tế | Fixed size | 37 | 197.3 | Trung bình. |
| KHMT liên kết quốc tế | Sentence | 15 | 485.9 | Tốt nhưng chunk dài. |
| KHMT liên kết quốc tế | Recursive | 48 | 149.6 | Tốt ở các đoạn. |

### Chiến lược của thành viên

**Nguyễn Thanh Phong — HeadingChunker (custom)**

- **Loại chiến lược:** Tách theo heading Markdown/heading viết hoa, `chunk_size=800`; section quá dài được cắt tiếp bằng `RecursiveChunker`.
- **Lý do chọn:** Các trang quy định đã được biên soạn theo mục. Giữ từng mục làm đơn vị trước giúp điều kiện và tiêu đề đi cùng nhau; khi cắt nhỏ, tiêu đề được gắn lại vào từng mảnh để giữ ngữ cảnh.
- **Kết quả nạp:** 118 chunks; embeddings dùng `text-embedding-3-small`; agent dùng gateway `cx/gpt-5.5` và trích dẫn số chunk.

### So sánh và nhận xét

HeadingChunker phù hợp nhất với corpus quy định vì tôn trọng cấu trúc có sẵn của tác giả. Khi section dài, hạ xuống RecursiveChunker cân bằng ngữ cảnh section và giới hạn kích thước. Hạn chế thấy ở câu 5: chunk về thời lượng/địa điểm chưa vào top-3, nên cần tinh chỉnh heading cleanup hoặc query expansion.

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn

| # | Câu hỏi | Gold answer | Chunk chứa thông tin |
|---|---|---|---|
| 1 | Ngưỡng đầu vào THPT 2025 và yêu cầu riêng Thiết kế vi mạch? | 22 điểm; riêng Thiết kế vi mạch cần Toán >= 6.5. | `2025-phuong-thuc-tuyen-sinh-nam-2025#13` |
| 2 | Điều kiện điểm SAT theo chứng chỉ quốc tế? | SAT >= 1200, mỗi môn >= 600. | `2025-phuong-thuc-tuyen-sinh-nam-2025#7` |
| 3 | Thí sinh đạt giải cao đăng ký thông tin khi nào? | 27/6/2025 đến hết 28/7/2025. | `2025-phuong-thuc-tuyen-sinh-nam-2025#6` |
| 4 | Kỹ thuật Máy tính có hai hướng chuyên sâu nào? | Thiết kế vi mạch và phần cứng; Hệ thống nhúng và Robot. | `nganh-ky-thuat-may-tinh#4` |
| 5 | KHMT liên kết quốc tế kéo dài bao lâu và học ở đâu? | 3.5 năm; giai đoạn 1 học UIT, giai đoạn 2 học UIT hoặc chuyển tiếp Birmingham City University. | `nganh-khoa-hoc-may-tinh-chuong-trinh-lien-ket-quoc-te#12` |

### Tổng hợp chất lượng truy xuất

Kết quả chạy `python bench.py`: OpenAI `text-embedding-3-small`, 118 chunks, top-k=3; agent dùng gateway `cx/gpt-5.5`.

| # | Câu hỏi | Chunk liên quan trong top-3? | Kết quả agent | Điểm |
|---|---|---|---|---:|
| 1 | Ngưỡng THPT + Vi mạch | Có, top-1 (0.686) | Đúng đầy đủ | 2/2 |
| 2 | Điều kiện SAT | Có, top-3 (0.585) | Đúng: SAT >= 1200, mỗi môn >= 600 | 2/2 |
| 3 | Thời gian đăng ký | Có, top-1 (0.586) | Đúng | 2/2 |
| 4 | Hai hướng KTMT | Có, top-1 (0.600) | Đúng | 2/2 |
| 5 | Liên kết quốc tế | Không; top-1 cùng tài liệu (0.612) nhưng thiếu dữ kiện | Báo không đủ ngữ cảnh, không bịa | 0/2 |

**Lọc bằng metadata có giúp ích không?** Query 5 chạy với `metadata_filter={"audience": "student"}`. Filter thực hiện trước similarity search và loại tài liệu giới thiệu chung `audience=public`; tuy nhiên riêng query này vẫn cần cải thiện ranking để chunk thời lượng/địa điểm vào top-3. Filter thu hẹp đúng tập ứng viên nhưng không thay thế chất lượng chunk/query.

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Các insights trình bày:**

- Chunk theo heading giữ điều kiện tuyển sinh và tiêu đề mục đi cùng nhau; heading được nối lại khi section bị cắt nhỏ.
- Metadata phải được truyền vào mọi chunk; nếu lọc sau top-k có thể bỏ hết kết quả hợp lệ.
- Grounded prompt đánh số `[1]`, `[2]`, `[3]` giúp truy vết câu trả lời về đúng chunk/nguồn.

**Bài học rút ra:** Cùng corpus nhưng strategy khác thay đổi sự cân bằng giữa kích thước chunk và độ đầy đủ thông tin. Trường hợp câu 5 chứng minh agent từ chối khi thiếu context an toàn hơn tạo đáp án không có nguồn.

**Nếu làm lại:** Chuẩn hóa heading từ HTML sạch hơn, bổ sung query expansion cho “thời lượng”, “địa điểm học”, và thêm cache embedding theo hash nội dung để chạy benchmark lặp lại nhanh hơn.

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá |
|---|---:|
| Lựa chọn tài liệu | 10 / 10 |
| Thiết kế chiến lược | 15 / 15 |
| Chất lượng truy xuất | 8 / 10 |
| Thuyết trình (Demo) & bài học | 4 / 5 |
| **Tổng phần nhóm** | **37 / 40** |
