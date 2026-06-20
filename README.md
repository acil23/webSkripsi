# Sistem Penjadwalan Mata Kuliah - Tahap 1

Tahap 1 berisi setup project web, struktur folder, routing dasar, template layout, sidebar, topbar, dashboard, dan placeholder untuk halaman berikutnya.

## Cara menjalankan

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Buka browser:

```text
http://127.0.0.1:8000
```

## Halaman yang tersedia

- `/dashboard`
- `/unggah-data`
- `/konfigurasi-kelas`
- `/parameter-algoritma`
- `/eksekusi-penjadwalan`
- `/hasil-penjadwalan`
- `/ekspor-hasil`
- `/riwayat-jadwal`

## Catatan

Fitur upload, konfigurasi kelas, parameter, eksekusi algoritma, hasil, ekspor, dan riwayat belum diimplementasikan pada tahap ini.
