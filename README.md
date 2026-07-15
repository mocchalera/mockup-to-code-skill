# mockup-to-code

An agent skill for turning static web-design mockups into responsive HTML/CSS
with measurable visual-fidelity evidence.

Instead of treating a mockup as a screenshot to trace, the skill builds a real
web document with flow, Grid, and Flexbox. It combines source-image
measurement, manifest-driven implementation, browser rendering, box and pixel
comparison, responsive checks, and explicit completion gates.

## What it provides

- Pixel-clone, production, and hybrid reconstruction modes
- Source measurement and element-manifest workflows
- Photo/background asset preflight and provenance checks
- Responsive typography, layout, and page-flow validation
- Browser rendering and DOMRect-based box comparison
- Crop-pair, pixel-diff, artifact, and completion evidence
- Regression tests for the executable gates

The complete operating contract is in [`SKILL.md`](SKILL.md). Detailed phase
guides are under [`references/`](references/).

## Requirements

- Python 3
- Node.js 18 or newer
- npm
- Chromium, Google Chrome, or Microsoft Edge

OpenCV, NumPy, and Pillow enable the full image-analysis path. Some operations
have a reduced Pillow-based fallback. The setup script reports the capabilities
available on the current machine.

## Install

Clone the repository into a skill directory recognized by your agent runtime,
then install the Node dependency:

```bash
git clone https://github.com/mocchalera/mockup-to-code-skill.git mockup-to-code
cd mockup-to-code
npm ci
bash scripts/setup_env.sh
```

The setup script prints the resolved skill directory, required-script status,
browser availability, Python imaging support, and recommended operating mode.

## Use

Invoke the skill when asking an agent to implement a supplied design mockup,
for example:

> Use mockup-to-code to turn these desktop and mobile mockups into a responsive
> page.

The agent should read `SKILL.md`, follow the referenced phase documents, keep
generated work in an isolated work root, and report the computed completion
verdict without promoting a prototype to complete.

## Validate the repository

```bash
npm ci
npm test
python3 -m json.tool schemas/element_manifest.schema.json >/dev/null
git diff --check
```

`VALIDATION.md` records the evolution of the executable contracts and the
evidence used to verify them.

## Repository layout

- `SKILL.md` — agent-facing entry point and hard rules
- `references/` — measurement, composition, assets, QA, and fallback guides
- `scripts/` — deterministic measurement and verification tools
- `schemas/` — element-manifest JSON Schema
- `templates/` — starter manifests, CSS, and review artifacts
- `test/` — regression coverage for the executable gates

## License

[ISC](LICENSE)
