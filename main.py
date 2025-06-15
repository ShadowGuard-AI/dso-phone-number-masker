#!/usr/bin/env python3

import argparse
import re
import logging
import os
import sys
import chardet
from faker import Faker
from faker.providers import phone_number
import secrets

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Initialize Faker with a seed for reproducibility
fake = Faker()
Faker.seed(secrets.randbits(32))  # Use secrets for better randomness


def setup_argparse():
    """
    Sets up the argument parser for the command-line interface.
    """
    parser = argparse.ArgumentParser(
        description="Masks or replaces phone numbers in text and data files."
    )
    parser.add_argument(
        "input_file",
        help="Path to the input file to process.",
    )
    parser.add_argument(
        "-o",
        "--output_file",
        help="Path to the output file. If not specified, overwrites the input file.",
    )
    parser.add_argument(
        "-m",
        "--mask_char",
        default="X",
        help="Character to use for masking phone numbers. Defaults to 'X'.",
    )
    parser.add_argument(
        "-r",
        "--replace",
        action="store_true",
        help="Replace phone numbers with fake phone numbers.",
    )
    parser.add_argument(
        "-k",
        "--keep_area_code",
        action="store_true",
        help="Keep the original area code when replacing or masking phone numbers.",
    )
    parser.add_argument(
        "--log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level. Defaults to INFO.",
    )

    return parser.parse_args()


def detect_encoding(file_path):
    """
    Detects the encoding of a file using chardet.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The detected encoding, or None if detection fails.
    """
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            return result["encoding"]
    except Exception as e:
        logging.error(f"Error detecting encoding: {e}")
        return None


def mask_phone_number(phone_number, mask_char="X"):
    """
    Masks a phone number, replacing digits with the specified character.

    Args:
        phone_number (str): The phone number to mask.
        mask_char (str): The character to use for masking. Defaults to 'X'.

    Returns:
        str: The masked phone number.
    """
    return "".join([mask_char if char.isdigit() else char for char in phone_number])


def replace_phone_number(phone_number, keep_area_code=False):
    """
    Replaces a phone number with a fake one.

    Args:
        phone_number (str): The phone number to replace.
        keep_area_code (bool): Whether to keep the original area code. Defaults to False.

    Returns:
        str: The replaced phone number.
    """
    try:
        # Extract area code if requested and possible.  Handle cases where number doesn't
        # neatly divide into area code / prefix/ line number.  This regex is more permissive
        # than the matching one used in find_phone_numbers, because we're trying to *extract*
        # something here.  The more restrictive one in find_phone_numbers is more security focused,
        # as it will avoid false positives.
        match = re.match(r"(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})", phone_number)

        if keep_area_code and match:
            area_code = match.group(1)
            new_number = fake.phone_number()

            new_match = re.match(r"(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})", new_number)

            if new_match:

                # Reassemble with existing area code
                replaced_number = area_code + "-" + new_match.group(2) + "-" + new_match.group(3)
            else:
                logging.warning(f"Failed to parse generated phone number {new_number}, using full random number.")
                replaced_number = fake.phone_number()

        else:
            replaced_number = fake.phone_number()

        return replaced_number
    except Exception as e:
        logging.error(f"Error replacing phone number: {e}")
        return phone_number  # Return original if replacement fails


def find_phone_numbers(text):
    """
    Finds phone numbers in the given text using regular expressions.  This is deliberately quite strict,
    to avoid false positives which could lead to data corruption.

    Args:
        text (str): The text to search.

    Returns:
        list: A list of phone numbers found in the text.
    """
    # Regular expression pattern to match phone numbers, more specific and secure
    pattern = re.compile(
        r"(?<!\d)(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})(?!\d)", re.VERBOSE
    )  # Added negative lookahead and lookbehind to avoid catching parts of longer sequences
    return list(
        set(re.findall(pattern, text))
    )  # Use set to remove duplicates before converting to list


def process_file(input_file, output_file=None, mask_char="X", replace=False, keep_area_code=False):
    """
    Processes the input file, masking or replacing phone numbers, and writes the output to a file.

    Args:
        input_file (str): Path to the input file.
        output_file (str): Path to the output file. If None, overwrites the input file.
        mask_char (str): Character to use for masking.
        replace (bool): Whether to replace phone numbers with fake ones.
        keep_area_code (bool): Whether to keep the original area code when replacing.
    """
    if not os.path.exists(input_file):
        logging.error(f"Input file not found: {input_file}")
        sys.exit(1)

    encoding = detect_encoding(input_file)
    if not encoding:
        logging.error("Failed to detect file encoding.  Please specify encoding if errors occur.")
        encoding = "utf-8"  # Fallback to utf-8

    try:
        with open(input_file, "r", encoding=encoding) as f:
            content = f.read()
    except Exception as e:
        logging.error(f"Error reading input file: {e}")
        sys.exit(1)

    phone_numbers = find_phone_numbers(content)
    logging.debug(f"Found phone numbers: {phone_numbers}")

    for phone_number in phone_numbers:
        if replace:
            replacement = replace_phone_number(phone_number, keep_area_code)
            logging.info(f"Replacing '{phone_number}' with '{replacement}'")
            content = content.replace(phone_number, replacement)
        else:
            masked_number = mask_phone_number(phone_number, mask_char)
            logging.info(f"Masking '{phone_number}' with '{masked_number}'")
            content = content.replace(phone_number, masked_number)

    if output_file is None:
        output_file = input_file  # Overwrite input file if no output file is specified

    try:
        with open(output_file, "w", encoding=encoding) as f:
            f.write(content)
        logging.info(f"Processed file saved to: {output_file}")
    except Exception as e:
        logging.error(f"Error writing output file: {e}")
        sys.exit(1)


def main():
    """
    Main function to execute the phone number masking/replacement process.
    """
    args = setup_argparse()

    # Set logging level
    logging.getLogger().setLevel(args.log_level)

    logging.debug(f"Arguments: {args}")

    input_file = args.input_file
    output_file = args.output_file
    mask_char = args.mask_char
    replace = args.replace
    keep_area_code = args.keep_area_code

    # Input Validation
    if len(mask_char) != 1:
        logging.error("Mask character must be a single character.")
        sys.exit(1)

    try:
        process_file(input_file, output_file, mask_char, replace, keep_area_code)
    except Exception as e:
        logging.critical(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()