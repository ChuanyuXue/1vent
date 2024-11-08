# 1vent

Automated daily coding activity tracking and analysis powered by WakaTime API and OpenAI

## Overview

1vent is a tool that automatically tracks your coding activity using WakaTime, analyzes the data, and provides personalized insights through OpenAI. It runs daily via GitHub Actions and can optionally email you the results.

## Usage

1. Fork this repository
2. Add secret variables to your repository

### Required Secret Variables

First make sure Github __Actions are enabled__ in your forked repository. Then go to your repo settings, tab __Secrets and variables__ -> Actions -> New repository secret and add the following variables:

- `GMAIL_USER`: Your email address (e.g. `yourname@gmail.com`)
- `GMAIL_PASSWORD`: Your gmail __app-specific password__
- `RECIPIENT_EMAIL`: The email address to receive summaries
- `OPENAI_API_KEY`: Your OpenAI API key
- `WAKATIME_API_KEY`: Your WakaTime API key

To save and analyze history coding activity, you also need to go __Actions__ -> General -> Workflow permissions -> Add the __Read and write permissions__. Change the timezone and GPT model verion in `src/config.py`.

For Gmail users, generate an app-specific password [here](https://myaccount.google.com/apppasswords).
