<!-- IMDb plugin for Limnoria that returns details for the top title match. -->

<h1 align ="center">IMDb</h1>

<!-- README_HEADER:start -->
<p align="center">
  <a href="https://github.com/Alcheri/IMDb/actions/workflows/tests.yml">
    <img src="https://github.com/Alcheri/IMDb/actions/workflows/tests.yml/badge.svg" alt="Tests">
  </a>
  <a href="https://github.com/Alcheri/IMDb/actions/workflows/lint.yml">
    <img src="https://github.com/Alcheri/IMDb/actions/workflows/lint.yml/badge.svg" alt="Lint">
  </a>
  <a href="https://github.com/Alcheri/IMDb/security/code-scanning">
    <img src="https://github.com/Alcheri/IMDb/actions/workflows/codeql.yml/badge.svg" alt="CodeQL">
  </a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code style: black">
  <img src="https://img.shields.io/badge/limnoria-compatible-brightgreen.svg" alt="Limnoria">
  <img src="https://img.shields.io/badge/License-BSD_3--Clause-blue.svg" alt="License">
</p>
<!-- README_HEADER:end -->

<p align="center">
  <em>IMDb plugin for Limnoria that returns details for the top title match.</em>
</p>

## Features

- Looks up the top IMDb title match for a query.
- Returns title, year, plot, genre/type, and main actors.
- Gracefully falls back to suggestion data when IMDb blocks detailed page scraping.

## Installation

From your Limnoria plugins directory (for example `~/runbot/plugins`):

```bash
git clone https://github.com/Alcheri/IMDb.git
```

Install dependencies from the plugin directory:

```bash
pip install --upgrade -r requirements.txt
```

Load the plugin:

```text
/msg bot load IMDb
```

## Configuration

Enable per channel:

```text
config channel #channel plugins.IMDb.enabled True
```

Disable per channel:

```text
config channel #channel plugins.IMDb.enabled False
```

## Usage

```text
<Barry> !imdb the witches of eastwick
<Puss> Top Match Details:
<Puss> Title: The Witches of Eastwick
<Puss> Year: 1987
<Puss> Plot: Three single women in a picturesque village have their wishes granted, at a cost, when a mysterious and flamboyant man arrives in their lives.
<Puss> Genre: Comedy, Fantasy, Horror
<Puss> Main Actors: Jack Nicholson, Cher, Susan Sarandon, Michelle Pfeiffer, Veronica Cartwright
```

## Notes

- IMDb can return anti-bot/interstitial responses for full title pages.
- When that happens, the plugin still returns a valid top match with available metadata.

## Troubleshooting

If `!imdb` is not returning expected output, check the following:

1. Confirm the plugin is loaded.

```text
/msg bot list IMDb
```

1. Confirm it is enabled for the channel.

```text
config channel #channel plugins.IMDb.enabled
```

1. Reload after updates.

```text
/msg bot reload IMDb
```

1. Reinstall plugin dependencies.

```bash
pip install --upgrade -r requirements.txt
```

1. Test with a popular, unambiguous title.

```text
!imdb the matrix
```

1. Check Limnoria logs for request or parsing errors if output is still missing.

### Expected Degraded Behavior

When IMDb blocks full title-page details, the plugin should still return a valid top match using suggestion metadata.

```text
<Barry> !imdb the witches of eastwick
<Puss> Top Match Details:
<Puss> Title: The Witches of Eastwick
<Puss> Year: 1987
<Puss> Plot: Plot unavailable (IMDb blocked detailed page lookup).
<Puss> Genre: feature
<Puss> Main Actors: Jack Nicholson, Cher
```

This response indicates fallback mode is working as intended.

<p align="center">Copyright © MMXXVI, Barry Suridge</p>
