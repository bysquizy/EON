"""Optional local-only smoke evaluation. Uses synthetic, in-memory chats."""
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eon.service import EonService


def main():
    service = EonService()
    service.select_length("kisa")
    cases = [
        ("Yalnız sonuçtaki sayıyı yaz. 17 çarpı 3 kaçtır?", "51"),
        ("Reply with just the capital of France.", "paris"),
        ("Sadece şu sözcüğü tekrarla: merhaba", "merhaba"),
        ("Return only the sum of 19 and 8.", "27"),
    ]
    passed = 0
    for prompt, expected in cases:
        service.new_chat()
        started = time.perf_counter()
        arrivals = []
        result = service.generate(text=prompt, emit=lambda _: arrivals.append(time.perf_counter()))
        answer = result["message"].strip().casefold().strip(" .!*")
        correct = answer == expected
        passed += correct
        print(f"{'PASS' if correct else 'MISS'} first={arrivals[0]-started:.2f}s total={arrivals[-1]-started:.2f}s")
    print(f"{passed}/{len(cases)} exact matches")
    return int(passed != len(cases))


if __name__ == "__main__":
    sys.exit(main())
