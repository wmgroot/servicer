import sys
from .run import run

def diff(a, b=None, name_only=True):
    command = 'git diff %s' % a
    if b:
        command = '%s..%s' % (command, b)
    if name_only:
        command = '%s --name-only' % command

    result = run(command)

    if name_only:
        return [f for f in result['stdout'].split('\n') if len(f) > 0]

    return result['stdout']

def tag(tag, message=None, push=False):
    command = 'git tag'
    if message:
        command = '%s -a %s -m "%s"' % (command, tag, message)
    else:
        command = '%s %s' % (command, tag)

    run(command)

    if push:
        run('git push origin %s' % tag)

def list_tags():
    result = run('git tag')
    return result['stdout'].split('\n')

def sanitize_tag(tag):
    for ch in '/ [ ]'.split():
        tag.replace(ch, '.')
    return tag
