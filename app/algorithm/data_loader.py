
import os
import math
import random
import re
import pandas as pd

# ============================================================
# DATA LOADER FINAL
# Membaca Konfigurasi Pembukaan Kelas sebagai sumber jumlah kelas
# ============================================================

MISSING_VALUES = {"", "-", "nan", "none", "tidak tersedia", "n/a", "null"}


def normalize_name(name):
    """Normalisasi nama dosen agar nama di preferensi dan master pengampu dapat dicocokkan."""
    if not isinstance(name, str):
        return ""

    text = name.lower()

    # Hapus sebagian gelar umum. Tidak harus sempurna, cukup stabil untuk pencocokan.
    titles = [
        "prof.", "dr.", "drs.", "dra.", "ir.", "eng.", "h.", "hj.",
        "s.kom.", "s.t.", "m.t.", "m.kom.", "m.sc.", "m.cs.", "m.eng.",
        "ph.d.", "ph.d", "mba.", "mba"
    ]

    for title in titles:
        text = text.replace(title, "")

    # Ambil bagian sebelum koma karena gelar sering berada setelah nama.
    text = text.split(",")[0]

    # Hapus simbol, rapikan spasi.
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return " ".join(text.split())


def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_code(value):
    return clean_text(value).upper()


def is_yes(value):
    return clean_text(value).lower() in {"ya", "yes", "true", "1", "y"}


def is_known_hierarchy_value(value):
    return clean_text(value).lower() not in MISSING_VALUES


def get_course_suffix(index):
    """
    0 -> A, 1 -> B, ..., 25 -> Z, 26 -> AA, dst.
    """
    letters = ""
    idx = index
    while True:
        letters = chr(65 + (idx % 26)) + letters
        idx = idx // 26 - 1
        if idx < 0:
            break
    return letters


# ============================================================
# 1. LOAD DATA DASAR
# ============================================================

def load_time_slots(path):
    df = normalize_columns(pd.read_csv(path))
    df = df.rename(columns={
        "hari": "Hari",
        "jam_mulai": "Mulai",
        "jam_selesai": "Selesai",
        "sks": "sks_val"
    })

    if "Sesi" in df.columns:
        df = df.drop(columns=["Sesi"])

    # Gunakan id asli jika ada agar stabil, fallback ke index.
    if "id" in df.columns:
        df["slot_id"] = df["id"].astype(int)
    else:
        df["slot_id"] = df.index

    return df.to_dict(orient="records")


def load_rooms(path):
    df = normalize_columns(pd.read_csv(path))
    df = df.rename(columns={
        "Ruang Kelas": "Ruang",
        "Kapasitas Max (Mahasiswa)": "Kapasitas"
    })

    df["room_id"] = df.index
    df["Kapasitas"] = df["Kapasitas"].astype(int)

    return df.to_dict(orient="records")


# ============================================================
# 2. LOAD MASTER MK DAN DOSEN
# ============================================================

def load_master_courses(file_mk_wajib, file_mk_pilihan):
    """
    Menggabungkan master MK wajib dan MK pilihan menjadi satu dictionary berbasis Kode MK.
    """
    course_map = {}
    mk_hierarchy = {}

    sources = [
        ("Wajib", file_mk_wajib),
        ("Pilihan", file_mk_pilihan),
    ]

    for jenis_mk, file_path in sources:
        df = normalize_columns(pd.read_csv(file_path))

        for _, row in df.iterrows():
            kode = clean_code(row["Kode MK"])

            sks_col = "SKS" if "SKS" in df.columns else "sks"

            course_data = {
                "kode_mk": kode,
                "nama_mk": clean_text(row["Nama MK"]),
                "sks": int(row[sks_col]),
                "jenis_mk": jenis_mk,
                "semester_kurikulum": clean_text(row["Semester"]),
                "bidang": clean_text(row.get("Bidang Ilmu Umum", "")),
                "cabang": clean_text(row.get("Cabang Ilmu", "")),
                "ranting": clean_text(row.get("Ranting Ilmu", "")),
            }

            course_map[kode] = course_data
            mk_hierarchy[kode] = {
                "bidang": course_data["bidang"],
                "cabang": course_data["cabang"],
                "ranting": course_data["ranting"],
            }

    return course_map, mk_hierarchy


