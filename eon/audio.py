"""Windows master volume control through the Core Audio COM API (ctypes, no extra packages).

Calls are in-process and take a few milliseconds. Other platforms report "unsupported".
"""
from __future__ import annotations

import ctypes
import sys
import threading
import uuid


class AudioError(ValueError):
    pass


class _GUID(ctypes.Structure):
    _fields_ = [("a", ctypes.c_uint32), ("b", ctypes.c_uint16), ("c", ctypes.c_uint16), ("d", ctypes.c_ubyte * 8)]


def _guid(text: str) -> _GUID:
    u = uuid.UUID(text)
    g = _GUID(u.time_low, u.time_mid, u.time_hi_version)
    for i, byte in enumerate(bytes([u.clock_seq_hi_variant, u.clock_seq_low]) + u.node.to_bytes(6, "big")):
        g.d[i] = byte
    return g


_CLSID_ENUM = "BCDE0395-E52F-467C-8E3D-C4579291692E"
_IID_ENUM = "A95664D2-9614-4F35-A746-DE8DB63617E6"
_IID_VOLUME = "5CDF2C82-841E-4546-9722-0CF74078229A"
_local = threading.local()


def supported() -> bool:
    return sys.platform == "win32"


def _call(obj, index, argtypes, *args):
    table = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    prototype = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes)
    return prototype(table[index])(obj, *args)


def _release(obj) -> None:
    if obj and obj.value:
        _call(obj, 2, [])


class _Endpoint:
    def __enter__(self):
        if not supported():
            raise AudioError("Ses denetimi yalnızca Windows'ta kullanılabilir.")
        if not getattr(_local, "ready", False):
            ctypes.windll.ole32.CoInitializeEx(None, 0)
            _local.ready = True
        enum = ctypes.c_void_p()
        clsid, iid = _guid(_CLSID_ENUM), _guid(_IID_ENUM)
        if ctypes.windll.ole32.CoCreateInstance(ctypes.byref(clsid), None, 23, ctypes.byref(iid), ctypes.byref(enum)) != 0:
            raise AudioError("Ses aygıtı hizmetine ulaşılamadı.")
        device = ctypes.c_void_p()
        try:
            if _call(enum, 4, [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)], 0, 1, ctypes.byref(device)) != 0:
                raise AudioError("Etkin bir ses çıkış aygıtı bulunamadı.")
            self.volume = ctypes.c_void_p()
            vol_iid = _guid(_IID_VOLUME)
            if _call(device, 3, [ctypes.POINTER(_GUID), ctypes.c_ulong, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)],
                     ctypes.byref(vol_iid), 23, None, ctypes.byref(self.volume)) != 0:
                raise AudioError("Ses düzeyi denetimi açılamadı.")
        finally:
            _release(device)
            _release(enum)
        return self

    def __exit__(self, *exc):
        _release(self.volume)


def get_state() -> dict:
    with _Endpoint() as ep:
        level, muted = ctypes.c_float(), ctypes.c_int()
        _call(ep.volume, 9, [ctypes.POINTER(ctypes.c_float)], ctypes.byref(level))
        _call(ep.volume, 15, [ctypes.POINTER(ctypes.c_int)], ctypes.byref(muted))
        return {"supported": True, "level": int(round(level.value * 100)), "muted": bool(muted.value)}


def set_level(percent: int) -> dict:
    if type(percent) is not int or not 0 <= percent <= 100:
        raise AudioError("Ses düzeyi 0 ile 100 arasında bir tam sayı olmalı.")
    with _Endpoint() as ep:
        if _call(ep.volume, 7, [ctypes.c_float, ctypes.c_void_p], percent / 100.0, None) != 0:
            raise AudioError("Ses düzeyi ayarlanamadı.")
    return get_state()


def set_mute(muted: bool) -> dict:
    if type(muted) is not bool:
        raise AudioError("Sessiz modu değeri geçersiz.")
    with _Endpoint() as ep:
        if _call(ep.volume, 14, [ctypes.c_int, ctypes.c_void_p], int(muted), None) != 0:
            raise AudioError("Sessiz modu ayarlanamadı.")
    return get_state()
