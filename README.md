# Then & Now: SA Town Names — live data

This repository holds the town and rename data for the **Then & Now: SA
Town Names** app. GitHub Pages publishes it at:

**https://nicos0351.github.io/then-and-now-data/data.json**

The app checks that address about once a week, and whenever someone taps
**⋮ → Refresh data**. If `dataVersion` is higher than the version the
phone already has, the app downloads the file, checks it, and updates its
map. Users get new renames without an app update.

## What's in `data.json`

| Field | What it is |
|---|---|
| `format` | File layout version. Leave at `1`; only an app release can change it. |
| `dataVersion` | **Raise by 1 every time you change anything.** Phones only update when this goes up. |
| `updated` | Date of this version, e.g. `"2026-11-03"`. |
| `changes` | List of `{version, date, summary}`. Add one per version; the app shows the summaries under "What's new". |
| `towns` | Every place on the map: towns, plus renamed airports, dams and mountain passes (same format as `assets/towns.json` in the app). |
| `stories` | Name meanings and pronunciation guides (same format as `assets/name_stories.json`). |

A town looks like this:

```json
{
  "key": "asset:east london:-33.015:27.912",
  "name": "KuGompo City",
  "oldName": "East London",
  "hasKnownRename": true,
  "renamedYear": 2026,
  "reverted": false,
  "notes": "Gazetted 6 Feb 2026. Under review after more than 38,000 objections (as of May 2026), so the old name is still widely used.",
  "province": "Eastern Cape",
  "latitude": -33.01529,
  "longitude": 27.91162,
  "population": 478676,
  "source": "https://..."
}
```

- `kind` is `"airport"`, `"dam"` or `"pass"` for those places; leave it
  out for towns. The app gives each kind its own pin, and only towns count
  for "Where am I?".
- **Never change a town's `key`.** It's how phones recognise the town, even
  after its name changes. For a brand-new town, invent a new unique key
  starting with `asset:`.
- To record a rename: put the new name in `name`, the name it had before
  1994 in `oldName`, set `hasKnownRename` to `true`, and fill in
  `renamedYear` and `source`.
- If a rename has a story entry, update the story's `name` to match.

## How updates happen

1. **Monthly check.** On the 1st of each month a scheduled Claude task
   searches for newly gazetted South African place-name changes. If it
   finds any, it opens a **pull request** here with the edits and the
   sources. It never publishes anything by itself.
2. **You review.** Open the pull request, read the sources, and check the
   **"Check data.json"** result at the bottom: green means the file is
   valid.
3. **Merge to publish.** Click *Merge*. The **"Publish data.json"** step
   checks the file again and republishes it within a few minutes; phones
   pick it up on their next check. If the check fails, nothing is
   published and the previous data stays live.

You can also edit `data.json` yourself in GitHub's web editor (pencil
icon). Raise `dataVersion`, add a `changes` entry, and commit. The same
check runs.

## Safety checks

- `validate.py` runs automatically on every pull request and push. It
  rejects missing fields, duplicate keys, unknown provinces, coordinates
  outside South Africa, a `dataVersion` that didn't go up, and accidental
  mass deletions (more than 2% of towns).
- The app runs its own checks too, so a broken file can never wipe a
  phone's data. It keeps what it has if the download fails, the file is
  malformed, it has fewer than 900 towns, or its `format` is unknown.
- Towns a user has edited or added in the app are never changed by an
  update.

Run the check yourself with `python validate.py data.json`.

## Offline Maps packs (optional)

The app's paid **Offline Maps** add-on reads its list of downloadable map
packs from `offline/packs.json` in this repository, published at
`https://nicos0351.github.io/then-and-now-data/offline/packs.json`. Until
that file exists, nothing is published and the add-on stays hidden in
the app.

- The `.mbtiles` map files themselves are **not** stored here. Attach them
  to a GitHub **Release** of this repository and put each download link in
  `packs.json`.
- `validate_packs.py` checks the list on every pull request and before
  publishing (format, https links, exact sizes, zoom ranges).
- The format, how to make packs legally and the size estimates are in the
  app's README ("Offline Maps add-on").

## Licences

Town names, positions and populations come from
[GeoNames](https://www.geonames.org/) under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Rename details
and name meanings cite their sources in the `source` / `sources` fields.