def load_pengampu_data(file_master_dosen):
    """
    Membaca Master Data Dosen Pengampu.
    Field penting:
    - Boleh Dijadwalkan
    - Dihitung Dalam Fairness
    """
    df = normalize_columns(pd.read_csv(file_master_dosen))

    dosen_hierarchy = {}
    official_name_by_norm = {}
    allowed_dosen = set()
    fairness_dosen = set()

    for _, row in df.iterrows():
        nama_asli = clean_text(row["NAMA"])
        norm = normalize_name(nama_asli)

        boleh_dijadwalkan = is_yes(row.get("Boleh Dijadwalkan", "Ya"))
        dihitung_fairness = is_yes(row.get("Dihitung Dalam Fairness", "Ya"))

        dosen_hierarchy[norm] = {
            "nama_asli": nama_asli,
            "homebase": clean_text(row.get("HOMEBASE", "")),
            "status_dosen": clean_text(row.get("Status Dosen", "")),
            "boleh_dijadwalkan": boleh_dijadwalkan,
            "dihitung_fairness": dihitung_fairness,
            "bidang": clean_text(row.get("BIDANG ILMU UMUM", "")),
            "cabang": clean_text(row.get("CABANG ILMU", "")),
            "ranting": clean_text(row.get("RANTING ILMU", "")),
        }

        official_name_by_norm[norm] = nama_asli

        if boleh_dijadwalkan:
            allowed_dosen.add(nama_asli)

        if boleh_dijadwalkan and dihitung_fairness:
            fairness_dosen.add(nama_asli)

    return dosen_hierarchy, official_name_by_norm, allowed_dosen, fairness_dosen


# ============================================================
# 3. LOAD PREFERENSI
# ============================================================

def load_preference_data(path, official_name_by_norm=None, allowed_dosen=None):
    """
    Membaca preferensi dan menstandarkan nama dosen ke nama resmi dari master pengampu.
    Dosen yang Boleh Dijadwalkan = Tidak akan dikeluarkan dari kandidat.
    """
    df = normalize_columns(pd.read_csv(path))

    candidates_dict = {}
    pref_info = {}

    official_name_by_norm = official_name_by_norm or {}
    allowed_dosen = allowed_dosen or set()

    for _, row in df.iterrows():
        kode_mk = clean_code(row["Kode MK"])
        raw_dosen = clean_text(row["Nama Dosen"])
        norm_dosen = normalize_name(raw_dosen)

        official_dosen = official_name_by_norm.get(norm_dosen, raw_dosen)

        # Jika master menyediakan allowed_dosen, filter kandidat yang tidak boleh dijadwalkan.
        if allowed_dosen and official_dosen not in allowed_dosen:
            continue

        try:
            prioritas = int(row["Prioritas"])
        except Exception:
            prioritas = 99

        role = clean_text(row.get("Berminat", ""))

        if kode_mk not in candidates_dict:
            candidates_dict[kode_mk] = []

        if official_dosen not in candidates_dict[kode_mk]:
            candidates_dict[kode_mk].append(official_dosen)

        pref_info[(official_dosen, kode_mk)] = {
            "prioritas": prioritas,
            "role": role,
        }

    return candidates_dict, pref_info


# ============================================================
# 4. PEMILIHAN DOSEN AWAL
# ============================================================

