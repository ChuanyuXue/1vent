import os
from typing import Optional
from openai import OpenAI
from pathlib import Path
import logging

from config import OPENAI_MODEL, SUMMARY_DIR, DATE_FORMAT, LOG_DIR
from comms import get_local_date


def get_latest_log() -> Optional[str]:
    """Get the content of the most recent log file"""
    try:
        log_dir = Path(LOG_DIR)
        log_files = list(log_dir.glob("productivity_log_*.txt"))

        if not log_files:
            logging.error("No log files found")
            return None

        latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
        with open(latest_log, "r") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error reading log file: {e}")
        return None


def get_prompt() -> Optional[str]:
    """Read the analysis prompt from prompts.txt"""
    try:
        prompt_file = Path("src") / "prompts.txt"
        with open(prompt_file, "r") as f:
            content = f.read()
            # Get the content between [CODING_ANALYSIS] and the next section or end of file
            start = content.find("[CODING_ANALYSIS]") + len("[CODING_ANALYSIS]")
            end = content.find("[", start) if content.find("[", start) != -1 else None
            return content[start:end].strip() if end else content[start:].strip()
    except Exception as e:
        logging.error(f"Error reading prompt file: {e}")
        return None


def process_with_chatgpt(client: OpenAI, log_content: str) -> Optional[str]:
    """Process log data with ChatGPT"""
    try:
        prompt = get_prompt()
        if not prompt:
            return None

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that analyzes coding activity data and provides personalized insights and suggestions for improvement.",
                },
                {"role": "user", "content": f"{prompt}\n\n{log_content}"},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error in processing with ChatGPT: {e}")
        return None


def save_summary(summary: str) -> None:
    """Save the summary to a file"""
    today = get_local_date().strftime(DATE_FORMAT)
    summary_dir = Path(SUMMARY_DIR)
    summary_dir.mkdir(exist_ok=True, parents=True)

    summary_file = summary_dir / f"coding_summary_{today}.txt"
    try:
        with open(summary_file, "w") as f:
            f.write(summary)
        logging.info(f"Summary saved to {summary_file}")
    except Exception as e:
        logging.error(f"Failed to save summary: {e}")


def get_api_key() -> Optional[str]:
    """Get OpenAI API key from environment variable"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logging.error("OpenAI API key not found in environment variables")
        return None
    return api_key


def main() -> None:

    # Load OpenAI API key from config
    api_key = get_api_key()
    if not api_key:
        logging.error("OpenAI API key not found in config.yml")
        return

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)

    # Get latest log content
    log_content = get_latest_log()
    if not log_content:
        logging.error("No log content found")
        return

    # Process log with ChatGPT
    summary = process_with_chatgpt(client, log_content)
    if summary:
        logging.info("\nCoding Activity Summary:")
        logging.info("=" * 50)
        logging.info(summary)
        logging.info("=" * 50)

        # Save summary to file
        save_summary(summary)


if __name__ == "__main__":
    main()
