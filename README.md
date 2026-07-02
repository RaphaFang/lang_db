# lang_db

A personal vocabulary trainer backed by Postgres. You feed it words; it stores
definitions, example sentences, and semantic vectors, then schedules reviews
with spaced repetition and gives you active writing practice.

## Architecture

One Postgres database (`lang`) and one Python package (`widget_srs/`).

**Tables** (`schema/*.sql`):

| table          | holds                                                                                          |
| -------------- | ---------------------------------------------------------------------------------------------- |
| `voc_t`        | the words: definition, pronunciation, sentences, synonyms/antonyms, and a pgvector `embedding` |
| `learning_t`   | per-word FSRS state (difficulty, stability, next review date)                                  |
| `review_log_t` | every review, used to retrain the scheduler                                                    |
| `group_t`      | word groupings                                                                                 |

**Code** (`widget_srs/`):

| module                  | does                                                        |
| ----------------------- | ----------------------------------------------------------- |
| `add_words.py`          | import words → cards via the Claude API                     |
| `paste_import.py`       | same import, $0, using a web LLM subscription (copy/paste)  |
| `embed.py`              | compute embeddings and find semantically similar words      |
| `fsrs.py` / `review.py` | FSRS-5 scheduler and its database glue                      |
| `run_review.py`         | the daily review session (passive recall)                   |
| `practice.py`           | active practice: write sentences/paragraphs from a word set |

Two inbox files at the repo root feed the importers: `words.txt` (words you
want to learn, one per line) and `paste.json` (where you drop a web model's
reply). Both are gitignored.

## Usage

### Setup (once)

1. Postgres running locally with a `lang` database and the `pgvector` extension.
2. Create the tables: run each file in `schema/`.
3. Install deps: `pip install psycopg pydantic anthropic sentence-transformers numpy scipy`
4. Environment variables:
   - `PSQL_USER`, `DB_PASSWORD` — database login (always)
   - `ANTHROPIC_API_KEY` — only for API import (`add_words`)
   - `LANG_LLM_MODEL` — optional, defaults to `claude-haiku-4-5`

### Add words

Put new words in `words.txt`, one per line, then either:

```bash
python3 -m widget_srs.add_words          # via Claude API (automatic)
```

or, for $0 using your web subscription: (this is the approach i choose)

```bash
python3 -m widget_srs.paste_import --prompt   # prints a prompt to paste into the web model
#   ... paste the model's JSON reply into paste.json ...
python3 -m widget_srs.paste_import            # imports it
```

Either way, words already in `voc_t` are skipped and `words.txt` is cleared on success.

### Review (passive recall)

```bash
python3 -m widget_srs.run_review [lang] [limit]
```

Shows each due word; you rate it 1–4 (Again/Hard/Good/Easy) and FSRS schedules
the next review.

### Practice (active production)

```bash
python3 -m widget_srs.practice [lang]
```

Pulls 10 semantically related words, you write one sentence per word or a short
paragraph using all of them, and it prints a grading prompt to paste into a web
model for feedback.
