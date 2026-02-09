from dataclasses import dataclass

from otstack.Branch import Branch
from otstack.PullRequest import PullRequest


@dataclass
class MockPullRequest(PullRequest):
    title: str
    description: str | None
    source_branch: Branch
    destination_branch: Branch
    url: str

    def change_destination(self, new_destination: Branch) -> None:
        self.destination_branch = new_destination

    def get_branch(self) -> Branch:
        return self.source_branch

    def is_local(self) -> bool:
        return self.source_branch.is_local() and self.destination_branch.is_local()

    def sync(self) -> bool:
        if not self.is_local():
            raise ValueError("sync() requires is_local() to return True, but it returned False")
        self.destination_branch.pull()
        if not self.source_branch.merge(self.destination_branch):
            return False
        self.source_branch.push()
        return True
