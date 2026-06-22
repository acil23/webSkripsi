# Sistem Penjadwalan Mata Kuliah - Tahap 8

Tahap 8 menambahkan penyimpanan riwayat jadwal menggunakan SQLite sesuai rancangan UC-07 dan UC-08.

## Fitur Tahap 8

- Modal Simpan Riwayat pada halaman Hasil Penjadwalan.
- Validasi nama riwayat.
- Penyimpanan snapshot hasil jadwal ke SQLite.
- Penyimpanan jadwal, evaluasi, parameter, konfigurasi kelas, beban dosen, dan log konvergensi.
- Halaman Riwayat Jadwal.
- Filter daftar riwayat berdasarkan nama dan status feasibility.
- Detail Riwayat Jadwal.
- Hapus riwayat.
- Ekspor ulang hasil riwayat dalam CSV/ZIP.

## Menjalankan Aplikasi

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Buka aplikasi di:

```text
http://127.0.0.1:8000
```

## Alur Uji Tahap 8

1. Jalankan alur Tahap 1 sampai Tahap 6 hingga hasil penjadwalan tersedia.
2. Buka `/hasil-penjadwalan`.
3. Klik `Simpan Riwayat`.
4. Isi nama riwayat dan simpan.
5. Buka `/riwayat-jadwal`.
6. Klik `Lihat Detail` pada salah satu riwayat.
7. Coba `Ekspor Ulang`.
8. Coba hapus salah satu riwayat.

## Struktur Komponen Baru

- `app/entities/history_entities.py`
- `app/repositories/history_repository.py`
- `app/controllers/history_controller.py`
- `app/routers/history_router.py`
- `app/templates/riwayat_jadwal.html`
- `app/templates/detail_riwayat.html`

SQLite tersimpan di:

```text
data/db/scheduling_history.sqlite3
```

Database dibuat otomatis saat aplikasi dijalankan.

## Catatan Tahap 9 - Perbaikan Testing Fungsional

Perbaikan yang ditambahkan pada Tahap 9:

1. **Batas parameter demo cepat**
   - `max_generations` sekarang valid mulai dari `1` sampai `1000`.
   - `pop_size` sekarang valid mulai dari `10` sampai `500`.
   - Batas validasi dipusatkan pada `app/entities/algorithm_entities.py` melalui konstanta `PARAMETER_LIMITS`, sehingga dapat dinaikkan atau diturunkan dengan aman tanpa mencari banyak file.

2. **Progress eksekusi otomatis**
   - Halaman `Eksekusi Penjadwalan` sekarang melakukan polling ke `/api/scheduling/status` setiap 1 detik saat proses berjalan.
   - Progress bar, generasi, fitness, dan konflik diperbarui tanpa perlu klik menu lain atau refresh manual.

3. **State tombol eksekusi lebih jelas**
   - Saat idle: `Mulai Eksekusi`.
   - Saat running: `Eksekusi Sedang Berjalan` dan tombol nonaktif.
   - Setelah selesai: `Jalankan Ulang Eksekusi`.
   - Jika gagal: `Coba Eksekusi Ulang`.

## Patch Tahap 9.1 - Perbaikan polling status eksekusi

Patch ini memperbaiki progress bar pada halaman Eksekusi Penjadwalan yang sebelumnya tidak bergerak otomatis. Penyebabnya adalah blok JavaScript polling status berada di luar blok `content` template Jinja, sehingga tidak ikut dirender oleh layout utama. Script polling sekarang dipindahkan ke dalam blok konten dan dibuat lebih robust dengan pengambilan status awal melalui endpoint `/api/scheduling/status`, lalu polling otomatis setiap 1 detik selama state eksekusi masih `running`.
