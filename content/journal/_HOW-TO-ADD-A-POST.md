---
title: How to add a journal post
date: 2026-08-11
draft: true
---

Files starting with an underscore are never published. This one is a guide.

## Adding a post

Make a new file in this folder called `YYYY-MM-DD-short-name.md`, for example
`2026-11-30-ruka.md`. Put this at the top, between the two lines of dashes:

```
---
title: The first race of the season
date: 2026-11-30
summary: One or two sentences that appear on the journal index.
image: race-forest
tags: racing, world cup
draft: false
---
```

Then write below it in plain text. A blank line starts a new paragraph.

- `title` and `date` are required. Everything else is optional.
- `date` must be `YYYY-MM-DD`. Posts are ordered newest first.
- `summary` shows on the index. Without one, the first paragraph is used.
- `image` is a slot name from `content/images.json`, not a file path. Leave it
  out if there is no photograph.
- `draft: true` keeps a post out of the built site entirely. Use it while
  writing. Delete the line or set it to `false` to publish.

## Formatting

`## A subheading` makes a subheading. `**bold**` and `*italic*` work.
A link is `[the words](https://example.com)`. A list is lines starting with `-`.

## Publishing

Run `python build.py` in the project folder. The post appears on `journal.html`
and gets its own page. Nothing else needs changing, and the Journal link only
appears in the site navigation once at least one post is published.
