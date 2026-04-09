"""
Interactive scanner demo.

Run:
    python scan_demo.py

Then type any Nepali or English sentence and press Enter.
Type 'exit' or 'quit' to stop.

Examples to try:
    वर्षको पहिलो महिना मा मेरो बैठक छ
    गत हप्ता बैठक भयो र अर्को महिना फेरि हुन्छ
    ३ दिन अगाडि
    3 days ago
    आजको तारिख सम्ममा बुझाउने
    यो हप्ता वसुली गर्ने
    मेरो account renew gardinus यो महिनाको अन्त्य तारिखसम्म मा
    हरेक हप्ता जाने
    परसि आउनुस्
    पर्सि आउनुस्
"""
import json
import sys
from library.scanner import scan_text


def main():
    print("=" * 60)
    print("  NepDateScan Interactive Demo")
    print("  Type a Nepali/English sentence and press Enter.")
    print("  Type 'exit' or 'quit' to stop.")
    print("=" * 60)
    print()

    while True:
        try:
            user_input = input(">> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if user_input.lower() in {"exit", "quit", "q"}:
            print("Bye!")
            break

        if not user_input:
            continue

        result = scan_text(user_input)

        print(f"\n  Original:   {result.original_text}")
        print(f"  Normalized: {result.normalized_text}")
        print(f"  Extractions ({len(result.extractions)}):")

        if not result.extractions:
            print("    (none)")
        else:
            print(json.dumps(result.extractions, indent=4, ensure_ascii=False))

        print()


if __name__ == "__main__":
    main()
