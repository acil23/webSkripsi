"""Definisi jenis data masukan dan struktur kolom wajib CSV."""

from __future__ import annotations

MAX_UPLOAD_SIZE_BYTES = 2 * 1024 * 1024

UPLOAD_DATASETS = [
    {
        "key": "data_mata_kuliah",
        "label": "Data Mata Kuliah",
        "icon": "▤",
        "input_name": "data_mata_kuliah",
        "multiple": True,
        "note": "Unggah 2 file: MK wajib dan MK pilihan.",
    },
    {
        "key": "data_dosen",
        "label": "Data Dosen",
        "icon": "◉",
        "input_name": "data_dosen",
        "multiple": False,
        "note": "Master data dosen pengampu.",
    },
    {
        "key": "data_preferensi_dosen",
        "label": "Data Preferensi Dosen",
        "icon": "♡",
        "input_name": "data_preferensi_dosen",
        "multiple": False,
        "note": "Relasi dosen, mata kuliah, dan prioritas.",
    },
    {
        "key": "data_ruang_kelas",
        "label": "Data Ruang Kelas",
        "icon": "▥",
        "input_name": "data_ruang_kelas",
        "multiple": False,
        "note": "Daftar ruang dan kapasitas.",
    },
    {
        "key": "data_slot_waktu",
        "label": "Data Slot Waktu",
        "icon": "◷",
        "input_name": "data_slot_waktu",
        "multiple": False,
        "note": "Hari, jam, dan durasi SKS.",
    },
    {
        "key": "data_jumlah_mahasiswa",
        "label": "Data Jumlah Mahasiswa",
        "icon": "👥",
        "input_name": "data_jumlah_mahasiswa",
        "multiple": False,
        "note": "Jumlah mahasiswa aktif per angkatan.",
    },
    {
        "key": "data_prakrs",
        "label": "Data Pra-KRS",
        "icon": "▧",
        "input_name": "data_prakrs",
        "multiple": False,
        "note": "Peminat mata kuliah pilihan.",
    },
]

REQUIRED_COLUMNS = {
    "mk_wajib": [
        "Kode MK",
        "Nama MK",
        "SKS",
        "Semester",
        "Bidang Ilmu Umum",
        "Cabang Ilmu",
        "Ranting Ilmu",
    ],
    "mk_pilihan": [
        "Kode MK",
        "Nama MK",
        "SKS",
        "Semester",
        "Bidang Ilmu Umum",
        "Cabang Ilmu",
        "Ranting Ilmu",
    ],
    "data_dosen": [
        "NAMA",
        "HOMEBASE",
        "Status Dosen",
        "Boleh Dijadwalkan",
        "Dihitung Dalam Fairness",
        "BIDANG ILMU UMUM",
        "CABANG ILMU",
        "RANTING ILMU",
    ],
    "data_preferensi_dosen": [
        "Kode MK",
        "Nama MK",
        "Prioritas",
        "Berminat",
        "Nama Dosen",
    ],
    "data_ruang_kelas": [
        "Ruang Kelas",
        "Kapasitas Max (Mahasiswa)",
    ],
    "data_slot_waktu": [
        "id",
        "hari",
        "jam_mulai",
        "jam_selesai",
        "sks",
    ],
    "data_jumlah_mahasiswa": [
        "Angkatan",
        "Jumlah Mahasiswa TIF",
    ],
    "data_prakrs": [
        "Kode MK",
        "Semester Aktif",
        "Jumlah Peminat",
    ],
}

CANONICAL_FILENAMES = {
    "mk_wajib": "MK Wajib TIF_All Semester_Mapped_v3.csv",
    "mk_pilihan": "MK Pilihan TIF_All Semester_Mapped_v3.csv",
    "data_dosen": "Master Data Dosen Pengampu.csv",
    "data_preferensi_dosen": "Preferensi MK dosen TIFv2.csv",
    "data_ruang_kelas": "Ruang Kelas.csv",
    "data_slot_waktu": "Time_Slots v2.csv",
    "data_jumlah_mahasiswa": "Jumlah Mahasiswa TIF.csv",
    "data_prakrs": "Pra_KRS_MK_Pilihan.csv",
}
