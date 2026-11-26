# Agent harness for ine_gt

## Set up the development environment

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe harness.py build
```

Run commands from the repository root with the editable package installed in the project virtual environment. Audit and persona use simulated responses. Live requires HTTPS access to datos.ine.gob.gt.

| Stage | Command | Agent output |
| --- | --- | --- |
| Inspect | `.\.venv\Scripts\python.exe harness.py inspect` | Read project files, parse Python sources, and check that the first README example calls the exported loader and citation functions with valid argument names and counts. |
| Build | `.\.venv\Scripts\python.exe harness.py build` | Install the package and development dependencies in the environment. Make the smallest change that satisfies the journey. |
| Audit | `.\.venv\Scripts\python.exe harness.py audit` | Report the test result, public signature/docstring changes, warning or exception behavior, and any remaining risk. |
| Persona | `.\.venv\Scripts\python.exe harness.py persona` | Verify the analyst journey below with simulated CKAN data. |
| Live | `.\.venv\Scripts\python.exe harness.py live` | Search the actual catalog, read one raw IPC row, load both curated series and check the municipal citation. Prints observed figures, UTC timestamps and query URLs. |

## Rehearse the live preview

For the preview rehearsal, run `.\.venv\Scripts\python.exe -m pytest -q -s -p no:cacheprovider tests/live_portal.py::test_vista_previa_en_portal` from the presentation computer and network. This test fails if the real preview fails.

For the presentation, run `.\.venv\Scripts\python.exe examples/demo_vista_previa.py` once during rehearsal and again on stage. A successful call saves a timestamped two-row preview under `outputs/` on that computer. On a portal error the script displays the saved result as a capture, or the local series catalog if there is no capture. A fallback demonstrates offline behavior and does not count as a successful live test.

## First persona: an analyst preparing a citable figure

An analyst knows a municipality's name but sees two matches. They select the department, load population for 2026, and put the period, value, and source in a report. The test in `tests/test_persona.py` checks these steps without network access. A failure means the human workflow or the statistical result is broken, even if individual helper tests pass.

## Review rules for the agent

- Keep the README's three-line example runnable and preserve `mostrar_fuente(tabla)` beside a quoted number.
- Check public type hints and docstrings for inputs, output columns, units, and series-dependent arguments.
- Preserve received values and provenance. Test warnings with a usable returned result; test invalid totals and missing columns against the documented exception contract.
- Prefer the existing public functions and dependencies. Add shared abstraction only after two real uses appear.
- Distinguish simulated tests from any live portal consultation in the final report. Never describe a simulated value as a published INE figure.

## Prepare a release

Keep user-visible changes under «Pendiente de publicación» in [CHANGELOG.md](CHANGELOG.md) as work lands on master. When publishing a numbered release, move those entries under its version and publication date. Check the version in pyproject.toml, the package's __version__, and the client User-Agent. Run inspect, audit and live against the release candidate and record the outcomes. Keep installation and usage in the README.
