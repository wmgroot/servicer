import sys
from .run import run

class Git():
    def __init__(self, hide_output=True):
        self.run = run
        self.hide_output = hide_output

    def files_changed_ahead_of_ref(self, ref):
        forward_commits = self.commits_against_ref(ref, commit_type='+')
        files_changed = set()
        for c in forward_commits:
            files_changed.update(self.diff(a='%s~' % c, b=c))
        return sorted(list(files_changed))

    def commits_against_ref(self, ref, commit_type='', hide_output=None):
        result = self.run('git cherry %s' % ref, hide_output=hide_output or self.hide_output)

        commits = result['stdout'].split('\n')
        return [c[2:] for c in commits if c and c.startswith(commit_type)]

    def diff(self, a, b=None, name_only=True, hide_output=None):
        command = 'git diff %s' % a
        if b:
            command = '%s..%s' % (command, b)
        if name_only:
            command = '%s --name-only' % command

        result = self.run(command, hide_output=hide_output or self.hide_output)

        if name_only:
            return [f for f in result['stdout'].split('\n') if len(f) > 0]

        return result['stdout']

    def tag(self, tag, message=None, push=False, hide_output=None):
        command = 'git tag'
        if message:
            command = '%s -a %s -m "%s"' % (command, tag, message)
        else:
            command = '%s %s' % (command, tag)

        self.run(command, hide_output=hide_output or self.hide_output)

        if push:
            self.run('git push origin %s' % tag)

    def list_tags(self):
        result = self.run('git tag')
        return result['stdout'].split('\n')

    def sanitize_tag(self, tag):
        for ch in '/ [ ]'.split():
            tag.replace(ch, '.')
        return tag
