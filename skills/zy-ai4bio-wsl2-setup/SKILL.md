---
name: zy-ai4bio-wsl2-setup
description: Detect Windows, Linux, or WSL2; reuse an existing WSL2 distribution or provision Ubuntu WSL2 when needed; then prepare a Linux Codex environment for ZY-AI4Bio skills. Use when a Windows user wants to install or run the local scientific workflows and asks for OS detection, WSL2 setup, or environment migration.
---

# ZY-AI4Bio Windows / WSL2 Setup

Codex and skill files work on native Windows. WSL2 is recommended for this repository's Linux-oriented scientific executables and shell scripts; it does not install those executables, model weights, or databases by itself.

## Detect And Reuse

1. Identify the machine on which commands will actually run. On native Linux, use that Linux installation; on an existing WSL2 session, reuse it. Do not try to create WSL on Linux or macOS. If the user's Windows machine is not connected, explain that its WSL state cannot be inspected or changed remotely.
2. On native Windows, run `scripts/ensure_wsl2.ps1` in PowerShell without `-Apply`. It reports whether a WSL2 distribution exists, whether an existing WSL1 distribution can be converted, or whether Ubuntu must be installed. Reuse any existing WSL2 distribution, including one with a name other than Ubuntu.
3. If setup is needed, explain that conversion or installation can require administrator rights, disk space, a Windows restart, and interactive creation of a Linux user. After the user has authorized those system changes, run the same script with `-Apply` from an elevated PowerShell session. Never unregister, reset, overwrite, or reinstall an existing distribution.
4. After a restart or first-run prompt, rerun the detection script. Do not report WSL2 as ready until it confirms a version-2 distribution.

## Run The Skills In WSL2

1. In the Windows Codex desktop app, set **Settings > Agent environment > Windows Subsystem for Linux** and restart the app. The integrated terminal is configured separately; select WSL there too when using its terminal for setup. Alternatively, use the Codex CLI inside WSL2. Verify the agent's commands run in Linux before starting a scientific workflow.
2. Work from the Linux filesystem, such as `~/code/zhuying-ai4bio`. If needed, install Git in the WSL distribution, clone this repository there, and run `bash skills/zy-ai4bio-wsl2-setup/scripts/bootstrap_wsl.sh` from its root. The bootstrap installs small base packages when supported, copies missing skills without replacing existing ones, and reports scientific executables visible on `PATH`.
3. Start a new Codex chat after installing skills. Confirm the active `CODEX_HOME` and skill directory match the agent's WSL environment. Native Windows and WSL skill installations are not assumed to be shared.
4. Check the specific scientific tool needed for the user's task. For example, WSL2 alone does not provide GROMACS, GNINA, UniDock-Pro, Chai-1, or their GPU runtime. Never claim a workflow is runnable until its executable, inputs, and required GPU/API access have been checked.

Use the official [Windows Codex WSL guide](https://learn.chatgpt.com/docs/windows/wsl), [Windows app settings](https://learn.chatgpt.com/docs/windows/windows-app), and [Microsoft WSL installation guide](https://learn.microsoft.com/en-us/windows/wsl/install) if host setup differs from the usual path.
