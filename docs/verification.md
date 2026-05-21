# Verification

## Automated tests

```bash
make test
```

21 tests cover simulator, failure injection, rules, ML scoring, and policy.

## Rule thresholds

| Check | Threshold |
|-------|-----------|
| Roll | \|roll\| > 25° |
| Airspeed disagree | \|error\| > 10 kt |
| Low altitude + descent | alt < 2000 ft, VS < -1500 fpm |
| Control effectiveness | < 0.60 |
| GPS confidence | < 0.50 |

## Simulation checks (preset missions)

| Metric | Target |
|--------|--------|
| Fault presets trigger ≥1 incident | 5/5 fault presets |
| Nominal rule false positives | 0 |
| Every incident has message + subsystem | Yes |

## ML

- Risk scores in [0, 1]
- Fault missions should peak higher than nominal (same seed) — see `test_ml_risk.py`
- ML does not directly command abort; rules/policy do

## Manual UI checklist

- [ ] Preset mission runs
- [ ] Charts render
- [ ] Incidents list populates on fault cases
- [ ] JSON/Markdown download works
