#!/usr/bin/env python3
"""Build and optionally push a DOCA layer container image from a template Containerfile."""

import argparse
import os
import subprocess
import sys
import tempfile
from string import Template

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONTAINERFILE = os.path.join(SCRIPT_DIR, "ovs-doca.Containerfile")

# Maps the arch property value (Linux convention) to the podman --platform value (OCI convention).
ARCH_TO_PLATFORM = {
    "x86_64":  "linux/amd64",
    "aarch64": "linux/arm64",
}

# (property_key, cli_flag, help_text, is_file_path)
PROPERTY_DEFS = [
    ("base_image",          "--base-image",          "Base OCP image SHA or tag (used in FROM)", False),
    ("doca_version",        "--doca-version",        "DOCA version string, e.g. 3.2.2", False),
    ("rhel_version",        "--rhel-version",        "RHEL major version, e.g. 9", False),
    ("epel_version",        "--epel-version",        "EPEL major version, e.g. 9", False),
    ("openvswitch_version", "--openvswitch-version", "OVS package version suffix to remove, e.g. 3.5", False),
    ("arch",                "--arch",                f"Target architecture: {', '.join(ARCH_TO_PLATFORM)} (default: x86_64)", False),
    ("image_path",          "--image-path",          "Full image destination, e.g. quay.io/org/repo/image", False),
    ("os_version_tag",      "--os-version-tag",      "Tag applied to the image, e.g. 4.21.24", False),
    ("pull_secret_file",    "--pull-secret-file",    "Path to pull secret JSON file (must exist)", True),
    ("quay_user",           "--quay-user",           "Quay.io username for push login", False),
    ("quay_password_file",  "--quay-password-file",  "Path to file containing Quay password (must exist)", True),
]

FILE_PATH_PROPS = {key for key, _, _, is_file in PROPERTY_DEFS if is_file}


def parse_properties(path):
    props = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                props[key.strip()] = value.strip()
    return props


def build_parser():
    parser = argparse.ArgumentParser(
        prog="build_doca_image.py",
        description=(
            "Render a template Containerfile and build (optionally push) a DOCA layer image.\n\n"
            "Values are loaded from --properties, then overridden by any CLI flags supplied.\n"
            "The --properties file is optional if all required values are given as CLI flags."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--properties", metavar="PATH",
        help="Path to a .properties file (key=value, lines starting with # are ignored).",
    )
    parser.add_argument(
        "--credentials-file", metavar="PATH",
        help=(
            "Path to a credentials properties file "
            f"(default: credentials.properties next to the script). "
            "Must exist when specified explicitly."
        ),
    )
    parser.add_argument(
        "--containerfile", metavar="PATH",
        default=DEFAULT_CONTAINERFILE,
        help=f"Template Containerfile to render (default: {DEFAULT_CONTAINERFILE}).",
    )
    parser.add_argument(
        "--generate-only", action="store_true",
        help=(
            "Render the Containerfile and print its path, then exit. "
            "No build or push is performed. The rendered file is always preserved."
        ),
    )
    parser.add_argument(
        "--preserve-rendered-containerfile", action="store_true",
        help="Keep the rendered Containerfile after the build completes (default: delete it).",
    )
    parser.add_argument(
        "--no-push", action="store_true",
        help="Skip pushing the image after build (default: push).",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print the resolved configuration and rendered Containerfile content before building.",
    )

    grp = parser.add_argument_group(
        "image / build properties",
        "Each flag overrides the corresponding key from --properties.",
    )
    for key, flag, help_text, _ in PROPERTY_DEFS:
        grp.add_argument(flag, dest=key, metavar="VALUE", help=help_text)

    return parser


def render(template_path, substitutions):
    with open(template_path) as f:
        content = f.read()
    try:
        return Template(content).substitute(substitutions)
    except KeyError as exc:
        print(f"ERROR: template references undefined variable: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"ERROR: malformed template placeholder: {exc}", file=sys.stderr)
        sys.exit(1)


def run_cmd(cmd, stdin_file=None):
    """Print and run a command. Streams output. Exits on non-zero return code."""
    print(f"+ {' '.join(cmd)}")
    if stdin_file:
        with open(stdin_file, "rb") as f:
            result = subprocess.run(cmd, stdin=f)
    else:
        result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


DEFAULT_CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, "credentials.properties")


def load_config(args):
    """Build effective config with priority: credentials file < properties file < CLI args."""
    config = {}

    # 1. Credentials file (lowest priority for credential keys).
    if args.credentials_file:
        if not os.path.isfile(args.credentials_file):
            print(f"ERROR: credentials file not found: {args.credentials_file}", file=sys.stderr)
            sys.exit(1)
        config.update(parse_properties(args.credentials_file))
    elif os.path.isfile(DEFAULT_CREDENTIALS_FILE):
        config.update(parse_properties(DEFAULT_CREDENTIALS_FILE))

    # 2. Version properties file (overrides credentials if the keys appear there).
    if args.properties:
        if not os.path.isfile(args.properties):
            print(f"ERROR: properties file not found: {args.properties}", file=sys.stderr)
            sys.exit(1)
        config.update(parse_properties(args.properties))

    # 3. CLI args (highest priority).
    for key, _, _, _ in PROPERTY_DEFS:
        val = getattr(args, key, None)
        if val is not None:
            config[key] = val

    return config


def validate_config(config, push, generate_only):
    """Validate required file-path properties and arch value. Exits on error."""
    errors = []

    arch = config.get("arch", "x86_64")
    if arch not in ARCH_TO_PLATFORM:
        errors.append(f"'arch' must be one of: {', '.join(ARCH_TO_PLATFORM)}; got: {arch!r}")

    if not generate_only:
        for key in FILE_PATH_PROPS:
            if key == "quay_password_file" and not push:
                continue
            path = config.get(key)
            if not path:
                errors.append(f"'{key}' is not set")
            elif not os.path.isfile(path):
                errors.append(f"'{key}' path does not exist: {path}")

    if errors:
        for msg in errors:
            print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(1)

def render_container_file_in_temporary_file(containerfile, config):
    rendered_content = render(containerfile, config)

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".Containerfile", prefix="doca-rendered-")
    with os.fdopen(tmp_fd, "w") as f:
        f.write(rendered_content)

    print(f"Rendered Containerfile: {tmp_path}")
    return tmp_path

