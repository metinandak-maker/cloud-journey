"""Command-line entry point using the same safety-checked engine as the GUI."""
from engine import run_council


def main():
    question = input('ASK THE COUNCIL:\n> ').strip()
    result = run_council(question)
    if 'error' in result:
        print(result['error'])
        return 1
    for section, text in result.items():
        print(f'\n{section.upper()}\n{text}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
