# Deploying to GitHub Pages

GitHub Pages hosts static websites from a GitHub repository. The Student Profile Builder provider
builds your static profile and publishes only the generated files to a
dedicated `gh-pages` branch. GitHub Pages serves the root of that branch.

In the GUI, publishing opens a separate deployment terminal. GitHub CLI owns authentication and
confirmation prompts while the editor and live preview remain usable. A deployment failure or a
closed terminal does not stop the GUI or change the local profile.

## Requirements and authentication

Install Git, GitHub CLI (`gh`), and have a GitHub account. Authenticate using GitHub CLI:

```powershell
gh auth login
```

Check installation and account status on Windows, Linux, or macOS:

```text
git --version
gh --version
gh auth status
```

An internet connection is required for GitHub authentication and publishing. GitHub CLI may open a
browser or provide a device-login flow. See the official [GitHub CLI authentication guide](https://cli.github.com/manual/gh_auth_login)
and [GitHub Pages documentation](https://docs.github.com/pages).

Student Profile Builder never asks for or stores your GitHub password or token. It never retrieves
a GitHub CLI token or inspects credential stores. GitHub CLI and Git handle authentication using
their supported HTTPS or SSH configuration.

## Personal and project sites

A personal site uses repository `username.github.io` and URL:

```text
https://username.github.io/
```

A project site uses a repository you name, such as `academic-profile`, and URL:

```text
https://username.github.io/academic-profile/
```

Only repositories owned by the active GitHub CLI account are supported in Phase 4.

For example, username `alice` can choose:

- Personal: repository `alice.github.io`, website `https://alice.github.io/`. Choose this for the
  main website attached to the account.
- Project: repository `academic-profile`, website `https://alice.github.io/academic-profile/`.
  Choose this if the personal site is already used or a separately named portfolio is preferred.

## Guided GUI workflow

```text
Edit profile → Save → local static build → Publish → separate terminal
             → gh-pages branch updated → GitHub Pages publishes the site
```

Open **Publish → GitHub Pages**, review Git and `gh` status, enter the expected username, select
Personal or Project, and click **Publish in Terminal**. If login is needed, complete it in that
terminal. Repository creation, an unmanaged `gh-pages` branch, or a conflicting Pages source keeps
the existing confirmation safeguards.

After success the GUI offers the expected website and repository links. GitHub may need some time
to make new content available; check repository Pages/Actions status rather than assuming an exact
deployment time.

## Commands

Interactive:

```powershell
python manage.py deploy github
```

Personal or project site:

```powershell
python manage.py deploy github --site personal
python manage.py deploy github --site project --repo academic-profile
```

Zero-network planning is available by supplying the expected username:

```powershell
python manage.py deploy github --site project --repo academic-profile --username YOUR_NAME --dry-run
```

Without `--username`, dry run may make a read-only GitHub CLI query to identify the active account;
it never creates repositories, pushes, runs login, or changes Pages settings.

Template and profile overrides remain temporary:

```powershell
python manage.py deploy github --site project --repo academic-profile --template basic --profile examples/profiles/full.md
```

## Publishing and ownership

The provider uses an isolated temporary Git workspace; it never adds `.git` to `dist/` or modifies
the current project repository. It copies only generated output, adds `.nojekyll`, and records
branch ownership with `.profile-builder-pages.json`. It commits and pushes only `gh-pages`, then
configures Pages to publish from `gh-pages` `/`. It does not create GitHub Actions workflows.

Unlike IITD's shared hosting directory, the marked `gh-pages` branch is entirely generated and may
be replaced on updates. If a pre-existing `gh-pages` branch lacks the marker, publishing defaults
to No. Changing a Pages source configured elsewhere also requires confirmation. Use `--yes` only
after reviewing these risks. Main, master, default, and source branches are not published over.

If generated content is unchanged, no new commit is pushed. GitHub may take a few minutes to make
a new or updated Pages URL available.

## Troubleshooting

- Git/`gh` missing: install the official tools; the builder does not install them.
- Not authenticated: run `gh auth login` or allow the interactive command to launch it.
- Wrong account: check `gh auth status` and switch accounts using GitHub CLI.
- Creation denied or repository exists: verify account ownership and naming.
- Unmanaged `gh-pages`: inspect it before consenting to replacement.
- Pages source differs: confirm whether changing it to `gh-pages` `/` is intended.
- Push rejected: check GitHub/Git permissions and configured protocol.
- URL unavailable: wait briefly and inspect the repository's Pages settings.

If the site shows 404, open **Repository → Settings → Pages** and confirm:

```text
Source: Deploy from a branch
Branch: gh-pages
Folder: /(root)
```

If the latest version is not visible, confirm the `gh-pages` branch was updated and review the
repository's Pages or Actions status.

## Manual fallback

Automatic publishing is recommended. If it cannot be used:

1. Build locally with `python manage.py build`.
2. Create or choose a repository owned by your GitHub account.
3. Publish the contents of `dist/`—not the surrounding project—to a `gh-pages` branch.
4. In **Repository → Settings → Pages → Build and deployment**, choose **Deploy from a branch**,
   branch `gh-pages`, folder `/(root)`, and save.

Normal future updates are simply: edit, save, and publish again.

## Security

Student Profile Builder never requests, stores, logs, or places in job files/commands a GitHub
password, personal access token, OAuth token, or SSH private key. It never calls `gh auth token`.
Authentication remains delegated to GitHub CLI and Git.

## Manual integration test

```powershell
gh auth status
python manage.py deploy github --site project --repo profile-builder-test --username YOUR_NAME --dry-run
python manage.py deploy github --site project --repo profile-builder-test
```

Verify the repository, `gh-pages` branch, marker, `.nojekyll`, Pages source, and website. Confirm
the default/source branch was not overwritten. If cleanup is desired, delete the test repository
manually through GitHub; this tool never deletes repositories.
# Prerequisite status

The Dashboard and `bootstrap.py` report Git and GitHub CLI (`gh`) separately. Missing tools do not
block editing or previewing and are never installed automatically. Install them through their
official platform instructions and authenticate with `gh auth login` before a real deployment.
