# Workflow digest contract

Project Krypton exposes two deliberately different identities for the synthetic C0
workflow.

The workflow_digest field is the portable semantic digest. It hashes canonical JSON
for the complete workflow result after excluding only the execution provenance object
and the consequence's derived provenance_reference. It retains the edit, evidence,
KEG, mapping, model contract, pair specification, outputs, units, applicability, and
all other scientific/software-semantic fields. Identical semantic inputs therefore
have the same digest across an editable checkout, an installed wheel, Windows, and
Linux.

The execution_digest field is the existing provenance-aware
C0MockWorkflowResult.digest(). It hashes the complete canonical result, including Git
commit, dirty-worktree state, Python version, dependency-lock digest, timestamp,
environment digest, and the linked provenance reference. It is expected to differ
when execution provenance differs.

The historical digest
65463be3bbf2709324c6ebeeeebe7915776232a882ffdcc809e05bb8455b4bfc remains
historical Task-3-through-Task-7A execution evidence. It is not relabeled as a portable
digest. The portable semantic digest introduced by Task 7A-R is
a2784df7b4f5d0e559e20d9e299f81859825557c42ac9a8e0c9d4059a811eee9.
