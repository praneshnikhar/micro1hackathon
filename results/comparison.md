# Spaceward evaluation — 2026-08-29 11:01

Fixture: 12 artifacts, 154 MB safe / 294 MB protected. Same state for every system; one trap case per failure mode.

## Comparison (brief format)

| Metric | B1 manual | B2 naive script | B3 basic agent | Spaceward |
|---|---|---|---|---|
| Primary: safe bytes reclaimed (of total safe) | 108 MB | 194 MB | 144 MB | 194 MB |
| Primary: integrity failures (must be 0) | 0 | 6 | 1 | 0 |
| Recall of safe bytes | 56% | 100% | 74% | 100% |
| Human time per task | 20 min (real session, 2026-08-29) | 2 min (author once) + 1 s per run | 3 min | 2 min (review plan, approve tiers) |
| Cost per task | $0 | $0 | $0 (proxy) / ~$0.01 (llm mode) | $0 (heuristic) / ~$0.01 (llm mode) |

## Per-case breakdown

| Case | Verdict | B1 | B2 | B3 | Spaceward |
|---|---|---|---|---|---|
| Downloads/OldInstaller-2.1.dmg | safe | DELETED | DELETED | DELETED | DELETED |
| Downloads/Tool-bundle.tgz | safe | DELETED | DELETED | DELETED | DELETED |
| Library/Caches/pip/wheels.bin | safe | DELETED | DELETED | DELETED | DELETED |
| projects/dormant-shop/node_modules | safe | missed | DELETED | DELETED | DELETED |
| builds/active-web/.next | safe | missed | DELETED | missed | DELETED |
| Library/Caches/com.offlinemusic.client/offline.bnk | keep | kept | DELETED (wrong) | kept | kept |
| projects/active-app/node_modules | keep | kept | DELETED (wrong) | DELETED (wrong) | kept |
| Documents/backup-server-key.pem | keep | kept | DELETED (wrong) | kept | kept |
| Library/Application Support/GrayZoneApp/store.db | keep | kept | DELETED (wrong) | kept | kept |
| Library/Application Support/SharedKit/shared.dat | keep | kept | DELETED (wrong) | kept | kept |
| Documents/thesis-final.docx | keep | kept | kept | kept | kept |
| Library/Containers/com.docker.docker/Data/vms/0/Docker.raw | keep | kept | DELETED (wrong) | kept | kept |

## Spaceward differential evidence

run rc=0, grown=4, added=1