def build_dosen_picker(candidates_dict, pref_info, dosen_hierarchy, allowed_dosen, fairness_dosen):
    """
    Menghasilkan fungsi get_best_dosen(kode_mk, sks_mk, mk_hierarchy)
    untuk assignment awal kelas.

    Catatan desain:
    - Kandidat preferensi boleh berasal dari dosen lintas departemen selama Boleh Dijadwalkan = Ya.
    - Fallback hierarki dibatasi ke dosen yang masuk fairness_dosen agar dosen lintas departemen
      tidak menjadi target fallback umum tanpa preferensi eksplisit.
    """
    workload_tracker = {}

    def workload_of(dosen):
        return workload_tracker.get(dosen, 0)

    def add_workload(dosen, sks):
        workload_tracker[dosen] = workload_tracker.get(dosen, 0) + sks

    def get_best_dosen(kode_mk, sks_mk, mk_h):
        candidates = list(candidates_dict.get(kode_mk, []))
        random.shuffle(candidates)

        # 1. Kandidat preferensi: gunakan prioritas asli.
        for dosen in candidates:
            if dosen not in allowed_dosen:
                continue

            if workload_of(dosen) + sks_mk <= 10:
                add_workload(dosen, sks_mk)
                prio = pref_info.get((dosen, kode_mk), {}).get("prioritas", 1)
                return dosen, prio, "Sesuai Preferensi"

        # 2. Fallback hierarki: hanya dosen yang dihitung fairness agar redistribusi internal tidak bias.
        if mk_h:
            hierarchy_candidates = list(fairness_dosen)
            random.shuffle(hierarchy_candidates)

            # P2 Ranting
            for dosen in hierarchy_candidates:
                d_h = dosen_hierarchy.get(normalize_name(dosen), {})
                if workload_of(dosen) + sks_mk <= 12:
                    if (
                        is_known_hierarchy_value(d_h.get("ranting"))
                        and is_known_hierarchy_value(mk_h.get("ranting"))
                        and clean_text(d_h.get("ranting")).lower() == clean_text(mk_h.get("ranting")).lower()
                    ):
                        add_workload(dosen, sks_mk)
                        return dosen, 2, "Kecocokan Ranting Ilmu"

            # P3 Cabang
            for dosen in hierarchy_candidates:
                d_h = dosen_hierarchy.get(normalize_name(dosen), {})
                if workload_of(dosen) + sks_mk <= 12:
                    if (
                        is_known_hierarchy_value(d_h.get("cabang"))
                        and is_known_hierarchy_value(mk_h.get("cabang"))
                        and clean_text(d_h.get("cabang")).lower() == clean_text(mk_h.get("cabang")).lower()
                    ):
                        add_workload(dosen, sks_mk)
                        return dosen, 3, "Kecocokan Cabang Ilmu"

            # P4 Bidang
            for dosen in hierarchy_candidates:
                d_h = dosen_hierarchy.get(normalize_name(dosen), {})
                if workload_of(dosen) + sks_mk <= 12:
                    if (
                        is_known_hierarchy_value(d_h.get("bidang"))
                        and is_known_hierarchy_value(mk_h.get("bidang"))
                        and clean_text(d_h.get("bidang")).lower() == clean_text(mk_h.get("bidang")).lower()
                    ):
                        add_workload(dosen, sks_mk)
                        return dosen, 4, "Kecocokan Bidang Ilmu"

        # 3. Last resort: kandidat preferensi walaupun melewati cap.
        if candidates:
            for dosen in candidates:
                if dosen in allowed_dosen:
                    add_workload(dosen, sks_mk)
                    prio = pref_info.get((dosen, kode_mk), {}).get("prioritas", 1)
                    return dosen, prio, "Sesuai Preferensi (Overload)"

        return "Unknown Dosen", 99, "Inisialisasi Awal"

    return get_best_dosen


# ============================================================
# 5. GENERATOR CLASS OBJECT DARI KONFIGURASI PEMBUKAAN KELAS
# ============================================================

def split_sks(sks_total):
    if sks_total == 4:
        return [2, 2]
    if sks_total == 5:
        return [3, 2]
    if sks_total == 6:
        return [3, 3]
    return [sks_total]


def create_class_objects_from_config(
    kode,
    nama_mk,
    sks_total,
    semester_kurikulum,
    jenis_mk,
    parallel,
    assigned_dosen_name,
    priority,
    metode,
    jumlah_mhs_per_kelas,
    estimasi_peserta,
    jumlah_kelas_final,
    counter,
):
    sks_parts = split_sks(sks_total)
    new_classes = []

    for i, sks_part in enumerate(sks_parts):
        part_suffix = f" (Sesi {i + 1})" if len(sks_parts) > 1 else ""

        obj = {
            "class_id": counter + i,
            "kode_mk": kode,
            "nama_mk": nama_mk + part_suffix,
            "sks": sks_part,
            "sks_asli": sks_total,
            "dosen": assigned_dosen_name,
            "dosen_priority": priority,
            "metode_pemilihan": metode,
            "jumlah_mhs": jumlah_mhs_per_kelas,
            "estimasi_peserta_mk": estimasi_peserta,
            "jumlah_kelas_final_mk": jumlah_kelas_final,
            "jenis_mk": jenis_mk,
            "semester": semester_kurikulum,
            "parallel": parallel,
            "is_split": len(sks_parts) > 1,
        }

        new_classes.append(obj)

    return new_classes, counter + len(new_classes)