def full_image_ref(config):
    """Return <image_path>:<os_version_tag>-<arch>."""
    image_path = config.get("image_path")
    os_version_tag = config.get("os_version_tag")
    arch = config.get("arch", "x86_64")
    if not image_path:
        print("ERROR: 'image_path' is required", file=sys.stderr)
        sys.exit(1)
    if not os_version_tag:
        print("ERROR: 'os_version_tag' is required", file=sys.stderr)
        sys.exit(1)
    return f"{image_path}:{os_version_tag}-{arch}"


def build_image(config, rendered_containerfile):
    ref = full_image_ref(config)
    arch = config.get("arch", "x86_64")
    platform = ARCH_TO_PLATFORM[arch]
    run_cmd([
        "podman", "build",
        "-t", ref,
        "-f", rendered_containerfile,
        "--authfile", config.get("pull_secret_file"),
        "--platform", platform,
    ])
    print("Build complete.")


def push_image(config):
    ref = full_image_ref(config)
    quay_user = config.get("quay_user")
    quay_password_file = config.get("quay_password_file")

    if not quay_user:
        print("ERROR: 'quay_user' is required for push", file=sys.stderr)
        sys.exit(1)

    run_cmd(
        ["podman", "login", "-u", quay_user, "--password-stdin", "quay.io"],
        stdin_file=quay_password_file,
    )
    run_cmd(["podman", "push", ref])
    print("Push complete.")

    digest = subprocess.check_output(
        ["podman", "inspect", "--format={{.Digest}}", ref],
        text=True,
    ).strip()
    print(f"Image reference : {ref}")
    print(f"Digest (for machine config): {digest}")


def main():
    parser = build_parser()
    args = parser.parse_args()

    config = load_config(args)
    push = not args.no_push

    if not os.path.isfile(args.containerfile):
        print(f"ERROR: template Containerfile not found: {args.containerfile}", file=sys.stderr)
        sys.exit(1)

    validate_config(config, push, args.generate_only)

    tmp_path = render_container_file_in_temporary_file(args.containerfile, config)
    
    if args.verbose:
        print("\n--- Resolved configuration ---")
        for key, value in sorted(config.items()):
            print(f"  {key} = {value}")
        print("\n--- Rendered Containerfile ---")
        with open(tmp_path) as f:
            print(f.read())
        print("------------------------------\n")

    if args.generate_only:
        print("--generate-only: skipping build. Rendered file preserved.")
        return

    should_delete = not args.preserve_rendered_containerfile

    try:
        build_image(config, tmp_path)
        if push:
            push_image(config)
    finally:
        if should_delete and os.path.exists(tmp_path):
            os.unlink(tmp_path)
            print(f"Cleaned up rendered Containerfile: {tmp_path}")
        elif not should_delete:
            print(f"Rendered Containerfile preserved at: {tmp_path}")


if __name__ == "__main__":
    main()
