from dataclasses import dataclass, field

from otstack.Branch import Branch


@dataclass
class MockBranch(Branch):
    name: str
    _merge_will_conflict: bool = field(default=False)
    _pull_has_new_commits: bool = field(default=False)
    _is_local: bool = field(default=False)
    _push_will_succeed: bool = field(default=True)
    push_called: bool = field(default=False)

    def merge(self, other_branch: Branch) -> bool:
        if self._merge_will_conflict:
            return False
        return True

    def pull(self) -> bool:
        return self._pull_has_new_commits

    def is_local(self) -> bool:
        return self._is_local

    def push(self) -> bool:
        self.push_called = True
        return self._push_will_succeed
