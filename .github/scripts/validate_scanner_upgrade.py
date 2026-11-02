"""One reviewed scanner-authority transition; ordinary PRs remain frozen."""
import hashlib, json, os, subprocess

REPOSITORY = 'appolon1908/Mobile-Control-Server'
BASE = 'c54bdbd111a6fcd8bde12d94abc62a1b4a42301f'
EXPECTED = {'.github/scripts/validate_source_scope.py': '705d8a6d821216b86b2ff911f45f3f4f8f67e586954fa7d852cd25e8bd25f1e5', '.github/source-scope.json': '56acbe0f8d5cd53f7d8b950bd38a896dbebbb87c136fe811c833d9e25abb8e78', 'governance/interim-release-policy.json': '481af7ec7819de7ada883f8d517bf7d9da08128bcf26d47f4d3a12149458a521', '.github/scripts/test_source_scope.py': '19219d4715baaa55150ffa279bef50c1d16895aa7e5103f7d7853cebc9ae3f7f', '.github/scripts/test_secret_scanner.sh': '4d783f4f8ea40ec7acdbb94c4732f0ec2f9b320cea1e6a408a6702f08ee2d016'}
OLD_CONTEXT = 'documentation-contract-source'
NEW_CONTEXT = 'documentation-contract-source-v2'
EXTERNAL_REVIEW_FILES = {'.github/workflows/source-scope.yml', '.github/scripts/validate_scanner_upgrade.py'}

def trusted_manifest(base, repository):
    if base != BASE or repository != REPOSITORY:
        raise ValueError('Unregistered scanner authority transition')
    changes = subprocess.check_output(['git', 'diff', '--raw', '--no-abbrev', '--no-renames', base, 'HEAD']).decode().splitlines()
    changed = set()
    for entry in changes:
        metadata, path = entry.split('\t', 1)
        old_mode, new_mode, old_blob, new_blob, status = metadata[1:].split()
        if path not in set(EXPECTED) | EXTERNAL_REVIEW_FILES or new_mode != '100644' or status not in ('A', 'M'):
            raise ValueError('Unreviewed source, authority, mode or path change: ' + path)
        changed.add(path)
        if path in EXPECTED:
            content = subprocess.check_output(['git', 'show', 'HEAD:' + path])
            if hashlib.sha256(content).hexdigest() != EXPECTED[path]:
                raise ValueError('Reviewed scanner delta changed: ' + path)
    if changed != set(EXPECTED) | EXTERNAL_REVIEW_FILES:
        raise ValueError('Scanner upgrade delta incomplete')
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal']).strip():
        raise ValueError('Dirty or untracked scanner upgrade source')
    manifest = json.loads(subprocess.check_output(['git', 'show', base + ':.github/source-scope.json']))
    policy = manifest['structured_files']['governance/interim-release-policy.json']
    found = 0
    for check in policy['required_checks']:
        if check['context'] == OLD_CONTEXT:
            check['context'] = NEW_CONTEXT
            found += 1
    if found != 1:
        raise ValueError('Unexpected prior scope policy')
    return manifest

if __name__ == '__main__':
    trusted_manifest(os.environ['BASE_SHA'], os.environ['GITHUB_REPOSITORY'])
    print('Exact reviewed scanner-only authority transition PASS; product source unchanged')
