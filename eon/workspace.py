"""Local library metadata, stored inside the same encrypted envelope as chats."""
import secrets

MODES = {
    "general": {"name": "Genel Asistan", "instructions": "Doğrudan ve dengeli yanıt ver."},
    "code": {"name": "Kodlama", "instructions": "Çalışabilir küçük örnekler ver. Varsayımları ve sınır durumlarını belirt."},
    "study": {"name": "Ders Çalışma", "instructions": "Kavramı adım adım öğret. Anlamayı kısa bir soruyla kontrol et."},
    "write": {"name": "Yazı Yardımcısı", "instructions": "Anlamı ve yazarın sesini koru. Akıcılık ve açıklığı geliştir."},
}
DEFAULT_LOOK = {"theme": "dark", "accent": "ice", "compact": False, "reduced": False}


def check_text(value, limit, required=True):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ValueError("Alan boş veya uzunluk sınırını aşıyor.")
    return value.strip()


def fold(value):
    return value.casefold().replace("i\u0307", "i").replace("ı", "i")


class Workspace:
    def __init__(self):
        self.projects = {}
        self.custom_modes = {}
        self.look = DEFAULT_LOOK.copy()

    def dump(self):
        return {"projects": self.projects, "custom_modes": self.custom_modes, "look": self.look}

    def restore(self, data):
        for key, records in (("projects", self.projects), ("custom_modes", self.custom_modes)):
            source = data[key]
            if not isinstance(source, dict) or len(source) > 64:
                raise ValueError("Koleksiyon geçersiz.")
            for ident, entry in source.items():
                if ident in MODES or not check_text(ident, 64):
                    raise ValueError("Kayıt kimliği geçersiz.")
                records[ident] = self.record(entry)
        self.appearance(data["look"])

    def appearance(self, data):
        if (not isinstance(data, dict) or data.get("theme") not in ("dark", "light")
                or data.get("accent") not in ("ice", "mint", "violet")
                or any(type(data.get(k)) != bool for k in ("compact", "reduced"))):
            raise ValueError("Görünüm seçimi geçersiz.")
        self.look = {k: data[k] for k in DEFAULT_LOOK}

    @staticmethod
    def record(data):
        if not isinstance(data, dict):
            raise ValueError("Kayıt geçersiz.")
        return {"name": check_text(data.get("name"), 64),
                "instructions": check_text(data.get("instructions"), 480, False)}

    def update(self, kind, data, items):
        records = self.projects if kind == "project" else self.custom_modes
        ident = data.get("id", "")
        if not isinstance(ident, str) or (ident and ident not in records):
            raise ValueError("Kayıt bulunamadı.")
        if data.get("delete") is True:
            if not ident:
                raise ValueError("Silinecek kaydı seç.")
            del records[ident]
            field, default = ("project", "") if kind == "project" else ("mode", "general")
            for item in items.values():
                if item[field] == ident:
                    item[field] = default
            return
        record = self.record(data)
        if not ident and len(records) >= 64:
            raise ValueError("Kayıt sınırına ulaşıldı.")
        records[ident or secrets.token_hex(8)] = record

    def modes(self):
        return {**MODES, **self.custom_modes}

    def configure(self, item, project, mode):
        if not isinstance(project, str) or (project and project not in self.projects):
            raise ValueError("Proje bulunamadı.")
        if not isinstance(mode, str) or mode not in self.modes():
            raise ValueError("Mod bulunamadı.")
        item.update(project=project, mode=mode)

    def guidance(self, item):
        mode = self.modes()[item["mode"]]["instructions"]
        project = self.projects.get(item["project"], {}).get("instructions", "")
        return "\n".join(s for s in (mode, project) if s)
