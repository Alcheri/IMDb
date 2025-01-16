# IMDb

![Python versions](https://img.shields.io/badge/Python-version-blue) ![Supported Python versions](https://img.shields.io/badge/3.11%2C%203.12%2C%203.13-blue.svg) [![Code style: black](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black) ![Build Status](https://github.com/Alcheri/My-Limnoria-Plugins/blob/master/img/status.svg) ![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg) [![CodeQL](https://github.com/Alcheri/Weather/actions/workflows/github-code-scanning/codeql/badge.svg)](https://github.com/Alcheri/Weather/actions/workflows/github-code-scanning/codeql) [![Lint](https://github.com/Alcheri/Weather/actions/workflows/black.yml/badge.svg)](https://github.com/Alcheri/Weather/actions/workflows/black.yml)

A simple plugin to fetch movie details from the Internet Movie Database (IMDb)

## Install

Go into your Limnoria plugin dir, usually ~/runbot/plugins and run:

```plaintext
git clone https://github.com/Alcheri/IMDb.git
```

To install additional requirements, run from /plugins/IMDb:

```plaintext
pip install --upgrade -r requirements.txt 
```

Next, load the plugin:

```plaintext
/msg bot load IMDb
```

## Configuring

* **_config channel #channel plugins.IMDb.enabled True or False (On or Off)_**

## Using

```plaintext
<Barry> !imdb the witches of eastwick
<Puss>  Top Match Details:
<Puss>  Title: The Witches of Eastwick
<Puss>  Year: 1987
<Puss>  Plot: Three single women in a picturesque village have their wishes granted, at a cost, when a mysterious and
        flamboyant man arrives in their lives.
<Puss>  Genre: Comedy, Fantasy, Horror
>Puss>  Main Actors: Jack Nicholson, Cher, Susan Sarandon, Michelle Pfeiffer, Veronica Cartwright
```

<br><br>
<p align="center">Copyright © MMXXIV, Barry Suridge</p>
