# iAquaLink Plus (salt cell)

Adds Jandy salt cell (AquaPure / TruClear) control to Home Assistant for iAquaLink 2.0/3.0 (iQ20) systems.

It rides on the built-in **Jandy iAquaLink** integration: no second login, no credentials stored. It sends the
documented iQ20 cloud commands that the core integration doesn't expose yet (`get_swc_config`, `set_swc_config`,
`control_swc_boost`; see the iaqualink-py protocol reference).

## Entities (device "Salt Cell")
| Entity | What it does |
|---|---|
| Pool output setting (number, 0–100 %) | Sets chlorine output for the pool |
| Spa output setting (number, disabled by default) | Sets output for the spa |
| Boost (switch) | Starts/stops boost (resumes if paused) |
| Boost duration (number, 1–24 h) | Length used the next time boost starts |
| Pool output / Pool status | What the cell is actually doing (running, standby, boosting…) |
| Salinity | Salt reading from the cell, ppm |
| Low salt (binary sensor) | Cell's low-salt warning |
| Boost status / Boost time remaining | Boost state and countdown |
| Salt cell (diagnostic) | detected / not detected / controller offline |

Diagnostics download includes the raw cloud payloads and read-only probes (OneTouch, variable-speed pump).

## Install
1. HACS → Integrations → ⋮ → Custom repositories → add this repo as an Integration, then download it. (Or copy `custom_components/iaqualink_plus` into `/config/custom_components/`.)
2. Restart Home Assistant.
3. Settings → Devices & services → Add integration → **iAquaLink Plus (Salt Cell)**.

Requires the Jandy iAquaLink integration to be set up first. Tested against Home Assistant 2026.10.2 with
iaqualink 0.7.0.
