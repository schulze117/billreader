# billreader

Reads files from a Google Drive folder and writes extracted fields into a
Google Sheet.

## Run

GitHub → Actions → run the workflow and enter the Drive folder id.

Locally:

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in values
python -m billreader.main
```

## Spreadsheet

The spreadsheet lives inside the Drive folder and must contain a `template` tab,
which is duplicated for each subfolder. A `summary` tab, if present, is left untouched.

## Secrets (Actions → Secrets)

- `GOOGLE_AI_API_KEY`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

The service account needs access to the Drive folder.
