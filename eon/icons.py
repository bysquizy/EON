"""Read a small Windows executable icon as pixels, without starting the target."""
import base64
import ctypes as ct
from ctypes import wintypes as w
import os
from pathlib import Path
from .launcher import safe_launch_path


def windows_pixels(path):
    if os.name != "nt" or Path(path).suffix.lower() != ".exe":
        raise ValueError("Yerleşik simge için yerel bir EXE seç veya PNG ekle.")
    path = safe_launch_path(path)
    if ct.windll.kernel32.GetDriveTypeW(str(Path(path).anchor)) != 3:
        raise ValueError("Simge için sabit yerel disk gerekli.")
    shell, gdi, ui = ct.windll.shell32, ct.windll.gdi32, ct.windll.user32
    def api(lib, name, result, *args):
        fn = getattr(lib, name)
        fn.restype, fn.argtypes = result, args
        return fn
    handle = ct.c_void_p
    extract = api(shell, "ExtractIconExW", w.UINT, w.LPCWSTR, ct.c_int, ct.POINTER(handle), ct.POINTER(handle), w.UINT)
    icon = handle()
    if extract(path, 0, ct.byref(icon), None, 1) != 1 or not icon:
        raise ValueError("EXE içinde okunabilir simge bulunamadı.")
    dc = bitmap = previous = None
    try:
        dc = api(gdi,"CreateCompatibleDC",handle,handle)(None)
        if not dc:
            raise ValueError("Simge belleği açılamadı.")
        # BITMAPINFOHEADER followed by room for one RGBQUAD. A negative height is top-down.
        import struct
        header = ct.create_string_buffer(struct.pack("<IiiHHIIiiII",40,48,-48,1,32,0,9216,0,0,0,0)+bytes(4))
        pixels = handle()
        bitmap = api(gdi,"CreateDIBSection",handle,handle,handle,w.UINT,ct.POINTER(handle),handle,w.DWORD)(
            dc, header, 0, ct.byref(pixels), None, 0)
        if not bitmap or not pixels:
            raise ValueError("Simge belleği açılamadı.")
        select = api(gdi,"SelectObject",handle,handle,handle)
        previous = select(dc,bitmap)
        draw = api(ui,"DrawIconEx",w.BOOL,handle,ct.c_int,ct.c_int,handle,ct.c_int,ct.c_int,w.UINT,handle,w.UINT)
        if not previous or not draw(dc,0,0,icon,48,48,0,None,3):
            raise ValueError("Simge okunamadı.")
        gdi.GdiFlush()
        rgba = bytearray(ct.string_at(pixels, 9216))
        rgba[0::4], rgba[2::4] = rgba[2::4], rgba[0::4]
        if not any(rgba[3::4]):
            rgba[3::4] = bytes([255])*2304
        return base64.b64encode(rgba).decode("ascii")
    finally:
        if previous:
            select(dc,previous)
        if bitmap:
            api(gdi,"DeleteObject",w.BOOL,handle)(bitmap)
        if dc:
            api(gdi,"DeleteDC",w.BOOL,handle)(dc)
        api(ui,"DestroyIcon",w.BOOL,handle)(icon)