def load_mk_active_from_config(
    class_config_path,
    course_map,
    candidates_dict,
    pref_info,
    dosen_hierarchy,
    allowed_dosen,
    fairness_dosen,
    semester_active="Ganjil",
):
    """
    Membentuk daftar kelas berdasarkan Jumlah Kelas Final dari Konfigurasi Pembukaan Kelas.
    """
    df_config = normalize_columns(pd.read_csv(class_config_path))

    required_cols = [
        "Kode MK", "Jenis MK", "Semester Aktif", "Status Dibuka",
        "Estimasi Peserta", "Jumlah Kelas Final"
    ]

    missing = [c for c in required_cols if c not in df_config.columns]
    if missing:
        raise ValueError(f"Kolom wajib tidak ditemukan pada konfigurasi pembukaan kelas: {missing}")

    classes = []
    counter = 0

    picker = build_dosen_picker(
        candidates_dict=candidates_dict,
        pref_info=pref_info,
        dosen_hierarchy=dosen_hierarchy,
        allowed_dosen=allowed_dosen,
        fairness_dosen=fairness_dosen,
    )

    # Hanya semester aktif dan kelas yang dibuka
    df_config = df_config[
        (df_config["Semester Aktif"].astype(str).str.strip().str.lower() == semester_active.lower())
        & (df_config["Status Dibuka"].astype(str).str.strip().str.lower() == "ya")
    ].copy()

    df_config["Jumlah Kelas Final"] = df_config["Jumlah Kelas Final"].fillna(0).astype(int)
    df_config["Estimasi Peserta"] = df_config["Estimasi Peserta"].fillna(0).astype(int)

    df_config = df_config[df_config["Jumlah Kelas Final"] > 0]

    for _, cfg in df_config.iterrows():
        kode = clean_code(cfg["Kode MK"])

        if kode not in course_map:
            raise ValueError(f"Kode MK {kode} pada konfigurasi tidak ditemukan di master MK.")

        course = course_map[kode]

        sks_total = int(course["sks"])
        nama_mk = course["nama_mk"]
        jenis_mk = clean_text(cfg.get("Jenis MK", course["jenis_mk"]))
        semester_kurikulum = clean_text(cfg.get("Semester Kurikulum", course["semester_kurikulum"]))

        jumlah_kelas_final = int(cfg["Jumlah Kelas Final"])
        estimasi_peserta = int(cfg["Estimasi Peserta"])

        # Kapasitas per kelas secara estimasi. Ini membuat constraint kapasitas tetap bermakna.
        jumlah_mhs_per_kelas = math.ceil(estimasi_peserta / jumlah_kelas_final) if jumlah_kelas_final > 0 else 0

        mk_h = {
            "bidang": course.get("bidang", ""),
            "cabang": course.get("cabang", ""),
            "ranting": course.get("ranting", ""),
        }

        for class_index in range(jumlah_kelas_final):
            suffix = get_course_suffix(class_index)

            assigned_dosen, prio, metode = picker(kode, sks_total, mk_h)

            new_objs, counter = create_class_objects_from_config(
                kode=kode,
                nama_mk=nama_mk,
                sks_total=sks_total,
                semester_kurikulum=semester_kurikulum,
                jenis_mk=jenis_mk,
                parallel=suffix,
                assigned_dosen_name=assigned_dosen,
                priority=prio,
                metode=metode,
                jumlah_mhs_per_kelas=jumlah_mhs_per_kelas,
                estimasi_peserta=estimasi_peserta,
                jumlah_kelas_final=jumlah_kelas_final,
                counter=counter,
            )

            classes.extend(new_objs)

    return classes, df_config


# ============================================================
# 6. FUNGSI UTAMA
# ============================================================

