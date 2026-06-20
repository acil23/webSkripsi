# Sistem Penjadwalan Mata Kuliah - Tahap 3

Tahap 3 mengimplementasikan UC-02 Mengelola Konfigurasi Pembukaan Kelas.

## Fitur yang sudah tersedia

1. Dashboard dan layout dasar.
2. Upload dan validasi CSV data masukan.
3. Pembentukan `DatasetBundle`.
4. Halaman Konfigurasi Pembukaan Kelas.
5. Rekomendasi jumlah kelas wajib berdasarkan jumlah mahasiswa.
6. Rekomendasi jumlah kelas pilihan berdasarkan data Pra-KRS.
7. Filter semester, jenis mata kuliah, dan pencarian mata kuliah.
8. Edit jumlah kelas final.
9. Simpan konfigurasi pembukaan kelas.
10. Pembentukan kelas paralel dan sesi perkuliahan.
11. Ekspor konfigurasi aktif ke `data/uploaded/Konfigurasi_Pembukaan_Kelas_<Semester>.csv` agar kompatibel dengan engine algoritma.

## Menjalankan aplikasi

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

## Alur uji Tahap 3

1. Buka `/unggah-data`.
2. Unggah seluruh CSV masukan.
3. Pastikan semua status data Valid.
4. Klik `Lanjut ke Konfigurasi Pembukaan Kelas`.
5. Pilih semester Ganjil atau Genap.
6. Tinjau tabel rekomendasi pembukaan kelas.
7. Ubah salah satu nilai `Kelas Final`.
8. Klik `Simpan Konfigurasi`.
9. Pastikan ringkasan `Kelas Terbentuk` dan `Sesi Perkuliahan` terisi.
10. Tombol `Lanjut ke Parameter Algoritma` aktif setelah konfigurasi disimpan.

## Komponen rancangan yang terimplementasi

- `SchedulingRouter`
- `SchedulingController`
- `ClassOpeningController`
- `ClassOpeningService`
- `KonfigurasiPembukaanKelas`
- `KelasPerkuliahan`
- `SesiPerkuliahan`
- `currentClassOpening`
- `currentClasses`
- `currentSessions`

## Catatan scope

Tahap ini belum menjalankan Memetic Algorithm. Engine algoritma tetap belum diubah. Integrasi engine akan dilakukan pada Tahap 5 setelah parameter algoritma selesai pada Tahap 4.
