#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil
from pathlib import Path

ROOT = Path('/home/solpi/work/blog-automation')
NAMI_ROOT = Path('/home/solpi/work/agents/agent3-nami/data/handoff')


def cp(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-id', required=True)
    args = ap.parse_args()
    run_id = args.run_id

    src_dir = NAMI_ROOT / run_id
    dst_dir = ROOT / 'data' / 'handoff' / run_id
    if not src_dir.exists():
        raise SystemExit(f'missing nami handoff dir: {src_dir}')

    src_nami = src_dir / 'nami_to_zoro.json'
    if not src_nami.exists():
        raise SystemExit(f'missing file: {src_nami}')
    cp(src_nami, dst_dir / 'nami_to_zoro.json')

    obj = json.loads(src_nami.read_text(encoding='utf-8'))
    copied = [str((dst_dir / 'nami_to_zoro.json').relative_to(ROOT))]

    for d in obj.get('drafts', []):
        for key in ('wp_ready_path', 'markdown_path', 'image_manifest'):
            p = d.get(key)
            if not p:
                continue
            s = src_dir / Path(p).relative_to(Path('data/handoff') / run_id)
            t = dst_dir / Path(p).relative_to(Path('data/handoff') / run_id)
            if s.exists():
                cp(s, t)
                copied.append(str(t.relative_to(ROOT)))

                if key == 'image_manifest':
                    man = json.loads(s.read_text(encoding='utf-8'))
                    for im in man.get('images', []):
                        lp = im.get('local_path')
                        if not lp:
                            continue
                        img_s = src_dir / Path(lp).relative_to(Path('data/handoff') / run_id)
                        img_t = dst_dir / Path(lp).relative_to(Path('data/handoff') / run_id)
                        if img_s.exists():
                            cp(img_s, img_t)
                            copied.append(str(img_t.relative_to(ROOT)))

    print(json.dumps({'ok': True, 'run_id': run_id, 'copied_count': len(copied), 'sample': copied[:8]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
