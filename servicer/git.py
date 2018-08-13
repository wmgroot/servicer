import sys
import os
from urllib.parse import quote_plus

from .run import run

class Git():
    def __init__(self, hide_output=True, protocol='ssh'):
        self.run = run
        self.hide_output = hide_output
        self.protocol = os.getenv('GIT_PROTOCOL', protocol)

    # deprecated, use diff with merge_base=True instead
    # def files_changed_ahead_of_ref(self, ref):
    #     forward_commits = self.commits_against_ref(ref, commit_type='+')
    #     files_changed = set()
    #     for c in forward_commits:
    #         files_changed.update(self.diff(a='%s~' % c, b=c, name_only=True))
    #     return sorted(list(files_changed))

    def authors_for_changes_ahead_of_ref(self, ref):
        forward_commits = self.commits_against_ref(ref, commit_type='+')
        authors = set()
        for c in forward_commits:
            authors.add(self.author_for_ref(c))
        return sorted(list(authors))

    def commits_against_ref(self, ref, commit_type='', hide_output=None):
        result = self.run('git cherry %s' % ref, hide_output=hide_output or self.hide_output)

        commits = result['stdout'].strip().split('\n')
        return [c[2:] for c in commits if c and c.startswith(commit_type)]

    def diff(self, a, b='HEAD', name_only=False, merge_base=False, hide_output=None):
        command = 'git diff %s' % a
        if merge_base:
            command = '%s...%s' % (command, b)
        else:
            command = '%s..%s' % (command, b)
        if name_only:
            command = '%s --name-only' % command

        result = self.run(command, hide_output=hide_output or self.hide_output)

        if name_only:
            return [f for f in result['stdout'].strip().split('\n') if len(f) > 0]

        return result['stdout'].strip()

    def tag(self, tag, message=None, push=False, hide_output=None):
        command = 'git tag'
        if message:
            command = '%s -a %s -m "%s"' % (command, tag, message)
        else:
            command = '%s %s' % (command, tag)

        self.run(command, hide_output=hide_output or self.hide_output)

        if push:
            self.push(ref=tag)

    def delete_tag(self, tags):
        if not isinstance(tags, list):
            tags = [tags]

        for tag in tags:
            self.run('git tag -d %s' % tag, check=False)
            self.push(ref=':refs/tags/%s' % tag)

    def list_tags(self):
        result = self.run('git tag')
        return result['stdout'].strip().split('\n')

    def sanitize_tag(self, tag):
        for ch in '/ [ ]'.split():
            tag.replace(ch, '.')
        return tag

    def set_config(self, config=None):
        for key, value in config.items():
            result = self.run('git config %s' % key)
            if not result['stdout'].strip():
                self.run('git config %s "%s"' % (key, value))

    def commit(self, add='.', message=None, check_commit=False):
        if not isinstance(add, list):
            add = [add]

        for a in add:
            self.run('git add %s' % a)

        self.run('git commit -m "%s"' % message, check=check_commit)

    def push(self, origin='origin', ref=None, local_ref=None, protocol=None, no_verify=False):
        if protocol == None:
            protocol = self.protocol

        command = 'git push'

        if local_ref:
            ref = '%s:%s' % (ref, local_ref)

        if no_verify:
            command = '%s --no-verify' % command

        if protocol == 'ssh':
            command = '%s %s %s' % (command, origin, ref)
        elif protocol == 'https':
            command = '%s https://%s:%s@%s %s' % (
                command,
                os.environ['GIT_USERNAME'],
                quote_plus(os.environ['GIT_PASSWORD']),
                os.environ['GIT_REPOSITORY'],
                ref,
            )
        else:
            raise ValueError('Invalid git push protocol: %s' % protocol)

        self.run(command)

    def current_branch(self):
        result = self.run('git rev-parse --abbrev-ref HEAD')
        return result['stdout'].strip()

    def author_for_ref(self, ref=None):
        command = 'git show --quiet --format="%an"'
        if ref:
            command = '%s %s' % (command, ref)

        result = self.run(command)
        return result['stdout'].strip()

    def fetch(self):
        command = 'git fetch'
        self.run(command)
