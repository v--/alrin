from collections.abc import Sequence

import pygit2


def git_commit(repo: pygit2.Repository, message: str, parents: Sequence[pygit2.Oid] = []) -> pygit2.Oid:
    ref = repo.index.write_tree()
    author = pygit2.Signature('Test author', 'author@test.test')
    committer = pygit2.Signature('Test committer', 'committer@test.test')

    return repo.create_commit('HEAD', author, committer, message, ref, parents)
