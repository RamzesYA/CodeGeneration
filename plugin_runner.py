#!/usr/bin/env python3
"""Run generators non-interactively using generated JSON and plugin choices.

Usage:
  python plugin_runner.py --input input.json --diagram-type classes --languages python,java

It will write outputs into `puml_server/storage/plugin_runs/<job_id>/` and print generated files to console.
"""
import argparse
import json
import uuid
import traceback
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
STORAGE = ROOT / 'puml_server' / 'storage' / 'plugin_runs'
STORAGE.mkdir(parents=True, exist_ok=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', '-i', help='Path to generated JSON (or - for stdin)', required=True)
    parser.add_argument('--diagram-type', '-t', choices=['classes','database','deployment'], help='Diagram type from plugin', required=True)
    parser.add_argument('--languages', '-l', help='Comma-separated languages (can be multiple). For classes: python,cpp,java. For DB: postgresql,mysql,oracle. For deployment: ignored', default='')
    parser.add_argument('--no-validate', action='store_true', help='Disable code validation')
    args = parser.parse_args()

    try:
        if args.input == '-':
            raw = Path('stdin_input.json')
            data = json.load(__import__('sys').stdin)
            raw.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            input_path = raw
        else:
            input_path = Path(args.input)
            if not input_path.exists():
                print('Input file not found:', input_path)
                return
            data = json.loads(input_path.read_text(encoding='utf-8'))

        langs = [x.strip().lower() for x in args.languages.split(',') if x.strip()]

        # create job dir
        job_id = uuid.uuid4().hex
        job_dir = STORAGE / job_id
        job_dir.mkdir(parents=True)
        # copy input JSON
        in_copy = job_dir / 'input.json'
        shutil.copyfile(str(input_path), str(in_copy))

        # import generator helpers from main
        from main import detect_generator_from_data

        results = []

        # Helper to run one generator instance
        def run_for_language(prefer_lang=None, db_type=None):
            gen = detect_generator_from_data(data, prefer_language=(prefer_lang or None), validate_code=not args.no_validate, db_type=db_type)
            # ensure generator reads our input copy
            gen.file_path = in_copy
            # choose sensible output filename inside job_dir
            try:
                out_name = Path(gen.output_file).name
            except Exception:
                out_name = f'output_{uuid.uuid4().hex[:6]}.txt'
            gen.output_file = job_dir / out_name
            print(f'Running generator: {gen.__class__.__name__} -> {gen.output_file}')
            gen.generate()
            if gen.output_file.exists():
                content = gen.output_file.read_text(encoding='utf-8')
            else:
                content = ''
            results.append({'generator': gen.__class__.__name__, 'file': str(gen.output_file), 'content': content})

        if args.diagram_type == 'deployment':
            run_for_language()
        elif args.diagram_type == 'classes':
            if not langs:
                # default to python
                langs = ['python']
            for l in langs:
                if l not in ('python','java','cpp'):
                    print('Skipping unknown classes language:', l)
                    continue
                run_for_language(prefer_lang=l)
        elif args.diagram_type == 'database':
            if not langs:
                langs = ['postgresql']
            for l in langs:
                if l not in ('postgresql','mysql','oracle'):
                    print('Skipping unknown database type:', l)
                    continue
                run_for_language(db_type=l)

        # write summary
        summary = {'job_id': job_id, 'generated': [{'generator': r['generator'], 'file': r['file']} for r in results]}
        (job_dir / 'result.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

        # Print results to console
        print('\n=== Generation summary ===')
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        for r in results:
            print('\n--- File:', r['file'], '---')
            print(r['content'][:10000])

        print(f'All outputs saved to: {job_dir}')

    except Exception as e:
        print('Error during generation:')
        traceback.print_exc()


if __name__ == '__main__':
    main()