def load_all_data(
    data_dir,
    semester_active="Ganjil",
    class_config_path=None,
    room_capacity_default=40,
):
    print(f"\n[Data Loader] Loading Semester: {semester_active}")

    data_dir = os.path.abspath(data_dir)

    if class_config_path is None:
        class_config_path = os.path.join(
            data_dir,
            f"Konfigurasi_Pembukaan_Kelas_{semester_active}.csv"
        )

    slots = load_time_slots(os.path.join(data_dir, "Time_Slots v2.csv"))
    rooms = load_rooms(os.path.join(data_dir, "Ruang Kelas.csv"))

    file_mk_wajib = os.path.join(data_dir, "MK Wajib TIF_All Semester_Mapped_v3.csv")
    file_mk_pilihan = os.path.join(data_dir, "MK Pilihan TIF_All Semester_Mapped_v3.csv")
    file_preferensi = os.path.join(data_dir, "Preferensi MK dosen TIFv2.csv")
    file_master_dosen = os.path.join(data_dir, "Master Data Dosen Pengampu.csv")

    if not os.path.exists(file_master_dosen):
        # Fallback untuk kompatibilitas lama, tetapi sebaiknya tidak dipakai lagi.
        file_master_dosen = os.path.join(data_dir, "Master Data Dosen DTIF.csv")

    if not os.path.exists(class_config_path):
        raise FileNotFoundError(
            f"File konfigurasi pembukaan kelas tidak ditemukan: {class_config_path}"
        )

    course_map, mk_hierarchy = load_master_courses(file_mk_wajib, file_mk_pilihan)

    dosen_hierarchy, official_name_by_norm, allowed_dosen, fairness_dosen = load_pengampu_data(
        file_master_dosen
    )

    candidates, pref_info = load_preference_data(
        file_preferensi,
        official_name_by_norm=official_name_by_norm,
        allowed_dosen=allowed_dosen,
    )

    classes, opening_config = load_mk_active_from_config(
        class_config_path=class_config_path,
        course_map=course_map,
        candidates_dict=candidates,
        pref_info=pref_info,
        dosen_hierarchy=dosen_hierarchy,
        allowed_dosen=allowed_dosen,
        fairness_dosen=fairness_dosen,
        semester_active=semester_active,
    )

    print(f"[Data Loader] Total MK dibuka: {opening_config['Kode MK'].nunique()}")
    print(f"[Data Loader] Total kelas paralel: {int(opening_config['Jumlah Kelas Final'].sum())}")
    print(f"[Data Loader] Total sesi perkuliahan: {len(classes)}")

    return {
        "slots": slots,
        "rooms": rooms,
        "classes": classes,
        "candidates": candidates,
        "pref_info": pref_info,
        "mk_hierarchy": mk_hierarchy,
        "dosen_hierarchy": dosen_hierarchy,
        "allowed_dosen": allowed_dosen,
        "fairness_dosen": fairness_dosen,
        "opening_config": opening_config.to_dict(orient="records"),
        "class_config_path": class_config_path,
    }


# ============================================================
# 7. EXPORT DEBUG
# ============================================================

def save_results_to_csv(data_result, output_folder="hasil_output"):
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_folder)
    os.makedirs(output_path, exist_ok=True)

    if "classes" in data_result:
        df_classes = pd.DataFrame(data_result["classes"])

        if not df_classes.empty:
            df_classes = df_classes.sort_values(
                by=["semester", "kode_mk", "parallel", "class_id"],
                kind="stable"
            )

        file_name = os.path.join(output_path, "1_final_classes_generated.csv")
        df_classes.to_csv(file_name, index=False)
        print(f"✅ [CSV] Data kelas berhasil disimpan di: {file_name}")

    if "opening_config" in data_result:
        file_name = os.path.join(output_path, "0_opening_config_used.csv")
        pd.DataFrame(data_result["opening_config"]).to_csv(file_name, index=False)
        print(f"✅ [CSV] Konfigurasi pembukaan kelas tersimpan di: {file_name}")

    if "slots" in data_result:
        pd.DataFrame(data_result["slots"]).to_csv(
            os.path.join(output_path, "2_debug_slots.csv"),
            index=False
        )

    if "rooms" in data_result:
        pd.DataFrame(data_result["rooms"]).to_csv(
            os.path.join(output_path, "3_debug_rooms.csv"),
            index=False
        )


if __name__ == "__main__":
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(CURRENT_DIR, "..", "data_input")

    result = load_all_data(
        DATA_DIR,
        semester_active="Ganjil",
        class_config_path=os.path.join(DATA_DIR, "Konfigurasi_Pembukaan_Kelas_Ganjil.csv"),
    )

    save_results_to_csv(result)
