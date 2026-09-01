# Deploying to IIT Delhi

The IIT Delhi provider uploads the generated static website to your CSC home space through your
computer's standard OpenSSH `ssh` and `scp` programs.

## Choose a target

- Public website: `~/public_html`, expected URL `https://web.iitd.ac.in/~userid/`. Your IITD
  account must be eligible for public web hosting.
- IITD-internal website: `~/private_html`, expected URL
  `http://privateweb.iitd.ac.in/~userid/`. It is accessible only from the IIT Delhi network.

The tool never guesses from your degree or program; you choose explicitly.

## Requirements and password safety

You need Python plus locally installed `ssh` and `scp`. On Windows PowerShell, check OpenSSH with:

```powershell
ssh -V
scp
```

The Student Profile Builder never asks for or stores your IIT Delhi password. When authentication
is required, the system's OpenSSH client displays the password prompt directly. Existing SSH keys
or an SSH agent work naturally; the builder does not create or manage keys.

From the GUI, Publish creates a local non-secret job and opens a separate terminal. All OpenSSH
prompts appear there while the editor and preview remain available. Closing the terminal interrupts
only that deployment; the GUI later marks the job interrupted. If no desktop terminal can be found,
the GUI provides an equivalent safe manual command containing no password.

On a first SSH connection, OpenSSH may ask whether the host is authentic. Personally verify and
accept it according to normal IIT Delhi/SSH practice. The builder does not bypass host-key checks
or answer that question automatically. Authentication may be requested more than once because
Phase 3 uses separate SSH and SCP operations.

## Commands

Interactive deployment:

```powershell
python manage.py deploy iitd
```

Explicit targets:

```powershell
python manage.py deploy iitd --target public --userid YOUR_ID
python manage.py deploy iitd --target private --userid YOUR_ID
```

Validate everything locally without connecting:

```powershell
python manage.py deploy iitd --target public --userid YOUR_ID --dry-run
```

Use a temporary template/profile override without changing `config.yml`:

```powershell
python manage.py deploy iitd --target public --userid YOUR_ID --template basic --profile examples/profiles/full.md
```

On the first deployment to a target, generated paths such as `index.html` can replace existing
files with the same names. The prompt defaults to No. For an intentional non-interactive first
deployment, add `--yes`. Files not tracked by the builder are never intentionally deleted.

## What happens

The builder validates and builds locally, inventories file count/size, validates `ssh` and `scp`,
then asks OpenSSH to read the previous ownership manifest. It uploads into a unique private staging
directory, installs generated paths, applies 755 to managed directories and 644 to managed files,
adds only the traverse bit to your home directory, writes the new manifest, removes only obsolete
previously managed files, verifies `index.html` and the manifest remotely, and removes staging.

Staging is the internally generated `$HOME/.student-profile-builder-upload-<32 hex characters>`
for the current deployment. Only that exact controlled directory is recursively removed, which
also handles hidden files and nested output. `public_html`, `private_html`, and `$HOME` are never
recursively deleted. If staging cleanup fails after installation and verification, publication
remains successful and the result includes a temporary-cleanup warning.

Updating is simply: edit `profile.md`, then deploy again. No remote runtime or package install is
needed.

Public hosting is intended for IIT Delhi faculty and PhD students. IITD-only hosting is available
to IITD users with CSC home space and is accessible only from the IIT Delhi network. The user always
chooses the target; the builder never infers program eligibility.

Before a real deployment the builder checks DNS/TCP reachability of `ssh1.iitd.ac.in:22` with a
short timeout. A failure suggests checking the current connection and campus/VPN requirements.
Authentication remains entirely in OpenSSH. Separate manifest, SCP upload, and install operations
can cause multiple password prompts. Optional `--retries 0..2` provides bounded high-level retries
for OpenSSH exit 255; it never reads or supplies a password. Connect timeout and conservative
keepalive settings are applied without disabling host verification.

## Existing files and troubleshooting

The builder manages only paths listed in `.profile-builder-manifest.json`. On the first deployment
it removes nothing. It does not recursively change unrelated files or wipe hosting directories.

- `ssh`/`scp` not found: enable the operating system's OpenSSH Client; do not install password automation tools.
- Authentication failed: check your IITD user ID/password or existing SSH configuration; the builder cannot inspect credentials.
- Permission denied or directory unavailable: verify your CSC account's hosting eligibility and access.
- Host-key warning: verify the server fingerprint through an IITD-authoritative channel; never bypass verification.
- Website not accessible immediately: allow for server delay and check the selected URL/eligibility.
- Private site unavailable: try from the IITD network or approved IITD access path.

## Manual integration test

First run the dry run. Then preserve a small unrelated test file remotely and deploy with:

```powershell
python manage.py deploy iitd --target public --userid YOUR_ID
```

Confirm OpenSSH handles authentication, `index.html` exists, the expected URL loads, and the
unmanaged test file remains. Repeat with `private` only if you intend to publish to that target.
# Prerequisite status

The Dashboard and `bootstrap.py` report whether `ssh` and `scp` are available. Missing OpenSSH does
not block editing or previewing and is never installed automatically. Install the OpenSSH client
through your operating system, then restart the application.
