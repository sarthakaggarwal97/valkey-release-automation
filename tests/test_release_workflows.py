import unittest
from pathlib import Path

WORKFLOWS = Path(".github/workflows")


def workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


class ReleaseWorkflowCoverageTest(unittest.TestCase):
    def test_qualification_builds_every_non_publishing_family(self) -> None:
        text = workflow("qualify-release.yml")
        for contract in (
            "workflow_call:",
            "default: reusable",
            "source_sha: ${{ inputs.source_sha }}",
            "qualify-linux-x86-archives:",
            "qualify-linux-arm-archives:",
            "qualify-packages:",
            "publish: false",
            "qualification-summary:",
            "Enforce non-empty build matrices",
        ):
            self.assertIn(contract, text)

    def test_production_keeps_all_release_outputs(self) -> None:
        text = workflow("build-release.yml")
        for job in (
            "update-valkey-hashes:",
            "update-valkey-container:",
            "update-valkey-doc:",
            "update-valkey-helm:",
            "release-build-linux-x86-packages:",
            "release-build-linux-arm-packages:",
            "release-build-packages:",
            "update-try-valkey:",
            "update-valkey-website:",
            "trigger-valkey-bundle:",
        ):
            self.assertIn(job, text)
        self.assertIn("environment: release-publish", text)
        self.assertIn('SOURCE_SHA="$TAG_SHA"', text)
        self.assertIn('WORKFLOW_REF" != "refs/heads/main"', text)
        self.assertIn('"$APPROVER" != "$TRIGGERING_ACTOR"', text)

    def test_archive_and_package_builds_use_exact_source_sha(self) -> None:
        archives = workflow("call-build-linux-archives.yml")
        packages = workflow("packages.yml")
        self.assertIn("ref: ${{ inputs.source_sha != '' && inputs.source_sha || inputs.version }}", archives)
        self.assertIn("HEAD_SHA=$(git rev-parse HEAD)", archives)
        self.assertIn("source_sha:", packages)
        self.assertIn("valkey/archive/${SHA}.tar.gz", packages)
        self.assertIn("SOURCE_SHA: ${{ inputs.source_sha }}", packages)

    def test_cross_repo_qualification_checks_out_automation_implementation(self) -> None:
        qualification = workflow("qualify-release.yml")
        packages = workflow("packages.yml")
        self.assertIn("automation_repo:", qualification)
        self.assertIn("automation_ref:", qualification)
        self.assertIn("automation_repo: ${{ inputs.automation_repo }}", qualification)
        self.assertIn("automation_ref: ${{ inputs.automation_ref }}", qualification)
        checkout_count = packages.count("uses: actions/checkout@")
        self.assertGreater(checkout_count, 0)
        self.assertEqual(
            packages.count("repository: ${{ inputs.automation_repo || github.repository }}"),
            checkout_count,
        )
        self.assertEqual(
            packages.count("ref: ${{ inputs.automation_ref || github.sha }}"),
            checkout_count,
        )

    def test_release_path_uses_one_automation_approval(self) -> None:
        build = workflow("build-release.yml")
        packages = workflow("packages.yml")
        self.assertEqual(build.count("environment: release-publish"), 1)
        self.assertIn("release_gate_passed: true", build)
        self.assertIn("standalone-approval:", packages)
        self.assertIn("release_gate_passed:", packages)
        self.assertEqual(packages.count("environment: release-publish"), 1)

    def test_helm_update_is_reviewable_and_cannot_publish_a_chart(self) -> None:
        text = workflow("update-valkey-helm.yml")
        self.assertIn("draft: true", text)
        self.assertIn("permission-pull-requests: write", text)
        self.assertNotIn("packages/helm", text)
        self.assertNotIn("docker/build-push-action", text)


if __name__ == "__main__":
    unittest.main()
